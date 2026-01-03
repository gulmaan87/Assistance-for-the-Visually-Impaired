# Backend API

FastAPI-based backend service providing ML inference endpoints with Redis caching and rate limiting.

## Setup

1. **Create virtual environment**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

4. **Start Redis** (required):
   ```bash
   docker run -d -p 6379:6379 redis:7-alpine
   ```

## Running

```bash
uvicorn app.main:app --reload --port 8000
```

API will be available at: `http://localhost:8000`

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Testing

```bash
pytest
```

Run with coverage:
```bash
pytest --cov=app --cov-report=html
```

## Environment Variables

See `.env.example` for all available configuration options.

Key variables:
- `REDIS_URL`: Redis connection string (default: `redis://localhost:6379/0`)
- `JWT_SECRET`: Secret key for JWT token validation
- `STORAGE_BASE_URL`: Base URL for object storage (optional in Week 1)
- `STORAGE_BUCKET`: Storage bucket name (optional in Week 1)

## Architecture

### Core Components

- **API Layer** (`app/api/v1/`): REST endpoints with versioning
- **Services** (`app/services/`): Business logic (OCR, TTS, caching)
- **Clients** (`app/clients/`): External service clients (Redis, storage)
- **Models** (`app/models/`): Pydantic request/response schemas
- **Core** (`app/core/`): Configuration, logging, security

### Redis Usage

- **Caching**: OCR results cached with TTL (default: 30 min)
- **Rate Limiting**: Per-user sliding window (default: 30 req/min)
- **Idempotency**: Request deduplication via idempotency keys
- **Distributed Locks**: Prevent duplicate ML inference jobs

### Request Flow

1. Request arrives with optional `x-request-id` header
2. Middleware adds request ID if missing, includes in response
3. JWT authentication extracts user subject
4. Rate limiting checks Redis
5. Idempotency check (if key provided)
6. Cache check for OCR results
7. If cache miss: acquire distributed lock, run OCR, cache result
8. Return response with request ID

## API Endpoints

### `POST /v1/upload-url`

Get presigned URL for image upload.

**Request**:
```json
{
  "content_type": "image/jpeg",
  "suffix": "jpg"
}
```

**Response**:
```json
{
  "upload_url": "https://storage.example.com/bucket/capture/...",
  "image_url": "https://storage.example.com/bucket/capture/...",
  "expiration": 300
}
```

### `POST /v1/ocr`

Run OCR on uploaded image.

**Headers**:
- `Authorization: Bearer <token>` (required)
- `Idempotency-Key: <key>` (optional)

**Request**:
```json
{
  "image_url": "https://storage.example.com/bucket/image.jpg",
  "locale": "en"
}
```

**Response**:
```json
{
  "text": "Extracted text here",
  "confidence": 0.95,
  "request_id": "uuid-here",
  "cache_hit": false,
  "ttl_seconds": 1800
}
```

### `POST /v1/tts`

Text-to-speech synthesis (placeholder in Week 1).

## Development

### Code Style

- Follow PEP 8
- Use type hints
- Add docstrings for public functions
- Keep functions focused and small

### Logging

All logs include request IDs for tracing. Log levels:
- `INFO`: Normal operations
- `WARNING`: Recoverable issues
- `ERROR`: Failures requiring attention

### Adding New Endpoints

1. Create Pydantic models in `app/models/`
2. Add service logic in `app/services/`
3. Create endpoint in `app/api/v1/`
4. Add tests in `tests/`
5. Update this README



