import 'dart:async';

import 'package:flutter/material.dart';

import 'services/api_client.dart';
import 'services/haptics.dart';
import 'services/network.dart';
import 'services/session.dart';
import 'services/tts_local.dart';
import 'services/upload.dart';
import 'services/image_picker_helper.dart';
import 'services/ocr_service.dart' show SmartOcrService, OcrServiceResult, OcrSource;

const _backendBaseUrl = 'http://localhost:8000'; // adjust for emulator/device
const _demoToken = 'demo-token'; // replace with real JWT when available

void main() {
  runApp(const AccessibilityAssistantApp());
}

class AccessibilityAssistantApp extends StatelessWidget {
  const AccessibilityAssistantApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Accessibility Assistant',
      theme: ThemeData.dark(),
      home: const VoiceFirstHome(),
    );
  }
}

class VoiceFirstHome extends StatefulWidget {
  const VoiceFirstHome({super.key});

  @override
  State<VoiceFirstHome> createState() => _VoiceFirstHomeState();
}

class _VoiceFirstHomeState extends State<VoiceFirstHome> {
  final _network = NetworkMonitor();
  final _session = Session();
  final _haptics = Haptics();
  final _tts = LocalTts();
  final _imagePicker = ImagePickerHelper();
  UploadService? _uploadService;
  late final ApiClient _apiClient;
  SmartOcrService? _ocrService;

  StreamSubscription<NetworkStatus>? _networkSub;
  bool _online = false;
  String _lastText = 'No text yet';
  bool _loading = false;
  String? _status;

  @override
  void initState() {
    super.initState();
    _apiClient = ApiClient(baseUrl: _backendBaseUrl, authToken: _demoToken);
    _uploadService =
        UploadService(baseUrl: _backendBaseUrl, authToken: _demoToken);
    _ocrService = SmartOcrService(
      apiClient: _apiClient,
      uploadService: _uploadService!,
      networkMonitor: _network,
    );
    _networkSub = _network.statusStream().listen((status) {
      setState(() {
        _online = status.isOnline;
        _status = status.isOnline
            ? 'Online (${status.type?.name ?? 'unknown'})'
            : 'Offline';
      });
    });
  }

  @override
  void dispose() {
    _networkSub?.cancel();
    _ocrService?.dispose();
    super.dispose();
  }

  Future<void> _runOcr() async {
    setState(() {
      _loading = true;
      _status = _online
          ? 'Ready to capture...'
          : 'Offline: will use local OCR';
    });
    try {
      // Step 1: Capture image from camera
      setState(() {
        _status = 'Opening camera...';
      });
      final imageFile = await _imagePicker.pickImageFromCamera();
      if (imageFile == null) {
        setState(() {
          _status = 'Image capture canceled';
        });
        return;
      }

      // Step 2: Run smart OCR (cloud/local switching)
      final idem = _session.newIdempotencyKey();
      setState(() {
        _status = _online ? 'Running cloud OCR...' : 'Running local OCR...';
      });

      final result = await _ocrService!.recognizeText(
        imageFile: imageFile,
        idempotencyKey: idem,
      );

      _lastText = result.text;
      final sourceLabel = result.source == OcrSource.cloud
          ? 'Cloud OCR'
          : 'Local OCR';
      _status = result.source == OcrSource.cloud &&
              result.cacheHit
          ? '$sourceLabel (cached, TTL ${result.ttlSeconds}s)'
          : '$sourceLabel (confidence: ${(result.confidence * 100).toStringAsFixed(0)}%)';

      // Speak the result with source indication
      final speakText = result.text.isEmpty
          ? 'No text detected'
          : result.text;
      await _tts.speak(speakText);
      await _haptics.success();

      if (mounted) {
        final snackBarText = result.source == OcrSource.local
            ? 'Using local OCR (offline mode)'
            : result.cacheHit
                ? 'Cache hit: result from cache'
                : 'Cloud OCR completed';
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(snackBarText)),
        );
      }
    } catch (e) {
      final errorMsg = 'OCR failed: $e';
      setState(() {
        _status = errorMsg;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg)),
        );
      }
      await _tts.speak('OCR processing failed');
      await _haptics.error();
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  Future<void> _speakLast() async {
    await _tts.speak(_lastText);
  }

  @override
  Widget build(BuildContext context) {
    final statusText = _status ?? (_online ? 'Online' : 'Offline');
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Icon(
                    _online ? Icons.wifi : Icons.wifi_off,
                    color: _online ? Colors.greenAccent : Colors.redAccent,
                  ),
                  const SizedBox(width: 8),
                  Text(statusText),
                ],
              ),
              const SizedBox(height: 24),
              Text(
                'Last text:',
                style: Theme.of(context).textTheme.titleMedium,
              ),
              const SizedBox(height: 8),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(8),
                  color: Colors.grey[850],
                ),
                child: Text(_lastText),
              ),
              const Spacer(),
              if (_loading) const LinearProgressIndicator(minHeight: 4),
              const SizedBox(height: 12),
              _ActionButton(
                label: 'Capture & OCR',
                icon: Icons.camera_alt,
                onPressed: _loading ? null : _runOcr,
              ),
              const SizedBox(height: 12),
              _ActionButton(
                label: 'Speak last',
                icon: Icons.volume_up,
                onPressed: _loading ? null : _speakLast,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.label,
    required this.icon,
    required this.onPressed,
  });

  final String label;
  final IconData icon;
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: double.infinity,
      child: ElevatedButton.icon(
        onPressed: onPressed,
        icon: Icon(icon),
        label: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(label),
        ),
      ),
    );
  }
}
