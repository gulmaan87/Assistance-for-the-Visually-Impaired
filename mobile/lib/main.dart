import 'package:flutter/material.dart';

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
  // TODO: wire voice commands, haptics, network-aware OCR/TT S flow.
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: Text(
          'Voice-first capture coming soon',
          style: Theme.of(context).textTheme.headlineSmall,
        ),
      ),
    );
  }
}

