import 'package:flutter/material.dart';
import 'package:medical_chatbot/presentation/screens/onboarding_screen.dart';

final ValueNotifier<ThemeMode> themeNotifier = ValueNotifier(ThemeMode.light);

void main() {
  runApp(const MedicalChatbotApp());
}

class MedicalChatbotApp extends StatelessWidget {
  const MedicalChatbotApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ValueListenableBuilder<ThemeMode>(
      valueListenable: themeNotifier,
      builder: (_, mode, __) {
        return MaterialApp(
          title: 'MedAssist AI',
          debugShowCheckedModeBanner: false,
          themeMode: mode,

          // --- LIGHT THEME ---
          theme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.light,
            colorScheme:
                ColorScheme.fromSeed(
                  seedColor: const Color(0xFF00A676),
                  brightness: Brightness.light,
                ).copyWith(
                  primary: const Color(0xFF00A676),
                  secondary: const Color(0xFF6C63FF),
                  surface: Colors.white,
                ),
            scaffoldBackgroundColor: const Color(0xFFF5F8FA),
            appBarTheme: const AppBarTheme(
              backgroundColor: Colors.white,
              foregroundColor: Color(0xFF1A202C),
              elevation: 0,
              shadowColor: Colors.black12,
            ),
            cardColor: Colors.white,
          ),

          // --- DARK THEME ---
          darkTheme: ThemeData(
            useMaterial3: true,
            brightness: Brightness.dark,
            colorScheme:
                ColorScheme.fromSeed(
                  seedColor: const Color(0xFF00E5C3),
                  brightness: Brightness.dark,
                ).copyWith(
                  primary: const Color(0xFF00E5C3),
                  secondary: const Color(0xFF6C63FF),
                  surface: const Color(0xFF141928),
                ),
            scaffoldBackgroundColor: const Color(0xFF0A0E1A),
            appBarTheme: const AppBarTheme(
              backgroundColor: Color(0xFF141928),
              foregroundColor: Color(0xFFE0E6F0),
              elevation: 0,
            ),
            cardColor: const Color(0xFF141928),
          ),

          home: const OnboardingScreen(),
        );
      },
    );
  }
}
