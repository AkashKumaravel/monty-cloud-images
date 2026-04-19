#!/bin/bash
set -e

REGION="us-east-1"
ENDPOINT="http://localhost:4566"
LAMBDA_ENDPOINT="http://localstack:4566"

export AWS_PAGER=""
AWS="aws --endpoint-url=$ENDPOINT --region $REGION --no-cli-pager"

S3_BUCKET="monty-cloud-images"
DDB_TABLE="monty-cloud-image-metadata"
QUEUE_NAME="image-events"
QUEUE_DLQ_NAME="image-events-dlq"
S3_EVENT_DLQ_NAME="s3-event-dlq"
API_NAME="image-service-api"
ROLE_ARN="arn:aws:iam::000000000000:role/lambda-role"

echo "🚀 Starting LocalStack setup..."

# -------------------------
# WAIT FOR LOCALSTACK
# -------------------------
echo "⏳ Waiting for LocalStack..."

for i in {1..40}; do
  if curl -s $ENDPOINT/_localstack/health | grep -q '"services"'; then
    echo "✅ LocalStack ready"
    break
  fi
  sleep 2
done

# -------------------------
# S3 (idempotent)
# -------------------------
echo "📦 S3 bucket..."

$AWS s3 mb s3://$S3_BUCKET 2>/dev/null || echo "  Already exists → skipping"

# -------------------------
# DynamoDB (SAFE CREATE)
# -------------------------
echo "🗄️ DynamoDB table..."

if ! $AWS dynamodb describe-table --table-name $DDB_TABLE > /dev/null 2>&1; then
  $AWS dynamodb create-table \
    --table-name $DDB_TABLE \
    --attribute-definitions \
      AttributeName=image_id,AttributeType=S \
      AttributeName=user_id,AttributeType=S \
      AttributeName=uploaded_at,AttributeType=N \
    --key-schema \
      AttributeName=image_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes '[
      {
        "IndexName": "user-index",
        "KeySchema": [
          {"AttributeName": "user_id", "KeyType": "HASH"},
          {"AttributeName": "uploaded_at", "KeyType": "RANGE"}
        ],
        "Projection": {"ProjectionType": "ALL"}
      }
    ]' > /dev/null
else
  echo "  Already exists → skipping"
fi

# -------------------------
# SQS — DLQs + Main Queues
# -------------------------
echo "📨 SQS queues..."

get_or_create_queue() {
  local NAME=$1
  local URL
  URL=$($AWS sqs get-queue-url --queue-name $NAME --query 'QueueUrl' --output text 2>/dev/null) || \
  URL=$($AWS sqs create-queue --queue-name $NAME --query 'QueueUrl' --output text)
  echo $URL
}

# DLQ for delete worker
DELETE_DLQ_URL=$(get_or_create_queue $QUEUE_DLQ_NAME)

