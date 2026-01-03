# Cloud-Backed Multimodal Accessibility Assistant

A production-grade, cloud-native, AI-powered system that helps visually impaired users understand their surroundings and read text using camera input, multimodal AI models, and audio output.

## Architecture Overview

### System Components

- **Mobile App (Flutter)**: Edge device handling camera capture, offline fallbacks, and voice-first UX
- **Backend API (FastAPI)**: Cloud service providing ML inference endpoints with Redis caching
- **Redis**: Performance layer for caching, rate limiting, idempotency, and distributed locks
- **Storage**: S3-compatible object storage for image uploads (mock in Week 1)

### Data Flow

#### OCR Flow (Week 1)
1. Mobile captures image from camera
2. Mobile requests presigned upload URL from backend
3. Mobile uploads image to storage
4. Mobile calls `/v1/ocr` with image URL and idempotency key
5. Backend checks Redis cache; if miss, runs OCR with distributed lock
6. Backend returns text + confidence + request ID
7. Mobile uses local TTS to speak the result

#### Object Detection Flow (Week 2)
1. Mobile captures image and uploads to storage
2. Mobile calls `/v1/object-detection` with image URL
3. Backend checks Redis cache; if miss, runs YOLOv8 with distributed lock
4. Backend returns list of detected objects with bounding boxes and confidence scores
5. Mobile formats and speaks the results via TTS

#### Scene Captioning Flow (Week 2)
1. Mobile captures image and uploads to storage
2. Mobile calls `/v1/scene-caption` with image URL
3. Backend checks Redis cache; if miss, runs BLIP model with distributed lock
4. Backend returns natural language caption with confidence score
5. Mobile speaks the caption via TTS

#### Natural Language Query Flow (Week 2)
1. Mobile captures image and uploads to storage
2. User asks a question about the image (voice or text)
3. Mobile calls `/v1/multimodal-llm/query` with image URL and question
4. Backend checks Redis cache; if miss, runs BLIP-2 model with distributed lock
5. Backend returns answer to the question
6. Mobile speaks the answer via TTS

## Week 1 Status

✅ Backend skeleton with FastAPI, Redis integration, OCR/TTS endpoints  
✅ Mobile skeleton with network awareness, image capture, upload flow  
✅ Redis: caching, rate limiting, idempotency, distributed locks  
✅ End-to-end OCR → TTS flow  
✅ Tests for backend OCR endpoint (cache, idempotency, rate limit)

## Week 2 Status

✅ Object detection with YOLOv8 (YOLOv8n model)  
✅ Scene captioning with BLIP (Salesforce/blip-image-captioning-base)  
✅ Multimodal LLM integration (BLIP-2 for image understanding)  
✅ Natural language query endpoint  
✅ All endpoints include Redis caching, rate limiting, idempotency, and distributed locking  
✅ Consistent error handling and timeout management

## Week 3 Status

✅ On-device OCR fallback using Google ML Kit (offline capability)  
✅ Network-aware switching (cloud vs local OCR based on connectivity)  
✅ Async job processing queue for long-running ML tasks  
✅ Redis-backed job state tracking with TTL  
✅ Enhanced logging with edge-cloud intelligence metrics  
✅ Graceful degradation when network is unavailable

## Quick Start

### Backend Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Copy .env.example to .env and configure
cp .env.example .env

# Start Redis (Docker recommended)
docker run -d -p 6379:6379 redis:7-alpine

# Run backend
uvicorn app.main:app --reload --port 8000
```

### Mobile Setup

```bash
cd mobile
flutter pub get

# Update backend URL in lib/main.dart if needed
# Run on device/emulator
flutter run
```

## API Endpoints

### Week 1 Endpoints
- `POST /v1/upload-url` - Get presigned URL for image upload
- `POST /v1/ocr` - Run OCR on uploaded image
- `POST /v1/tts` - Text-to-speech synthesis (placeholder)

### Week 2 Endpoints
- `POST /v1/object-detection` - Detect objects in image using YOLOv8
  - Request: `{image_url, confidence_threshold?}`
  - Response: `{objects: [{class_name, confidence, bbox}], total_objects, ...}`
  
- `POST /v1/scene-caption` - Generate natural language caption for image using BLIP
  - Request: `{image_url, max_length?}`
  - Response: `{caption, confidence, ...}`
  
- `POST /v1/multimodal-llm` - Answer prompts about images using multimodal LLM
  - Request: `{image_url, prompt, max_tokens?, temperature?}`
  - Response: `{response, confidence?, ...}`
  
- `POST /v1/multimodal-llm/query` - Natural language question answering about images
  - Request: `{image_url, question, max_tokens?}`
  - Response: `{answer, confidence?, ...}`

### Week 3 Endpoints
- `POST /v1/async-jobs` - Create async job for long-running ML processing
  - Request: `{job_type, image_url, parameters?}`
  - Response: `{job_id, status, created_at, estimated_completion_seconds}`
  
- `GET /v1/async-jobs/{job_id}` - Get async job status and result
  - Response: `{job_id, status, created_at, completed_at?, result?, error?, progress_percent?}`

API docs available at: `http://localhost:8000/docs` (Swagger UI)

## Testing

```bash
cd backend
pytest
```

## Environment Variables

See `backend/.env.example` for required configuration.

## Tech Stack

- **Backend**: FastAPI, Redis, Python 3.12+
- **Mobile**: Flutter 3.2+
- **AI/ML**: 
  - OCR: PaddleOCR/Tesseract (placeholder in Week 1)
  - Object Detection: YOLOv8 (Ultralytics)
  - Scene Captioning: BLIP (Salesforce/blip-image-captioning-base)
  - Multimodal LLM: BLIP-2 (Salesforce/blip2-opt-2.7b)
- **Storage**: S3-compatible (mock in Week 1)

## Project Structure

```
Assistance-for-the-Visually-Impaired/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # API endpoints
│   │   ├── clients/          # External service clients (Redis, storage)
│   │   ├── core/             # Config, logging, security
│   │   ├── models/           # Pydantic models
│   │   └── services/         # Business logic (OCR, TTS, cache)
│   └── tests/                # Integration tests
└── mobile/
    └── lib/
        ├── main.dart         # App entrypoint
        └── services/         # API client, network, TTS, upload
```

## Next Steps (Week 4+)

- Implement actual OCR with PaddleOCR or Tesseract (replace placeholder)
- Performance optimization and model quantization
- Enhanced error handling and fallback strategies
- User preferences and model selection
- Voice command interface
- Continuous scene description mode
- Privacy enhancements (anonymization, auto data deletion)
- Production monitoring and alerting

