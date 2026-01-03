import 'dart:io';
import 'package:image_picker/image_picker.dart';
import 'api_client.dart';
import 'network.dart';
import 'ocr_local.dart';
import 'upload.dart';

/// Source of OCR result.
enum OcrSource {
  cloud,
  local,
}

/// Result from OCR processing (cloud or local).
class OcrServiceResult {
  OcrServiceResult({
    required this.text,
    required this.confidence,
    required this.source,
    this.cacheHit = false,
    this.ttlSeconds = 0,
  });

  final String text;
  final double confidence;
  final OcrSource source;
  final bool cacheHit;
  final int ttlSeconds;
}

/// Unified OCR service that intelligently switches between cloud and local OCR
/// based on network conditions and quality.
class SmartOcrService {
  SmartOcrService({
    required ApiClient apiClient,
    required UploadService uploadService,
    required NetworkMonitor networkMonitor,
    LocalOcrService? localOcr,
  })  : _apiClient = apiClient,
        _uploadService = uploadService,
        _networkMonitor = networkMonitor,
        _localOcr = localOcr ?? LocalOcrService();

  final ApiClient _apiClient;
  final UploadService _uploadService;
  final NetworkMonitor _networkMonitor;
  final LocalOcrService _localOcr;

  /// Run OCR with intelligent cloud/local switching.
  /// 
  /// Strategy:
  /// - If offline: use local OCR immediately
  /// - If online with good connection: prefer cloud (better accuracy)
  /// - If online with poor connection: try cloud with timeout, fallback to local
  /// - If cloud fails: fallback to local
  Future<OcrServiceResult> recognizeText({
    required XFile imageFile,
    required String idempotencyKey,
    Duration cloudTimeout = const Duration(seconds: 3),
  }) async {
    // Check network status
    final networkStatus = await _networkMonitor.statusStream().first;
    final isOnline = networkStatus.isOnline;

    // Strategy 1: Offline - use local OCR immediately
    if (!isOnline) {
      return _runLocalOcr(imageFile);
    }

    // Strategy 2: Online - try cloud first, fallback to local on failure
    try {
      // Try cloud OCR with timeout
      final cloudResult = await _runCloudOcr(
        imageFile: imageFile,
        idempotencyKey: idempotencyKey,
        timeout: cloudTimeout,
      ).timeout(cloudTimeout);

      // Cloud succeeded - return result
      return cloudResult;
    } catch (e) {
      // Cloud failed - fallback to local OCR
      // Log the error but don't throw - graceful degradation
      return _runLocalOcr(imageFile);
    }
  }

  /// Run cloud OCR (upload + API call).
  Future<OcrServiceResult> _runCloudOcr({
    required XFile imageFile,
    required String idempotencyKey,
    required Duration timeout,
  }) async {
    // Step 1: Get upload URL
    final urlRes = await _uploadService
        .getUploadUrl(imageFile.path)
        .timeout(timeout);

    // Step 2: Upload image
    final file = File(imageFile.path);
    await _uploadService
        .uploadToUrl(urlRes.uploadUrl, file)
        .timeout(timeout);

    // Step 3: Run OCR API
    final apiResult = await _apiClient
        .runOcr(
          imageUrl: Uri.parse(urlRes.imageUrl),
          idempotencyKey: idempotencyKey,
        )
        .timeout(timeout);

    return OcrServiceResult(
      text: apiResult.text,
      confidence: apiResult.confidence,
      source: OcrSource.cloud,
      cacheHit: apiResult.cacheHit,
      ttlSeconds: apiResult.ttlSeconds,
    );
  }

  /// Run local OCR.
  Future<OcrServiceResult> _runLocalOcr(XFile imageFile) async {
    final localResult = await _localOcr.recognizeText(imageFile.path);

    if (localResult == null) {
      throw Exception('Local OCR failed: no text detected');
    }

    return OcrServiceResult(
      text: localResult.text,
      confidence: localResult.confidence,
      source: OcrSource.local,
    );
  }

  /// Dispose resources.
  void dispose() {
    _localOcr.dispose();
  }
}

