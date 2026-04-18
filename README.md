# Monty Cloud Image Service

Serverless image management service using AWS Lambda, S3, DynamoDB, and API Gateway — fully testable locally via LocalStack.

## Architecture

```
Client → API Gateway → Lambda Handlers → S3 / DynamoDB
                                ↑
                          Shared Lambda Layer
                     (db_service, s3_service, config)
```

- **upload_trigger** — generates a pre-signed S3 upload URL
- **s3_event_processor** — S3 event triggers metadata persistence to DynamoDB
- **list_images** — queries a DynamoDB GSI by user_id
- **download_image** — generates a pre-signed S3 download URL
- **delete_image** — removes the S3 object and DynamoDB record

## Prerequisites

- Docker & Docker Compose
- Python 3.11+
- `awslocal` CLI (`pip install awscli-local`)

## Quick Start

```bash
pip install -r requirements.txt
make setup    # starts LocalStack + creates S3 bucket & DynamoDB table
make test     # runs unit + integration tests
```

## Project Structure

See the tree in the repo root for full layout. Key directories:

| Path | Purpose |
|---|---|
| `src/handlers/` | Lambda function entry points |
| `src/layer/python/` | Shared layer (DB, S3, config, response helpers) |
| `tests/unit/` | Mocked unit tests |
| `tests/integration/` | Tests against LocalStack |
| `docs/` | OpenAPI spec |
