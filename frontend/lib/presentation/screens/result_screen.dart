import 'package:flutter/material.dart';

class ResultScreen extends StatelessWidget {
  const ResultScreen({super.key, required this.bookingPayload});

  final Map<String, dynamic> bookingPayload;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final rawSlot = bookingPayload['slot'];
    final slot = rawSlot is Map
        ? Map<String, dynamic>.from(rawSlot)
        : <String, dynamic>{};

    return Scaffold(
      appBar: AppBar(title: const Text('Randevu Sonucu')),
      body: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Container(
              padding: const EdgeInsets.all(18),
              decoration: BoxDecoration(
                color: scheme.primary.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(18),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Randevu Onaylandı',
                    style: TextStyle(
                      color: scheme.primary,
                      fontWeight: FontWeight.bold,
                      fontSize: 18,
                    ),
                  ),
                  const SizedBox(height: 14),
                  _DetailRow(
                    label: 'Rezervasyon Kodu',
                    value: bookingPayload['booking_id']?.toString() ?? '-',
                  ),
                  _DetailRow(
                    label: 'Hastane',
                    value: slot['hospital_name']?.toString() ?? '-',
                  ),
                  _DetailRow(
                    label: 'Şehir',
                    value: slot['city']?.toString() ?? '-',
                  ),
                  _DetailRow(
                    label: 'Bölüm',
                    value: slot['specialty']?.toString() ?? '-',
                  ),
                  _DetailRow(
                    label: 'Doktor',
                    value: slot['physician_name']?.toString() ?? '-',
                  ),
                  _DetailRow(
                    label: 'Tarih / Saat',
                    value: _formatDate(slot['start_at']?.toString()),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
            FilledButton.icon(
              onPressed: () => Navigator.pop(context),
              icon: const Icon(Icons.arrow_back),
              label: const Text('Sohbete Dön'),
            ),
          ],
        ),
      ),
    );
  }

  static String _formatDate(String? raw) {
    if (raw == null || raw.isEmpty) {
      return '-';
    }
    try {
      final dateTime = DateTime.parse(raw).toLocal();
      final day = dateTime.day.toString().padLeft(2, '0');
      final month = dateTime.month.toString().padLeft(2, '0');
      final year = dateTime.year.toString();
      final hour = dateTime.hour.toString().padLeft(2, '0');
      final minute = dateTime.minute.toString().padLeft(2, '0');
      return '$day.$month.$year $hour:$minute';
    } catch (_) {
      return raw;
    }
  }
}

class _DetailRow extends StatelessWidget {
  const _DetailRow({
    required this.label,
    required this.value,
  });

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Text('$label: $value'),
    );
  }
}
