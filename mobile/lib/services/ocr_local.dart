import 'package:google_mlkit_text_recognition/google_mlkit_text_recognition.dart';
import 'package:image_picker/image_picker.dart';

/// Result from local OCR processing.
class LocalOcrResult {
  LocalOcrResult({
    required this.text,
    required this.confidence,
    required this.blocks,
  });

  /// Extracted text from the image.
  final String text;

  /// Average confidence score (0.0 to 1.0).
  final double confidence;

  /// Number of text blocks detected.
  final int blocks;
}

/// On-device OCR service using Google ML Kit Text Recognition.
/// Provides offline OCR capability as a fallback when cloud OCR is unavailable.
class LocalOcrService {
  LocalOcrService() : _textRecognizer = TextRecognizer();

  final TextRecognizer _textRecognizer;

  /// Run OCR on a local image file.
  /// Returns null if processing fails or image is invalid.
  Future<LocalOcrResult?> recognizeText(String imagePath) async {
    try {
      final inputImage = InputImage.fromFilePath(imagePath);
      final recognizedText = await _textRecognizer.processImage(inputImage);

      if (recognizedText.text.isEmpty) {
        return null;
      }

      // Calculate average confidence from all blocks
      double totalConfidence = 0.0;
      int blockCount = 0;
      for (final block in recognizedText.blocks) {
        for (final line in block.lines) {
          // ML Kit doesn't provide confidence per element, so we estimate
          // based on detection quality (presence of text = reasonable confidence)
          totalConfidence += 0.85; // Conservative estimate
          blockCount += line.elements.length;
        }
      }

      final avgConfidence = blockCount > 0
          ? totalConfidence / blockCount
          : 0.7; // Default confidence if no elements

      return LocalOcrResult(
        text: recognizedText.text,
        confidence: avgConfidence.clamp(0.0, 1.0),
        blocks: recognizedText.blocks.length,
      );
    } catch (e) {
      // Log error but don't throw - allows graceful fallback
      return null;
    }
  }

  /// Run OCR on an XFile (from image_picker).
  Future<LocalOcrResult?> recognizeTextFromFile(XFile file) async {
    return recognizeText(file.path);
  }

  /// Dispose resources when done.
  void dispose() {
    _textRecognizer.close();
  }
}

