import 'package:flutter/material.dart';
import 'package:medical_chatbot/domain/entities/appointment_slot.dart';
import 'package:medical_chatbot/presentation/blocs/chat_bloc.dart';


class AppointmentsScreen extends StatefulWidget {
  const AppointmentsScreen({super.key, required this.bloc});

  final ChatBloc bloc;

  @override
  State<AppointmentsScreen> createState() => _AppointmentsScreenState();
}

class _AppointmentsScreenState extends State<AppointmentsScreen> {
  @override
  void initState() {
    super.initState();
    widget.bloc.refreshAppointments();
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: widget.bloc,
      builder: (context, _) {
        final bookings = widget.bloc.appointments;
        final activeBookings =
            bookings.where((booking) => booking.status != 'cancelled').toList();
        final cancelledBookings =
            bookings.where((booking) => booking.status == 'cancelled').toList();
        final suggestedSlots = widget.bloc.suggestedSlots;

        return Scaffold(
          appBar: AppBar(
            title: const Text('Randevu Merkezi'),
            actions: [
              IconButton(
                onPressed: widget.bloc.isRefreshingAppointments
                    ? null
                    : () => widget.bloc.refreshAppointments(),
                icon: const Icon(Icons.refresh),
              ),
            ],
          ),
          body: widget.bloc.isRefreshingAppointments &&
                  bookings.isEmpty &&
                  suggestedSlots.isEmpty
              ? const Center(child: CircularProgressIndicator())
              : ListView(
                  padding: const EdgeInsets.all(16),
                  children: [
                    _HeaderCard(
                      title: 'Mevcut Randevular',
                      subtitle:
                          '${activeBookings.length} aktif, ${cancelledBookings.length} geçmiş/iptal kaydı',
                    ),
                    const SizedBox(height: 12),
                    if (widget.bloc.appointmentsErrorMessage != null)
                      _InfoBanner(
                        message: widget.bloc.appointmentsErrorMessage!,
                        color: Colors.redAccent,
                      ),
                    if (widget.bloc.errorMessage != null)
                      _InfoBanner(
                        message: widget.bloc.errorMessage!,
                        color: Colors.redAccent,
                      ),
                    if (activeBookings.isEmpty)
                      _EmptySection(
                        icon: Icons.calendar_today_outlined,
                        title: 'Aktif randevu yok',
                        description:
                            'Sohbette şehir, bölüm ve saat belirterek yeni randevu seçenekleri getirebilirsiniz.',
                      )
                    else
                      ...activeBookings.map(
                        (booking) => _BookingCard(
                          booking: booking,
                          onCancel: widget.bloc.isBusy
                              ? null
                              : () => widget.bloc.cancelBooking(booking.bookingId),
                        ),
                      ),
                    const SizedBox(height: 24),
                    _HeaderCard(
                      title: 'Önerilen Gelecek Randevular',
                      subtitle: suggestedSlots.isEmpty
                          ? 'Son aramada seçenek yok'
                          : '${suggestedSlots.length} seçenek hazır',
                    ),
                    const SizedBox(height: 12),
                    if (suggestedSlots.isEmpty)
                      _EmptySection(
                        icon: Icons.search_outlined,
                        title: 'Henüz öneri yok',
                        description:
                            'Örnek: "Ankara kalp rahatsızlığım var, Ankara’da uygun kardiyologları göster" ya da "yarın saat 12 için KBB ara".',
                      )
                    else
                      ...suggestedSlots.asMap().entries.map(
                        (entry) => _SuggestedSlotCard(
                          index: entry.key + 1,
                          slot: entry.value,
                          onBook: widget.bloc.isBusy
                              ? null
                              : () => widget.bloc.bookSuggestedSlot(entry.value),
                        ),
                      ),
                    if (cancelledBookings.isNotEmpty) ...[
                      const SizedBox(height: 24),
                      _HeaderCard(
                        title: 'Geçmiş / İptal Kayıtları',
                        subtitle: '${cancelledBookings.length} kayıt',
                      ),
                      const SizedBox(height: 12),
                      ...cancelledBookings.map(
                        (booking) => _BookingCard(
                          booking: booking,
                          onCancel: null,
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    Container(
                      padding: const EdgeInsets.all(16),
                      decoration: BoxDecoration(
                        color: isDark ? const Color(0xFF141928) : Colors.white,
                        borderRadius: BorderRadius.circular(18),
                      ),
                      child: Text(
                        'İpuçları: "Ankara kardiyoloji seçeneklerini göster", "yarın saat 10 gibi KBB bul", "ilkini al", "randevularımı göster", "ilk randevumu iptal et".',
                        style: TextStyle(
                          color: scheme.onSurface.withValues(alpha: 0.72),
                          height: 1.45,
                        ),
                      ),
                    ),
                  ],
                ),
        );
      },
    );
  }
}

class _HeaderCard extends StatelessWidget {
  const _HeaderCard({
    required this.title,
    required this.subtitle,
  });

  final String title;
  final String subtitle;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF141928) : Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: TextStyle(
              color: scheme.onSurface,
              fontWeight: FontWeight.bold,
              fontSize: 17,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            subtitle,
            style: TextStyle(
              color: scheme.onSurface.withValues(alpha: 0.68),
            ),
          ),
        ],
      ),
    );
  }
}

