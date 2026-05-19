class AppointmentSlotEntity {
  final String slotId;
  final String hospitalName;
  final String city;
  final String physicianName;
  final String specialty;
  final DateTime startAt;
  final bool isAvailable;

  const AppointmentSlotEntity({
    required this.slotId,
    required this.hospitalName,
    required this.city,
    required this.physicianName,
    required this.specialty,
    required this.startAt,
    required this.isAvailable,
  });
}

class AppointmentBookingEntity {
  final String bookingId;
  final String status;
  final AppointmentSlotEntity slot;

  const AppointmentBookingEntity({
    required this.bookingId,
    required this.status,
    required this.slot,
  });
}
