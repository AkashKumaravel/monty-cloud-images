# Monty Cloud Image Service

Serverless image management service built with AWS Lambda, S3, DynamoDB, API Gateway, and SQS — fully testable locally via LocalStack.

## LocalStack — Local AWS Development

This project uses [LocalStack](https://localstack.cloud/) to emulate AWS services locally. LocalStack runs as a Docker container and provides a local endpoint (`http://localhost:4566`) that mimics real AWS APIs — no AWS account or credentials needed.

All infrastructure (S3, DynamoDB, Lambda, API Gateway, SQS, EventBridge) is created automatically by the setup script against this local endpoint.

**Useful resources if you're new to LocalStack:**

- [What is LocalStack & Getting Started](https://docs.localstack.cloud/aws/getting-started/) — overview and first steps
- [LocalStack AWS Service Reference](https://docs.localstack.cloud/aws/) — supported AWS services and their coverage
- [LocalStack with Docker Compose](https://learnbatta.com/blog/aws-localstack-with-docker-compose/#docker-compose-file-for-localstack-docker-composeyml) — how to set up LocalStack using Docker Compose


## Architecture

```
                                    ┌──────────────┐
                                    │  EventBridge  │
                                    │  (24h cron)   │
                                    └──────┬───────┘
                                           │
Client ──► API Gateway ──► Lambda ──► S3 / DynamoDB / SQS
                                           │
                              S3 Event ──► Lambda (mark COMPLETED)
                              SQS Msg  ──► Lambda (delete worker)
```

### Lambdas

| Lambda | Trigger | Purpose |
|---|---|---|
| `upload-handler` | API Gateway | Generate pre-signed upload URL + create PENDING record |
| `list-handler` | API Gateway | Query images with filters (user, file name, tag, time range) |
| `download-handler` | API Gateway | Generate pre-signed download URL (ownership enforced) |
| `delete-handler` | API Gateway | Queue async delete via SQS (ownership enforced) |
| `delete-worker` | SQS | Delete S3 object + DynamoDB record |
| `s3-event-handler` | S3 Event | Mark upload as COMPLETED after file lands in S3 |
| `pending-cleanup-handler` | EventBridge | Clean up stale PENDING records older than 24 hours |

### Upload Flow

```
1. Client → POST /images/upload → Lambda creates PENDING record + returns pre-signed URL
2. Client → PUT (pre-signed URL) → File uploaded directly to S3
3. S3 Event → Lambda → Marks record as COMPLETED in DynamoDB
```

### Delete Flow

```
1. Client → DELETE /images/{image_id} → Lambda validates ownership + queues SQS message
2. SQS → delete-worker Lambda → Deletes S3 object + DynamoDB record
```

### Resilience

| Component | Retry | DLQ |
|---|---|---|
| `s3-event-handler` | 2 retries | `s3-event-dlq` |
| `delete-worker` (SQS) | 3 receives | `image-events-dlq` |
| `pending-cleanup-handler` | EventBridge default | — |
| API handlers | Client retries on error | N/A (synchronous) |

---

## Prerequisites

- **Docker & Docker Compose** — LocalStack runs in a container
- **Python 3.11+**
- **AWS CLI** — used by the setup script (`pip install awscli`)

---

## Quick Start

```bash
# 1. Clone the repo
git clone <repo-url>
cd monty-cloud-images

# 2. Install Python dependencies
pip install -r requirements.txt

# 3. Start LocalStack + deploy everything
make all
```

That's it. The setup script will:
- Start LocalStack (Docker)
- Create S3 bucket, DynamoDB table, SQS queues (with DLQs)
- Deploy all Lambda functions
- Wire up S3 event notifications and SQS triggers
- Create API Gateway with all routes
- Schedule the pending cleanup job (every 24h)

At the end, it prints all API endpoints:

```
✅ FULL STACK READY
===========================================

📡 API Endpoints:
-------------------------------------------
POST   http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/upload
GET    http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images
GET    http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/{image_id}/download
DELETE http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/{image_id}
```

---

## API Reference

All API endpoints use `http://localhost:4566/restapis/<API_ID>/dev/_user_request_` as the base URL. Replace `<API_ID>` with the ID printed by `make all`.

Authentication is via the `x-user-id` header (mock auth for local development).

### 1. Upload Image

Generates a pre-signed S3 upload URL and creates a PENDING metadata record.

```
POST /images/upload
```

**Headers**

| Header | Required | Description |
|---|---|---|
| `x-user-id` | Yes | User identifier |
| `Content-Type` | Yes | `application/json` |

**Request Body**

```json
{
  "file_name": "photo.png",
  "tags": ["vacation", "beach"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `file_name` | string | Yes | Name of the file |
| `tags` | string[] | No | Tags for filtering (default: `[]`) |

**Response** `200 OK`

```json
{
  "image_id": "a756fdca-2863-4617-9a17-8da722359f2f",
  "upload_url": "http://localhost:4566/monty-cloud-images/...",
  "s3_key": "a756fdca-2863-4617-9a17-8da722359f2f_photo.png",
  "status": "PENDING"
}
```

**Then upload the file using the pre-signed URL:**

```bash
curl -X PUT "<upload_url>" --upload-file photo.png
```

After the file lands in S3, the status automatically changes to `COMPLETED`.

**Example**

```bash
# Step 1: Get upload URL
curl -X POST http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/upload \
  -H "Content-Type: application/json" \
  -H "x-user-id: user1" \
  -d '{"file_name": "photo.png", "tags": ["vacation"]}'

# Step 2: Upload file (use upload_url from response)
curl -X PUT "<upload_url>" --upload-file photo.png
```

**Errors**

| Status | Reason |
|---|---|
| 401 | Missing `x-user-id` header |
| 400 | Missing `file_name` in body |

---

### 2. List Images

Query images with filters. Supports pagination.

```
GET /images
```

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `user_id` | string | Filter by user (uses GSI) |
| `file_name` | string | Filter by file name (uses GSI) |
| `tag` | string | Filter by tag (scan + filter) |
| `uploaded_after` | int | Epoch timestamp — images uploaded after this time |
| `uploaded_before` | int | Epoch timestamp — images uploaded before this time |
| `limit` | int | Max results per page (default: 10, max: 50) |
| `next_token` | string | Pagination token from previous response |

**Response** `200 OK`

```json
{
  "items": [
    {
      "image_id": "a756fdca-...",
      "user_id": "user1",
      "file_name": "photo.png",
      "s3_key": "a756fdca-..._photo.png",
      "status": "COMPLETED",
      "tags": ["vacation"],
      "uploaded_at": 1776570036,
      "uploaded_date": "2026-04-19"
    }
  ],
  "count": 1,
  "request_id": "...",
  "next_token": "..."
}

```

**Examples**

```bash
# List by user
curl -X GET "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images?user_id=user1"

# List by tag
curl -X GET "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images?tag=vacation"

# List by file name
curl -X GET "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images?file_name=photo.png"

# List with time range
curl -X GET "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images?user_id=user1&uploaded_after=1700000000&uploaded_before=1800000000"

# Paginate
curl -X GET "http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images?user_id=user1&limit=5&next_token=<token>"
```

**Errors**

| Status | Reason |
|---|---|
| 400 | `limit` exceeds 50 |
| 400 | `uploaded_after` > `uploaded_before` |
| 400 | Invalid `next_token` |

---

### 3. Download Image

Generates a pre-signed S3 download URL. Ownership is enforced — only the uploader can download.

```
GET /images/{image_id}/download
```

**Headers**

| Header | Required | Description |
|---|---|---|
| `x-user-id` | Yes | Must match the image owner |

**Response** `200 OK`

```json
{
  "image_id": "a756fdca-...",
  "download_url": "http://localhost:4566/monty-cloud-images/...",
  "expires_in": 3600,
  "request_id": "..."
}
```

**Then download the file:**

```bash
curl -o photo.png "<download_url>"
```

**Example**

```bash
# Get download URL
curl -X GET http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/<image_id>/download \
  -H "x-user-id: user1"

# Download the file
curl -o photo.png "<download_url>"
```

**Errors**

| Status | Reason |
|---|---|
| 401 | Missing `x-user-id` header |
| 400 | Missing `image_id` |
| 404 | Image not found |
| 403 | User does not own the image |

---

### 4. Delete Image

Queues an async delete request. The image is removed from both S3 and DynamoDB by the delete worker.

```
DELETE /images/{image_id}
```

**Headers**

| Header | Required | Description |
|---|---|---|
| `x-user-id` | Yes | Must match the image owner |

**Response** `202 Accepted`

```json
{
  "message": "Delete request accepted",
  "image_id": "a756fdca-...",
  "status": "PENDING",
  "request_id": "..."
}
```

**Example**

```bash
curl -X DELETE http://localhost:4566/restapis/<API_ID>/dev/_user_request_/images/<image_id> \
  -H "x-user-id: user1"
```

**Errors**

| Status | Reason |
|---|---|
| 401 | Missing `x-user-id` header |
| 400 | Missing `image_id` |
| 404 | Image not found |
| 403 | User does not own the image |

---

## Running Tests

```bash
make test
```

Runs 109 unit tests using `pytest` + `moto` (AWS mock). No Docker or LocalStack needed for tests.

```
====================== 109 passed in 15s ======================
```

---

## Project Structure

```
monty-cloud-image-service/
├── src/
│   ├── handlers/                  # Lambda function entry points
│   │   ├── upload_handler.py
│   │   ├── list_handler.py
│   │   ├── download_handler.py
│   │   ├── delete_handler.py
│   │   ├── delete_worker.py       # SQS consumer — deletes S3 + DynamoDB
│   │   ├── s3_event_handler.py    # S3 trigger — marks COMPLETED
│   │   └── pending_cleanup_handler.py  # Scheduled — cleans stale PENDING
│   ├── models/                    # Data models
│   │   └── image_metadata.py      # ImageMetadata dataclass + DynamoDB schema
│   └── layer/python/              # Shared Lambda layer
│       ├── config.py              # Environment variable loading
│       ├── constants.py           # Shared constants (status, errors, limits)
│       ├── db_service.py          # DynamoDB operations
│       ├── s3_service.py          # S3 operations (pre-signed URLs)
│       ├── sqs_service.py         # SQS operations
│       ├── pagination.py          # Cursor-based pagination
│       └── utils.py               # Response helpers, logging, auth
├── tests/                         # Unit tests (pytest + moto)
├── docs/
│   └── api_spec.yaml              # OpenAPI spec
├── docker-compose.yml             # LocalStack container
├── setup-aws.sh                   # Infrastructure setup script
├── Makefile                       # Build commands
└── requirements.txt               # Python dependencies
```

---

## Makefile Commands

| Command | Description |
|---|---|
| `make all` | Start LocalStack + deploy everything |
| `make test` | Run unit tests |
| `make clean` | Stop LocalStack + remove artifacts |
| `make down` | Stop LocalStack |

---

## Tech Stack

| Service | Purpose |
|---|---|
| API Gateway | REST API routing |
| Lambda | Business logic |
| S3 | Image storage |
| DynamoDB | Image metadata |
| SQS | Async delete processing |
| EventBridge | Scheduled cleanup |
| LocalStack | Local AWS emulation |

---

## Design Decisions

### Pre-signed URLs over Lambda Proxy

Clients upload/download files directly to/from S3 using pre-signed URLs instead of streaming through Lambda. This keeps Lambda lightweight, avoids the 6MB payload limit, and lets S3 handle the heavy lifting.

### CDN-Ready Download Abstraction

The download handler uses `generate_download_url()` — an abstraction layer in `s3_service.py` that currently returns S3 pre-signed URLs. When moving to production, this can be swapped to return CloudFront signed URLs without changing any handler code.

```python
# s3_service.py
def generate_download_url(s3_key, expires_in=DOWNLOAD_URL_EXPIRY):
    """Today: S3 pre-signed URL. Future: CloudFront signed URL."""
    return generate_presigned_download_url(s3_key, expires_in)
```

### Async Deletes via SQS

Delete requests are queued to SQS rather than processed synchronously. This gives the client a fast `202 Accepted` response while the delete worker handles S3 + DynamoDB cleanup in the background with retry support and DLQ for failures.

### Stale PENDING Cleanup

If a client requests an upload URL but never uploads the file, the DynamoDB record stays in `PENDING` state. A scheduled EventBridge rule triggers the cleanup handler every 24 hours to delete PENDING records older than 24 hours.

---
