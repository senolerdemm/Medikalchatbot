import 'package:flutter/material.dart';
import 'package:medical_chatbot/main.dart';

class AppointmentsScreen extends StatelessWidget {
  const AppointmentsScreen({super.key});

  // Dummy randevular
  static final List<Map<String, String>> _appointments = [
    {
      'doctor': 'Dr. Ahmet Yılmaz',
      'branch': 'Kardiyoloji',
      'hospital': 'Şehir Hastanesi',
      'date': '14 Mayıs 2026',
      'time': '10:30',
      'status': 'Onaylandı',
    },
    {
      'doctor': 'Dr. Elif Demir',
      'branch': 'Nöroloji',
      'hospital': 'Üniversite Hastanesi',
      'date': '22 Mayıs 2026',
      'time': '14:00',
      'status': 'Beklemede',
    },
    {
      'doctor': 'Dr. Mehmet Kaya',
      'branch': 'Göz Hastalıkları',
      'hospital': 'Özel Sağlık Merkezi',
      'date': '3 Haziran 2026',
      'time': '09:15',
      'status': 'Onaylandı',
    },
  ];

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        title: Text(
          'Randevularım',
          style: TextStyle(
            color: scheme.onSurface,
            fontSize: 17,
            fontWeight: FontWeight.bold,
          ),
        ),
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: GestureDetector(
              onTap: () => themeNotifier.value = isDark
                  ? ThemeMode.light
                  : ThemeMode.dark,
              child: Icon(
                isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                color: scheme.primary,
                size: 22,
              ),
            ),
          ),
        ],
      ),
      body: _appointments.isEmpty
          ? Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(
                    Icons.calendar_today_outlined,
                    size: 64,
                    color: scheme.onSurface.withOpacity(0.2),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'Henüz randevunuz yok',
                    style: TextStyle(
                      color: scheme.onSurface.withOpacity(0.4),
                      fontSize: 16,
                    ),
                  ),
                ],
              ),
            )
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _appointments.length,
              itemBuilder: (ctx, i) {
                final a = _appointments[i];
                final isConfirmed = a['status'] == 'Onaylandı';
                final statusColor = isConfirmed
                    ? const Color(0xFF00A676)
                    : const Color(0xFFFFB347);

                return Container(
                  margin: const EdgeInsets.only(bottom: 14),
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: isDark ? const Color(0xFF141928) : Colors.white,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: isDark
                        ? []
                        : [
                            BoxShadow(
                              color: Colors.black.withOpacity(0.06),
                              blurRadius: 8,
                              offset: const Offset(0, 2),
                            ),
                          ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      // Üst: Doktor + durum
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Expanded(
                            child: Text(
                              a['doctor']!,
                              style: TextStyle(
                                color: scheme.onSurface,
                                fontWeight: FontWeight.bold,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 4,
                            ),
                            decoration: BoxDecoration(
                              color: statusColor.withOpacity(0.12),
                              borderRadius: BorderRadius.circular(20),
                            ),
                            child: Text(
                              a['status']!,
                              style: TextStyle(
                                color: statusColor,
                                fontSize: 12,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      // Branş
                      Text(
                        a['branch']!,
                        style: TextStyle(
                          color: scheme.primary,
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                      const SizedBox(height: 12),
                      // Alt: tarih, saat, hastane
                      Row(
                        children: [
                          Icon(
                            Icons.calendar_today_outlined,
                            size: 14,
                            color: scheme.onSurface.withOpacity(0.4),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            a['date']!,
                            style: TextStyle(
                              color: scheme.onSurface.withOpacity(0.55),
                              fontSize: 13,
                            ),
                          ),
                          const SizedBox(width: 16),
                          Icon(
                            Icons.access_time_outlined,
                            size: 14,
                            color: scheme.onSurface.withOpacity(0.4),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            a['time']!,
                            style: TextStyle(
                              color: scheme.onSurface.withOpacity(0.55),
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Row(
                        children: [
                          Icon(
                            Icons.local_hospital_outlined,
                            size: 14,
                            color: scheme.onSurface.withOpacity(0.4),
                          ),
                          const SizedBox(width: 6),
                          Text(
                            a['hospital']!,
                            style: TextStyle(
                              color: scheme.onSurface.withOpacity(0.55),
                              fontSize: 13,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                );
              },
            ),
    );
  }
}
