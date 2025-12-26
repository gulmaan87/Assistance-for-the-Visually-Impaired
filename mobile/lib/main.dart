import 'dart:async';

import 'package:flutter/material.dart';

import 'services/api_client.dart';
import 'services/haptics.dart';
import 'services/network.dart';
import 'services/session.dart';
import 'services/tts_local.dart';
import 'services/upload.dart';
import 'services/image_picker_helper.dart';

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
    super.dispose();
  }

  Future<void> _runOcr() async {
    setState(() {
      _loading = true;
      _status = _online ? 'Ready to capture...' : 'Offline: using local text';
    });
    try {
      if (!_online) {
        _lastText = 'Offline. Please connect to run OCR.';
        await _tts.speak(_lastText);
        await _haptics.error();
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(content: Text('Offline: Please connect to run OCR')),
          );
        }
        return;
      }

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

      // Step 2: Get upload URL from backend
      final uploadService = _uploadService!;
      late String uploadUrl, imageUrl;
      try {
        setState(() {
          _status = 'Getting upload URL...';
        });
        final urlRes = await uploadService.getUploadUrl(imageFile.path);
        uploadUrl = urlRes.uploadUrl;
        imageUrl = urlRes.imageUrl;
      } catch (e) {
        final errorMsg = 'Failed to get upload URL: $e';
        setState(() {
          _status = errorMsg;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(errorMsg)),
          );
        }
        await _tts.speak('Upload URL request failed');
        await _haptics.error();
        return;
      }

      // Step 3: Upload image to storage
      try {
        setState(() {
          _status = 'Uploading image...';
        });
        await uploadService.uploadToUrl(uploadUrl, imageFile);
      } catch (e) {
        final errorMsg = 'Upload failed: $e';
        setState(() {
          _status = errorMsg;
        });
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(errorMsg)),
          );
        }
        await _tts.speak('Image upload failed');
        await _haptics.error();
        return;
      }

      // Step 4: Run OCR on uploaded image
      final idem = _session.newIdempotencyKey();
      try {
        setState(() {
          _status = 'Running OCR...';
        });
        final result = await _apiClient.runOcr(
          imageUrl: Uri.parse(imageUrl),
          idempotencyKey: idem,
        );
        _lastText = result.text;
        _status = result.cacheHit
            ? 'Cache hit (TTL ${result.ttlSeconds}s)'
            : 'OCR fresh result';
        await _tts.speak(result.text);
        await _haptics.success();
        if (mounted && result.cacheHit) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text('Cache hit: result from cache')),
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
      }
    } catch (e) {
      final errorMsg = 'Unexpected error: $e';
      setState(() {
        _status = errorMsg;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(errorMsg)),
        );
      }
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
