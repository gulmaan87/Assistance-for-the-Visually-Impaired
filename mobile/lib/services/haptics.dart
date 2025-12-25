import 'package:vibration/vibration.dart';

class Haptics {
  Future<void> success() async {
    if (await Vibration.hasVibrator() ?? false) {
      Vibration.vibrate(duration: 50);
    }
  }

  Future<void> error() async {
    if (await Vibration.hasVibrator() ?? false) {
      Vibration.vibrate(pattern: [0, 40, 30, 80]);
    }
  }
}




