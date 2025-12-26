import 'dart:io';
import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:path/path.dart' as p;
import 'package:mime/mime.dart';

typedef UploadUrlResult = ({String uploadUrl, String imageUrl, int expiration});

class UploadService {
  final String baseUrl;
  final String authToken;
  final http.Client _client;

  UploadService(
      {required this.baseUrl, required this.authToken, http.Client? client})
      : _client = client ?? http.Client();

  Future<UploadUrlResult> getUploadUrl(String filePath) async {
    final ext = p.extension(filePath).replaceFirst('.', '');
    final suffix = ext.isEmpty ? 'jpg' : ext;
    final contentType = lookupMimeType(filePath) ?? 'image/jpeg';
    final resp = await _client.post(
      Uri.parse('$baseUrl/v1/upload-url'),
      headers: {
        'content-type': 'application/json',
        'authorization': 'Bearer $authToken',
      },
      body: jsonEncode({
        'content_type': contentType,
        'suffix': suffix,
      }),
    );
    if (resp.statusCode != 200) {
      throw Exception('Failed to get upload URL: ${resp.body}');
    }
    final map = jsonDecode(resp.body) as Map<String, dynamic>;
    return (
      uploadUrl: map['upload_url'] as String,
      imageUrl: map['image_url'] as String,
      expiration: map['expiration'] as int,
    );
  }

  Future<void> uploadToUrl(String uploadUrl, File image,
      {String? contentType}) async {
    final bytes = await image.readAsBytes();
    final resp = await _client.put(
      Uri.parse(uploadUrl),
      headers: {
        'content-type':
            contentType ?? lookupMimeType(image.path) ?? 'image/jpeg',
      },
      body: bytes,
    );
    if (resp.statusCode < 200 || resp.statusCode >= 300) {
      throw Exception('Upload failed: ${resp.statusCode} ${resp.reasonPhrase}');
    }
  }
}
