import 'package:flutter/material.dart';
import 'package:medical_chatbot/main.dart';
import 'chat_screen.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Randevu Sonucu',
          style: TextStyle(color: scheme.onSurface, fontSize: 16),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: GestureDetector(
              onTap: () {
                themeNotifier.value = isDark ? ThemeMode.light : ThemeMode.dark;
              },
              child: Icon(
                isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                color: scheme.primary,
                size: 22,
              ),
            ),
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Agent chip
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
              decoration: BoxDecoration(
                color: const Color(0xFF6C63FF).withOpacity(0.1),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(
                  color: const Color(0xFF6C63FF).withOpacity(0.3),
                ),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: const [
                  Icon(
                    Icons.calendar_today_outlined,
                    color: Color(0xFF6C63FF),
                    size: 15,
                  ),
                  SizedBox(width: 8),
                  Text(
                    'Appointment Agent tarafından işlendi',
                    style: TextStyle(
                      color: Color(0xFF6C63FF),
                      fontSize: 13,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36),

            // Check icon
            Center(
              child: Container(
                width: 86,
                height: 86,
                decoration: BoxDecoration(
                  color: scheme.primary,
                  shape: BoxShape.circle,
                  boxShadow: [
                    BoxShadow(
                      color: scheme.primary.withOpacity(0.3),
                      blurRadius: 20,
                      spreadRadius: 2,
                    ),
                  ],
                ),
                child: Icon(
                  Icons.check_rounded,
                  color: isDark ? const Color(0xFF0A0E1A) : Colors.white,
                  size: 48,
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Randevunuz Oluşturuldu!',
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 22,
                fontWeight: FontWeight.bold,
                color: scheme.onSurface,
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Hastane sistemi ile senkronize edildi.',
              textAlign: TextAlign.center,
              style: TextStyle(
                color: scheme.onSurface.withOpacity(0.45),
                fontSize: 13,
              ),
            ),
            const SizedBox(height: 32),

            // Detail card
            Card(
              elevation: isDark ? 0 : 2,
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(18),
                side: isDark
                    ? BorderSide(
                        color: const Color(0xFF6C63FF).withOpacity(0.25),
                      )
                    : BorderSide.none,
              ),
              child: Padding(
                padding: const EdgeInsets.all(22),
                child: Column(
                  children: [
                    _row(context, 'Tarih', '14 Mayıs 2026'),
                    _divider(context),
                    _row(context, 'Saat', '10:30'),
                    _divider(context),
                    _row(context, 'Bölüm', 'Kardiyoloji'),
                    _divider(context),
                    _row(context, 'Doktor', 'Dr. Ahmet Yılmaz'),
                    _divider(context),
                    _row(context, 'Hastane', 'Şehir Hastanesi'),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 32),
            ElevatedButton.icon(
              onPressed: () {
                Navigator.pushAndRemoveUntil(
                  context,
                  MaterialPageRoute(builder: (_) => const ChatScreen()),
                  (route) => false,
                );
              },
              icon: const Icon(Icons.chat_rounded, size: 18),
              label: const Text(
                'Sohbete Dön',
                style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: scheme.primary,
                foregroundColor: isDark
                    ? const Color(0xFF0A0E1A)
                    : Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(14),
                ),
                elevation: isDark ? 0 : 2,
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  Widget _row(BuildContext ctx, String label, String value) {
    final scheme = Theme.of(ctx).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: TextStyle(
              color: scheme.onSurface.withOpacity(0.5),
              fontSize: 15,
            ),
          ),
          Text(
            value,
            style: TextStyle(
              color: scheme.onSurface,
              fontSize: 15,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _divider(BuildContext ctx) {
    return Divider(
      color: Theme.of(ctx).colorScheme.onSurface.withOpacity(0.08),
      height: 24,
    );
  }
}
