import 'package:flutter/material.dart';


class HistoryScreen extends StatelessWidget {
  const HistoryScreen({
    super.key,
    required this.summaryMessage,
    required this.payload,
  });

  final String summaryMessage;
  final Map<String, dynamic> payload;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final viewModel = _HistoryViewModel.fromPayload(
      payload: payload,
      summaryMessage: summaryMessage,
    );

    return Scaffold(
      appBar: AppBar(
        title: const Text('Geçmiş Özeti'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          _SectionCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 10,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: scheme.primary.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(999),
                  ),
                  child: Text(
                    'Kişisel Geçmiş Ajanı',
                    style: TextStyle(
                      color: scheme.primary,
                      fontWeight: FontWeight.w700,
                      fontSize: 12,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  viewModel.summaryMessage,
                  style: TextStyle(
                    color: scheme.onSurface,
                    height: 1.5,
                    fontSize: 15,
                  ),
                ),
              ],
            ),
          ),
          if (viewModel.focusAreas.isNotEmpty) ...[
            const SizedBox(height: 16),
            _SectionTitle(
              title: 'Odak Alanları',
              subtitle: 'Bu özet şu başlıklara göre hazırlandı.',
            ),
            const SizedBox(height: 10),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: viewModel.focusAreas
                  .map(
                    (focus) => Chip(
                      label: Text(_focusLabel(focus)),
                      backgroundColor: scheme.primary.withValues(alpha: 0.08),
                      side: BorderSide.none,
                      labelStyle: TextStyle(
                        color: scheme.primary,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  )
                  .toList(),
            ),
          ],
          const SizedBox(height: 20),
          _SectionTitle(
            title: 'Profil',
              subtitle: 'Kullanıcı profili ve temel notlar',
          ),
          const SizedBox(height: 10),
          _SectionCard(
            child: Text(
              viewModel.profileSummary,
              style: TextStyle(
                color: scheme.onSurface,
                height: 1.45,
              ),
            ),
          ),
          if (viewModel.medications.isNotEmpty || viewModel.allergyNotes.isNotEmpty) ...[
            const SizedBox(height: 20),
            _SectionTitle(
              title: 'Tedavi ve Duyarlılıklar',
              subtitle: 'Kayıtlarda bulunan ilaç ve alerji bilgileri',
            ),
            const SizedBox(height: 10),
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (viewModel.medications.isNotEmpty) ...[
                    _MiniHeading(
                      icon: Icons.medication_outlined,
                      label: 'Düzenli İlaçlar',
                    ),
                    const SizedBox(height: 8),
                    ...viewModel.medications.map(_BulletText.new),
                  ],
                  if (viewModel.medications.isNotEmpty &&
                      viewModel.allergyNotes.isNotEmpty)
                    const SizedBox(height: 16),
                  if (viewModel.allergyNotes.isNotEmpty) ...[
                    _MiniHeading(
                      icon: Icons.warning_amber_outlined,
                      label: 'Alerji ve Notlar',
                    ),
                    const SizedBox(height: 8),
                    ...viewModel.allergyNotes.map(_BulletText.new),
                  ],
                ],
              ),
            ),
          ],
          if (viewModel.upcomingAppointments.isNotEmpty ||
              viewModel.cancelledAppointments.isNotEmpty) ...[
            const SizedBox(height: 20),
            _SectionTitle(
              title: 'Randevu Geçmişi',
              subtitle: 'Yaklaşan ve iptal edilen kayıtlar',
            ),
            const SizedBox(height: 10),
            if (viewModel.upcomingAppointments.isNotEmpty)
              _AppointmentSection(
                title: 'Yaklaşan Randevular',
                records: viewModel.upcomingAppointments,
              ),
            if (viewModel.upcomingAppointments.isNotEmpty &&
                viewModel.cancelledAppointments.isNotEmpty)
              const SizedBox(height: 12),
            if (viewModel.cancelledAppointments.isNotEmpty)
              _AppointmentSection(
                title: 'İptal Edilenler',
                records: viewModel.cancelledAppointments,
                dimmed: true,
              ),
          ],
          if (viewModel.conversationSummary.isNotEmpty ||
              viewModel.recentMessages.isNotEmpty) ...[
            const SizedBox(height: 20),
            _SectionTitle(
              title: 'Yakın Sohbet Hafızası',
              subtitle: 'Son mesajların özet ve ham görünümü',
            ),
            const SizedBox(height: 10),
            _SectionCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  if (viewModel.conversationSummary.isNotEmpty) ...[
                    _MiniHeading(
                      icon: Icons.forum_outlined,
                      label: 'Konuşma Özeti',
                    ),
                    const SizedBox(height: 8),
                    Text(
                      viewModel.conversationSummary,
                      style: TextStyle(
                        color: scheme.onSurface,
                        height: 1.45,
                      ),
                    ),
                  ],
                  if (viewModel.conversationSummary.isNotEmpty &&
                      viewModel.recentMessages.isNotEmpty)
                    const SizedBox(height: 16),
                  if (viewModel.recentMessages.isNotEmpty) ...[
                    _MiniHeading(
                      icon: Icons.chat_bubble_outline,
                      label: 'Son Mesajlar',
                    ),
                    const SizedBox(height: 8),
                    ...viewModel.recentMessages.map(
                      (message) => _MessageRow(message: message),
                    ),
                  ],
                ],
              ),
            ),
          ],
          const SizedBox(height: 20),
          _SectionTitle(
            title: 'Kayıt Geçmişi',
            subtitle: '${viewModel.historyEntries.length} kayıt gösteriliyor',
          ),
          const SizedBox(height: 10),
          if (viewModel.historyEntries.isEmpty)
            _SectionCard(
              child: Text(
                'Bu kullanıcı için klinik geçmiş kaydı bulunmuyor.',
                style: TextStyle(
                  color: scheme.onSurface.withValues(alpha: 0.72),
                ),
              ),
            )
          else
            ...viewModel.historyEntries.map(
              (entry) => _HistoryEntryCard(entry: entry),
            ),
          const SizedBox(height: 24),
          _SectionCard(
            child: Text(
              'Not: Bu ekran yalnızca backend\'in döndürdüğü profil, geçmiş, sohbet ve randevu payload\'ını gösterir. Kayıtlarda olmayan bilgi burada görünmez.',
              style: TextStyle(
                color: isDark
                    ? scheme.onSurface.withValues(alpha: 0.76)
                    : scheme.onSurface.withValues(alpha: 0.68),
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _focusLabel(String focus) {
    switch (focus) {
      case 'summary':
        return 'Genel Özet';
      case 'medications':
        return 'İlaçlar';
      case 'allergies':
        return 'Alerjiler';
      case 'labs':
        return 'Tahliller';
      case 'appointments':
        return 'Randevular';
      case 'visits':
        return 'Ziyaretler';
      case 'conversation':
        return 'Sohbet Hafızası';
      case 'recommendation':
        return 'Genel Öneri';
      default:
        return focus;
    }
  }
}

class _HistoryViewModel {
  const _HistoryViewModel({
    required this.summaryMessage,
    required this.focusAreas,
    required this.profileSummary,
    required this.medications,
    required this.allergyNotes,
    required this.conversationSummary,
    required this.historyEntries,
    required this.upcomingAppointments,
    required this.cancelledAppointments,
    required this.recentMessages,
  });

  final String summaryMessage;
  final List<String> focusAreas;
  final String profileSummary;
  final List<String> medications;
  final List<String> allergyNotes;
  final String conversationSummary;
  final List<_HistoryEntryVm> historyEntries;
  final List<_AppointmentRecordVm> upcomingAppointments;
  final List<_AppointmentRecordVm> cancelledAppointments;
  final List<_MessageVm> recentMessages;

  factory _HistoryViewModel.fromPayload({
    required Map<String, dynamic> payload,
    required String summaryMessage,
  }) {
    List<String> stringList(Object? raw) {
      if (raw is! List) return const [];
      return raw
          .map((item) => item?.toString().trim() ?? '')
          .where((item) => item.isNotEmpty)
          .toList();
    }

    List<_HistoryEntryVm> historyEntries(Object? raw) {
      if (raw is! List) return const [];
      return raw
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .map(_HistoryEntryVm.fromJson)
          .toList();
    }

    List<_AppointmentRecordVm> appointments(Object? raw) {
      if (raw is! List) return const [];
      return raw
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .map(_AppointmentRecordVm.fromJson)
          .toList();
    }

    List<_MessageVm> messages(Object? raw) {
      if (raw is! List) return const [];
      return raw
          .whereType<Map>()
          .map((item) => Map<String, dynamic>.from(item))
          .map(_MessageVm.fromJson)
          .toList();
    }

    return _HistoryViewModel(
      summaryMessage: summaryMessage,
      focusAreas: stringList(payload['focus_areas']),
      profileSummary:
          payload['profile_summary']?.toString().trim().isNotEmpty == true
          ? payload['profile_summary'].toString()
          : 'Kayıtlı profil bilgisi bulunmuyor.',
      medications: stringList(payload['medications']),
      allergyNotes: stringList(payload['allergy_notes']),
      conversationSummary: payload['conversation_summary']?.toString() ?? '',
      historyEntries: historyEntries(payload['history_entries']),
      upcomingAppointments: appointments(payload['upcoming_appointments']),
      cancelledAppointments: appointments(payload['cancelled_appointments']),
      recentMessages: messages(payload['recent_messages']),
    );
  }
}

class _HistoryEntryVm {
  const _HistoryEntryVm({
    required this.type,
    required this.summary,
    required this.recordedAt,
  });

  final String type;
  final String summary;
  final DateTime? recordedAt;

  factory _HistoryEntryVm.fromJson(Map<String, dynamic> json) {
    return _HistoryEntryVm(
      type: json['type']?.toString() ?? 'history',
      summary: json['summary']?.toString() ?? '',
      recordedAt: DateTime.tryParse(json['recorded_at']?.toString() ?? ''),
    );
  }
}

class _AppointmentRecordVm {
  const _AppointmentRecordVm({
    required this.bookingId,
    required this.status,
    required this.statusLabel,
    required this.displayText,
  });

  final String bookingId;
  final String status;
  final String statusLabel;
  final String displayText;

  factory _AppointmentRecordVm.fromJson(Map<String, dynamic> json) {
    return _AppointmentRecordVm(
      bookingId: json['booking_id']?.toString() ?? '',
      status: json['status']?.toString() ?? '',
      statusLabel: json['status_label']?.toString() ?? '',
      displayText: json['display_text']?.toString() ?? '',
    );
  }
}

class _MessageVm {
  const _MessageVm({
    required this.role,
    required this.content,
    required this.createdAt,
  });

  final String role;
  final String content;
  final DateTime? createdAt;

  factory _MessageVm.fromJson(Map<String, dynamic> json) {
    return _MessageVm(
      role: json['role']?.toString() ?? '',
      content: json['content']?.toString() ?? '',
      createdAt: DateTime.tryParse(json['created_at']?.toString() ?? ''),
    );
  }
}

class _SectionTitle extends StatelessWidget {
  const _SectionTitle({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          title,
          style: TextStyle(
            color: scheme.onSurface,
            fontWeight: FontWeight.w700,
            fontSize: 18,
          ),
        ),
        const SizedBox(height: 4),
        Text(
          subtitle,
          style: TextStyle(
            color: scheme.onSurface.withValues(alpha: 0.66),
          ),
        ),
      ],
    );
  }
}

