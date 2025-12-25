import 'dart:convert';
import 'package:http/http.dart' as http;

class OcrResult {
  OcrResult({
    required this.text,
    required this.confidence,
    required this.cacheHit,
    required this.ttlSeconds,
  });

  final String text;
  final double confidence;
  final bool cacheHit;
  final int ttlSeconds;
}

class ApiClient {
  ApiClient({
    required this.baseUrl,
    required this.authToken,
    http.Client? httpClient,
  }) : _http = httpClient ?? http.Client();

  final String baseUrl;
  final String authToken;
  final http.Client _http;

  Future<OcrResult> runOcr({
    required Uri imageUrl,
    required String idempotencyKey,
    String? locale,
  }) async {
    final uri = Uri.parse('$baseUrl/v1/ocr');
    final resp = await _http.post(
      uri,
      headers: {
        'content-type': 'application/json',
        'authorization': 'Bearer $authToken',
        'idempotency-key': idempotencyKey,
      },
      body: jsonEncode({
        'image_url': imageUrl.toString(),
        if (locale != null) 'locale': locale,
      }),
    );

    if (resp.statusCode != 200) {
      throw Exception('OCR failed: ${resp.statusCode} ${resp.body}');
    }
    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    return OcrResult(
      text: data['text'] as String,
      confidence: (data['confidence'] as num).toDouble(),
      cacheHit: data['cache_hit'] as bool? ?? false,
      ttlSeconds: data['ttl_seconds'] as int? ?? 0,
    );
  }
}




