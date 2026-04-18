#!/bin/bash
set -e

REGION="us-east-1"
LOCALSTACK_ENDPOINT="http://localhost:4566"
DYNAMODB_TABLE="monty-cloud-image-metadata"
S3_BUCKET="monty-cloud-images"
DELETE_QUEUE_URL="http://localhost:4566/000000000000/delete-queue"

# Create S3 bucket
awslocal s3 mb s3://$BUCKET --region $REGION

# Create DynamoDB table with GSI
awslocal dynamodb create-table \
  --table-name $TABLE \
  --attribute-definitions \
    AttributeName=image_id,AttributeType=S \
    AttributeName=user_id,AttributeType=S \
    AttributeName=uploaded_at,AttributeType=S \
  --key-schema AttributeName=image_id,KeyType=HASH \
  --global-secondary-indexes '[
    {
      "IndexName": "user-images-index",
      "KeySchema": [
        {"AttributeName": "user_id", "KeyType": "HASH"},
        {"AttributeName": "uploaded_at", "KeyType": "RANGE"}
      ],
      "Projection": {"ProjectionType": "ALL"},
      "ProvisionedThroughput": {"ReadCapacityUnits": 5, "WriteCapacityUnits": 5}
    }
  ]' \
  --provisioned-throughput ReadCapacityUnits=5,WriteCapacityUnits=5 \
  --region $REGION

echo "Infrastructure initialized successfully."
