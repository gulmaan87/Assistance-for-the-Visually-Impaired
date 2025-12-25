import 'package:flutter_tts/flutter_tts.dart';

class LocalTts {
  LocalTts() : _tts = FlutterTts();
  final FlutterTts _tts;

  Future<void> speak(String text) async {
    await _tts.setSpeechRate(0.45);
    await _tts.setVolume(0.9);
    await _tts.setPitch(1.0);
    await _tts.speak(text);
  }
}




