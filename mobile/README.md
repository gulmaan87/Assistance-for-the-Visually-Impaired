# Mobile App

Flutter-based mobile application with voice-first UX, network awareness, and offline fallbacks.

## Setup

1. **Install Flutter** (if not already installed):
   - Follow instructions at: https://flutter.dev/docs/get-started/install

2. **Install dependencies**:
   ```bash
   flutter pub get
   ```

3. **Configure backend URL**:
   - Edit `lib/main.dart`
   - Update `_backendBaseUrl` constant (default: `http://localhost:8000`)
   - For Android emulator: use `http://10.0.2.2:8000`
   - For iOS simulator: use `http://localhost:8000`
   - For physical device: use your computer's local IP address

4. **Configure authentication token**:
   - Edit `lib/main.dart`
   - Update `_demoToken` constant with real JWT (Week 1 uses stub)

## Running

```bash
flutter run
```

Run on specific device:
```bash
flutter devices  # List available devices
flutter run -d <device-id>
```

## Architecture

### Key Components

- **Main App** (`lib/main.dart`): Voice-first UI with camera capture and OCR flow
- **Services**:
  - `api_client.dart`: Backend API communication
  - `upload.dart`: Image upload to storage
  - `network.dart`: Connectivity monitoring
  - `tts_local.dart`: Local text-to-speech
  - `haptics.dart`: Haptic feedback
  - `session.dart`: Idempotency key management
  - `image_picker_helper.dart`: Camera image capture

### User Flow

1. User taps "Capture & OCR" button
2. Camera opens to capture image
3. App requests upload URL from backend
4. App uploads image to storage
5. App calls OCR endpoint with image URL
6. App receives text result
7. Local TTS speaks the text
8. Haptic feedback confirms success

### Network Awareness

- App monitors connectivity status
- Shows online/offline indicator
- Gracefully handles offline scenarios
- Falls back to cached/last results when offline

### Accessibility Features

- **Voice-first**: All interactions have audio feedback
- **Haptic feedback**: Critical actions trigger vibrations
- **Clear status**: Network and processing status clearly displayed
- **Error handling**: All errors announced via TTS + visual snackbars

## Dependencies

Key packages:
- `http`: API communication
- `connectivity_plus`: Network status monitoring
- `flutter_tts`: Local text-to-speech
- `vibration`: Haptic feedback
- `image_picker`: Camera access
- `uuid`: Idempotency key generation
- `mime`: Content type detection
- `path`: File path utilities

## Configuration

### Backend URL

Update the constant in `lib/main.dart`:

```dart
const _backendBaseUrl = 'http://your-backend-url:8000';
```

### Authentication

Replace demo token with real JWT:

```dart
const _demoToken = 'your-jwt-token-here';
```

## Development

### Code Style

- Follow Flutter/Dart style guide
- Use meaningful variable names
- Keep widgets focused and reusable
- Handle errors gracefully with user feedback

### Testing

Run tests:
```bash
flutter test
```

### Build

Android APK:
```bash
flutter build apk --release
```

iOS (requires macOS):
```bash
flutter build ios --release
```

## Known Limitations (Week 1)

- Backend URL hardcoded (should use config/environment)
- JWT token hardcoded (should use secure storage)
- No offline OCR fallback (TFLite models coming in Week 3)
- Image upload uses mock presigned URLs (real S3 integration pending)

## Next Steps (Week 2+)

- Real S3 presigned URL generation
- Secure token storage
- On-device OCR fallback models
- Voice command recognition
- Enhanced error recovery