class _SectionCard extends StatelessWidget {
  const _SectionCard({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF141928) : Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: child,
    );
  }
}

class _MiniHeading extends StatelessWidget {
  const _MiniHeading({
    required this.icon,
    required this.label,
  });

  final IconData icon;
  final String label;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Row(
      children: [
        Icon(icon, size: 18, color: scheme.primary),
        const SizedBox(width: 8),
        Text(
          label,
          style: TextStyle(
            color: scheme.onSurface,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }
}

class _BulletText extends StatelessWidget {
  const _BulletText(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(top: 7),
            child: Container(
              width: 6,
              height: 6,
              decoration: BoxDecoration(
                color: scheme.primary,
                shape: BoxShape.circle,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              text,
              style: TextStyle(
                color: scheme.onSurface,
                height: 1.45,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _AppointmentSection extends StatelessWidget {
  const _AppointmentSection({
    required this.title,
    required this.records,
    this.dimmed = false,
  });

  final String title;
  final List<_AppointmentRecordVm> records;
  final bool dimmed;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return _SectionCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: scheme.onSurface,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 10),
          ...records.map(
            (record) => Padding(
              padding: const EdgeInsets.only(bottom: 10),
              child: Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: dimmed
                      ? scheme.onSurface.withValues(alpha: 0.04)
                      : scheme.primary.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      record.displayText,
                      style: TextStyle(
                        color: scheme.onSurface,
                        height: 1.4,
                      ),
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Durum: ${record.statusLabel.isNotEmpty ? record.statusLabel : _statusLabel(record.status)}',
                      style: TextStyle(
                        color: scheme.onSurface.withValues(alpha: 0.62),
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      'Rezervasyon Kodu: ${record.bookingId}',
                      style: TextStyle(
                        color: scheme.onSurface.withValues(alpha: 0.58),
                        fontSize: 12,
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _MessageRow extends StatelessWidget {
  const _MessageRow({required this.message});

  final _MessageVm message;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final normalizedRole = message.role.trim().toLowerCase();
    final isUser = normalizedRole == 'user' || normalizedRole == 'kullanıcı' || normalizedRole == 'kullanici';
    final roleLabel = isUser ? 'Kullanıcı' : (normalizedRole == 'assistant' || normalizedRole == 'asistan' ? 'Asistan' : 'Mesaj');
    return Container(
      margin: const EdgeInsets.only(bottom: 10),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: isUser
            ? scheme.primary.withValues(alpha: 0.08)
            : scheme.onSurface.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            roleLabel,
            style: TextStyle(
              color: isUser ? scheme.primary : scheme.onSurface,
              fontWeight: FontWeight.w700,
              fontSize: 12,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            message.content,
            style: TextStyle(
              color: scheme.onSurface,
              height: 1.45,
            ),
          ),
          if (message.createdAt != null) ...[
            const SizedBox(height: 6),
            Text(
              _formatDateTime(message.createdAt!),
              style: TextStyle(
                color: scheme.onSurface.withValues(alpha: 0.52),
                fontSize: 12,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _HistoryEntryCard extends StatelessWidget {
  const _HistoryEntryCard({required this.entry});

  final _HistoryEntryVm entry;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF141928) : Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(
                  horizontal: 10,
                  vertical: 6,
                ),
                decoration: BoxDecoration(
                  color: scheme.primary.withValues(alpha: 0.10),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  _entryTypeLabel(entry.type),
                  style: TextStyle(
                    color: scheme.primary,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
              const Spacer(),
              if (entry.recordedAt != null)
                Text(
                  _formatDateTime(entry.recordedAt!),
                  style: TextStyle(
                    color: scheme.onSurface.withValues(alpha: 0.58),
                    fontSize: 12,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            entry.summary,
            style: TextStyle(
              color: scheme.onSurface,
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

String _formatDateTime(DateTime value) {
  final local = value.toLocal();
  final day = local.day.toString().padLeft(2, '0');
  final month = local.month.toString().padLeft(2, '0');
  final year = local.year.toString();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$day.$month.$year $hour:$minute';
}

String _entryTypeLabel(String raw) {
  switch (raw) {
    case 'lab':
      return 'Tahlil';
    case 'visit':
      return 'Ziyaret';
    case 'medication':
      return 'İlaç';
    case 'appointment':
      return 'Randevu';
    case 'interaction':
      return 'Sohbet';
    case 'allergy':
      return 'Alerji';
    default:
      return raw.isEmpty ? 'Kayıt' : 'Kayıt';
  }
}

String _statusLabel(String raw) {
  switch (raw.toLowerCase()) {
    case 'confirmed':
      return 'Onaylandı';
    case 'cancelled':
    case 'canceled':
      return 'İptal edildi';
    case 'pending':
      return 'Beklemede';
    default:
      return raw.isEmpty ? 'Bilinmiyor' : raw;
  }
}