DELETE_DLQ_ARN=$($AWS sqs get-queue-attributes \
  --queue-url $DELETE_DLQ_URL \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

# Main delete queue + redrive policy
QUEUE_URL=$(get_or_create_queue $QUEUE_NAME)

$AWS sqs set-queue-attributes \
  --queue-url $QUEUE_URL \
  --attributes "{\"RedrivePolicy\":\"{\\\"deadLetterTargetArn\\\":\\\"$DELETE_DLQ_ARN\\\",\\\"maxReceiveCount\\\":\\\"3\\\"}\"}" 

echo "  Delete Queue : $QUEUE_URL"
echo "  Delete DLQ   : $DELETE_DLQ_URL"

# DLQ for s3 event handler
S3_EVENT_DLQ_URL=$(get_or_create_queue $S3_EVENT_DLQ_NAME)

S3_EVENT_DLQ_ARN=$($AWS sqs get-queue-attributes \
  --queue-url $S3_EVENT_DLQ_URL \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

echo "  S3 Event DLQ : $S3_EVENT_DLQ_URL"

# Lambda env (uses LAMBDA_ENDPOINT so Lambdas can reach LocalStack inside Docker network)
LAMBDA_ENV="Variables={
  S3_BUCKET=$S3_BUCKET,
  DYNAMODB_TABLE=$DDB_TABLE,
  DELETE_QUEUE_URL=$QUEUE_URL,
  LOCALSTACK_ENDPOINT=$LAMBDA_ENDPOINT,
  S3_PRESIGN_ENDPOINT=$ENDPOINT
}"

# -------------------------
# PACKAGE LAMBDA CODE
# -------------------------
echo "📦 Packaging Lambda..."

rm -f function.zip
cd src
zip -r ../function.zip . > /dev/null
cd ..

# -------------------------
# DEPLOY LAMBDAS
# -------------------------
echo "⚙️ Deploying Lambdas..."

deploy_lambda() {
  local NAME=$1
  local HANDLER=$2

  if $AWS lambda get-function --function-name $NAME > /dev/null 2>&1; then
    $AWS lambda update-function-code \
      --function-name $NAME \
      --zip-file fileb://function.zip > /dev/null

    $AWS lambda update-function-configuration \
      --function-name $NAME \
      --timeout 30 \
      --environment "$LAMBDA_ENV" > /dev/null
  else
    $AWS lambda create-function \
      --function-name $NAME \
      --runtime python3.11 \
      --handler $HANDLER \
      --role $ROLE_ARN \
      --timeout 30 \
      --zip-file fileb://function.zip \
      --environment "$LAMBDA_ENV" > /dev/null
  fi

  echo "  ✅ $NAME"
}

deploy_lambda "upload-handler"          "handlers.upload_handler.handler"
deploy_lambda "list-handler"            "handlers.list_handler.handler"
deploy_lambda "download-handler"        "handlers.download_handler.handler"
deploy_lambda "delete-handler"          "handlers.delete_handler.handler"
deploy_lambda "delete-worker"           "handlers.delete_worker.handler"
deploy_lambda "s3-event-handler"        "handlers.s3_event_handler.handler"
deploy_lambda "pending-cleanup-handler" "handlers.pending_cleanup_handler.handler"

# Allow time for Lambdas to fully register before wiring triggers
sleep 5

# -------------------------
# DLQ for s3-event-handler Lambda
# -------------------------
echo "🔁 Configuring s3-event-handler DLQ..."

$AWS lambda put-function-event-invoke-config \
  --function-name "s3-event-handler" \
  --maximum-retry-attempts 2 \
  --destination-config "{\"OnFailure\":{\"Destination\":\"$S3_EVENT_DLQ_ARN\"}}" > /dev/null

echo "  ✅ s3-event-handler → $S3_EVENT_DLQ_NAME (after 2 retries)"

# -------------------------
# S3 → Lambda Event Notification
# -------------------------
echo "🔔 Configuring S3 event notification..."

S3_EVENT_LAMBDA_ARN="arn:aws:lambda:$REGION:000000000000:function:s3-event-handler"

# Lambda needs a moment to be fully registered before S3 can validate it
sleep 5

$AWS s3api put-bucket-notification-configuration \
  --bucket $S3_BUCKET \
  --notification-configuration "{
    \"LambdaFunctionConfigurations\": [
      {
        \"LambdaFunctionArn\": \"$S3_EVENT_LAMBDA_ARN\",
        \"Events\": [\"s3:ObjectCreated:*\"]
      }
    ]
  }"

echo "  ✅ S3 ObjectCreated → s3-event-handler"

# -------------------------
# SQS → Lambda Event Source Mapping (delete-worker)
# -------------------------
echo "🔗 Configuring SQS → delete-worker..."

QUEUE_ARN=$($AWS sqs get-queue-attributes \
  --queue-url $QUEUE_URL \
  --attribute-names QueueArn \
  --query 'Attributes.QueueArn' \
  --output text)

EXISTING_MAPPING=$($AWS lambda list-event-source-mappings \
  --function-name delete-worker \
  --event-source-arn $QUEUE_ARN \
  --query 'EventSourceMappings[0].UUID' \
  --output text 2>/dev/null)

if [ "$EXISTING_MAPPING" = "None" ] || [ -z "$EXISTING_MAPPING" ]; then
  $AWS lambda create-event-source-mapping \
    --function-name delete-worker \
    --event-source-arn $QUEUE_ARN \
    --batch-size 1 > /dev/null
  echo "  ✅ SQS → delete-worker (new)"
else
  echo "  ✅ SQS → delete-worker (exists)"
fi

# -------------------------
# EventBridge — Pending cleanup every 24 hours
# -------------------------
echo "⏰ Scheduling pending cleanup (every 24h)..."

RULE_NAME="pending-cleanup-schedule"

$AWS events put-rule \
  --name $RULE_NAME \
  --schedule-expression "rate(24 hours)" > /dev/null

$AWS lambda add-permission \
  --function-name "pending-cleanup-handler" \
  --statement-id "eventbridge-cleanup" \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com > /dev/null 2>&1 || true

CLEANUP_LAMBDA_ARN="arn:aws:lambda:$REGION:000000000000:function:pending-cleanup-handler"

