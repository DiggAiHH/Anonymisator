# Anonymisator - SecureDoc Flow MedTech AI Privacy Proxy

A privacy-first medical document processing system with PHI anonymization and a minimal MCP tool server.

## Features

- **Backend Privacy Proxy**: FastAPI-based service that anonymizes PHI before LLM calls
- **MCP Tool Server**: Minimal TypeScript server exposing data-minimizing tool endpoints
- **Android SDK**: Native Android app and SDK for mobile integration
- **In-Memory Processing**: No persistence of PHI or mappings
- **Stripe Integration**: Secure webhook handling with signature verification

## Architecture

### Backend Privacy Proxy (FastAPI)
- Accepts medical text input
- Anonymizes PHI in-memory with collision-resistant placeholders
- Sends only anonymized text to external LLMs
- Re-identifies LLM responses back to original values
- Zero persistence of sensitive data

### MCP Tool Server (TypeScript)
- Exposes tool endpoints for integration
- Returns only free time slots (no patient data)
- Designed for future Postgres integration

### Android SDK (Kotlin)
- Native Android app for mobile PHI-protected document processing
- Clean Kotlin SDK with coroutines support
- Retrofit-based networking with proper error handling
- Ready-to-install APK for Android 7.0+

## Setup

### Prerequisites
- Python 3.9+
- Node.js 18+
- pip
- npm
- (For Android) Android Studio with JDK 17

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Create `.env` file:
```bash
# LLM Configuration
LLM_API_URL=https://api.openai.com/v1/chat/completions
LLM_API_KEY=your_api_key_here
LLM_MODEL=gpt-4

# Stripe Configuration
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_API_KEY=sk_test_your_stripe_key

# Server Configuration
HOST=0.0.0.0
PORT=8000
```

3. Run the backend:
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

### MCP Server Setup

1. Install Node.js dependencies:
```bash
npm install
```

2. Build TypeScript:
```bash
npm run build
```

3. Run the MCP server:
```bash
npm start
```

Or for development:
```bash
npm run dev
```

### Android SDK Setup

1. Open the `android/` folder in Android Studio

2. Sync Gradle files and build:
```bash
cd android
./gradlew assembleDebug
```

3. Install on device/emulator:
```bash
adb install app/build/outputs/apk/debug/app-debug.apk
```

4. Or run directly from Android Studio

For more details, see [Android README](android/README.md).

## API Documentation

### Backend Privacy Proxy

#### POST /v1/securedoc/generate
Generates LLM responses with PHI protection.

**Request:**
```json
{
  "practice_id": "practice_123",
  "task": "summarize",
  "text": "Patient John Doe, DOB 01/15/1980, presented with..."
}
```

**Response:**
```json
{
  "output_text": "Patient John Doe, DOB 01/15/1980, presented with...",
  "status": "success"
}
```

#### POST /v1/billing/stripe/webhook
Stripe webhook endpoint with signature verification.

**Headers:**
- `Stripe-Signature`: Webhook signature

### MCP Tool Server

#### GET /tools/get_free_slots
Returns available appointment slots (data-minimized).

**Query Parameters:**
- `date` (optional): Date to check (YYYY-MM-DD format)

**Response:**
```json
{
  "slots": [
    {"time": "09:00", "duration_minutes": 30},
    {"time": "10:30", "duration_minutes": 30},
    {"time": "14:00", "duration_minutes": 30}
  ]
}
```

## Security

- PHI mappings stored in RAM only (no disk persistence)
- Request bodies not logged
- Stripe webhook signature verification
- Replay attack protection
- Input size limits enforced
- Control character validation

## Development

### Running Tests
```bash
# Backend tests
python -m pytest tests/

# MCP server tests (if added)
npm test
```

### Docker Compose (Optional)
```bash
docker-compose up
```

## License

See LICENSE file for details.