class _BookingCard extends StatelessWidget {
  const _BookingCard({
    required this.booking,
    this.onCancel,
  });

  final AppointmentBookingEntity booking;
  final VoidCallback? onCancel;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    final statusColor = _statusColor(booking.status);
    final cancelled = booking.status == 'cancelled';

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
              Expanded(
                child: Text(
                  '${booking.slot.specialty} • ${booking.slot.city}',
                  style: TextStyle(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
                ),
              ),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: statusColor.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  _statusLabel(booking.status),
                  style: TextStyle(
                    color: statusColor,
                    fontWeight: FontWeight.w700,
                    fontSize: 12,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          _InfoLine(
            icon: Icons.schedule_outlined,
            text: _formatDateTime(booking.slot.startAt),
          ),
          _InfoLine(
            icon: Icons.person_outline,
            text: booking.slot.physicianName,
          ),
          _InfoLine(
            icon: Icons.location_on_outlined,
            text: '${booking.slot.hospitalName} / ${booking.slot.city}',
          ),
          const SizedBox(height: 10),
          Text(
            'Rezervasyon Kodu: ${booking.bookingId}',
            style: TextStyle(
              color: scheme.onSurface.withValues(alpha: 0.56),
              fontSize: 12,
            ),
          ),
          if (!cancelled && onCancel != null) ...[
            const SizedBox(height: 12),
            Align(
              alignment: Alignment.centerRight,
              child: OutlinedButton.icon(
                onPressed: onCancel,
                icon: const Icon(Icons.close),
                label: const Text('İptal Et'),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _SuggestedSlotCard extends StatelessWidget {
  const _SuggestedSlotCard({
    required this.index,
    required this.slot,
    this.onBook,
  });

  final int index;
  final AppointmentSlotEntity slot;
  final VoidCallback? onBook;

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
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: scheme.primary.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                alignment: Alignment.center,
                child: Text(
                  '$index',
                  style: TextStyle(
                    color: scheme.primary,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  '${slot.specialty} • ${slot.city}',
                  style: TextStyle(
                    color: scheme.onSurface,
                    fontWeight: FontWeight.w700,
                    fontSize: 16,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          _InfoLine(
            icon: Icons.schedule_outlined,
            text: _formatDateTime(slot.startAt),
          ),
          _InfoLine(
            icon: Icons.person_outline,
            text: slot.physicianName,
          ),
          _InfoLine(
            icon: Icons.local_hospital_outlined,
            text: slot.hospitalName,
          ),
          const SizedBox(height: 12),
          Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              onPressed: onBook,
              icon: const Icon(Icons.event_available),
              label: const Text('Bu Randevuyu Al'),
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoLine extends StatelessWidget {
  const _InfoLine({
    required this.icon,
    required this.text,
  });

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        children: [
          Icon(icon, size: 18, color: scheme.primary),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              text,
              style: TextStyle(color: scheme.onSurface.withValues(alpha: 0.78)),
            ),
          ),
        ],
      ),
    );
  }
}

class _EmptySection extends StatelessWidget {
  const _EmptySection({
    required this.icon,
    required this.title,
    required this.description,
  });

  final IconData icon;
  final String title;
  final String description;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: scheme.primary.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        children: [
          Icon(icon, color: scheme.primary, size: 34),
          const SizedBox(height: 10),
          Text(
            title,
            style: TextStyle(
              color: scheme.onSurface,
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 6),
          Text(
            description,
            textAlign: TextAlign.center,
            style: TextStyle(
              color: scheme.onSurface.withValues(alpha: 0.68),
              height: 1.45,
            ),
          ),
        ],
      ),
    );
  }
}

class _InfoBanner extends StatelessWidget {
  const _InfoBanner({
    required this.message,
    required this.color,
  });

  final String message;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        message,
        style: TextStyle(color: color),
      ),
    );
  }
}

String _formatDateTime(DateTime dateTime) {
  final local = dateTime.toLocal();
  final day = local.day.toString().padLeft(2, '0');
  final month = local.month.toString().padLeft(2, '0');
  final year = local.year.toString();
  final hour = local.hour.toString().padLeft(2, '0');
  final minute = local.minute.toString().padLeft(2, '0');
  return '$day.$month.$year $hour:$minute';
}

String _statusLabel(String status) {
  switch (status) {
    case 'confirmed':
      return 'Onaylandı';
    case 'cancelled':
      return 'İptal';
    case 'pending':
      return 'Beklemede';
    default:
      return status;
  }
}

Color _statusColor(String status) {
  switch (status) {
    case 'confirmed':
      return const Color(0xFF0E9F6E);
    case 'cancelled':
      return const Color(0xFFE02424);
    case 'pending':
      return const Color(0xFFF59E0B);
    default:
      return const Color(0xFF6B7280);
  }
}