$AWS events put-targets \
  --rule $RULE_NAME \
  --targets "[{\"Id\":\"1\",\"Arn\":\"$CLEANUP_LAMBDA_ARN\"}]" > /dev/null

echo "  ✅ pending-cleanup-handler runs every 24 hours"

# -------------------------
# API GATEWAY (idempotent)
# -------------------------
echo "🌐 API Gateway..."

API_ID=$($AWS apigateway get-rest-apis \
  --query "items[?name=='$API_NAME'].id | [0]" \
  --output text 2>/dev/null)

if [ "$API_ID" = "None" ] || [ -z "$API_ID" ]; then
  API_ID=$($AWS apigateway create-rest-api --name $API_NAME --query 'id' --output text)
  echo "  Created API: $API_ID"
else
  echo "  Reusing API: $API_ID"
fi

LAMBDA_URI_PREFIX="arn:aws:apigateway:$REGION:lambda:path/2015-03-31/functions/arn:aws:lambda:$REGION:000000000000:function"

ROOT_ID=$($AWS apigateway get-resources \
  --rest-api-id $API_ID \
  --query 'items[?path==`/`].id | [0]' \
  --output text)

# Helper to create resource + method + integration
wire_route() {
  local PARENT_ID=$1
  local PATH_PART=$2
  local HTTP_METHOD=$3
  local LAMBDA_NAME=$4

  RESOURCE_ID=$($AWS apigateway create-resource \
    --rest-api-id $API_ID \
    --parent-id $PARENT_ID \
    --path-part "$PATH_PART" \
    --query 'id' --output text 2>/dev/null) || \
  RESOURCE_ID=$($AWS apigateway get-resources \
    --rest-api-id $API_ID \
    --query "items[?pathPart=='$PATH_PART' && parentId=='$PARENT_ID'].id | [0]" \
    --output text)

  $AWS apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method $HTTP_METHOD \
    --authorization-type NONE > /dev/null

  $AWS apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $RESOURCE_ID \
    --http-method $HTTP_METHOD \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "$LAMBDA_URI_PREFIX:$LAMBDA_NAME/invocations" > /dev/null

  echo "$RESOURCE_ID"
}

# /images
IMAGES_ID=$(wire_route $ROOT_ID "images" "GET" "list-handler")
echo "  ✅ GET /images → list-handler"

# /images/upload
UPLOAD_ID=$(wire_route $IMAGES_ID "upload" "POST" "upload-handler")
echo "  ✅ POST /images/upload → upload-handler"

# /images/{image_id}
IMAGE_ID_RESOURCE=$(wire_route $IMAGES_ID "{image_id}" "DELETE" "delete-handler")
echo "  ✅ DELETE /images/{image_id} → delete-handler"

# /images/{image_id}/download
DOWNLOAD_ID=$(wire_route $IMAGE_ID_RESOURCE "download" "GET" "download-handler")
echo "  ✅ GET /images/{image_id}/download → download-handler"

# -------------------------
# LAMBDA PERMISSIONS
# -------------------------
echo "🔐 Lambda permissions..."

for FN in upload-handler list-handler download-handler delete-handler; do
  $AWS lambda add-permission \
    --function-name $FN \
    --statement-id "apigw-$(date +%s)-$FN" \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com > /dev/null 2>&1 || true
done

# -------------------------
# DEPLOY API
# -------------------------
echo "🚀 Deploying API..."

$AWS apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name dev > /dev/null

BASE_URL="http://localhost:4566/restapis/$API_ID/dev/_user_request_"

echo ""
echo "✅ FULL STACK READY"
echo "==========================================="
echo ""
echo "📡 API Endpoints:"
echo "-------------------------------------------"
echo "POST   $BASE_URL/images/upload"
echo "GET    $BASE_URL/images"
echo "GET    $BASE_URL/images/{image_id}/download"
echo "DELETE $BASE_URL/images/{image_id}"
echo ""
echo "🔧 Internal (not API-triggered):"
echo "-------------------------------------------"
echo "S3 Event  → s3-event-handler (DLQ: $S3_EVENT_DLQ_NAME)"
echo "SQS Event → delete-worker    (DLQ: $QUEUE_DLQ_NAME)"
echo "Schedule  → pending-cleanup-handler (every 24h)"
echo ""
echo "📬 Queue URLs:"
echo "-------------------------------------------"
echo "Delete Queue     : $QUEUE_URL"
echo "Delete DLQ       : $DELETE_DLQ_URL"
echo "S3 Event DLQ     : $S3_EVENT_DLQ_URL"
echo "==========================================="
