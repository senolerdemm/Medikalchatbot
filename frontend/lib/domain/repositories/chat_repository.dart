import '../entities/appointment_slot.dart';
import '../entities/message.dart';

abstract class ChatRepository {
  Future<DemoUserSession> login({
    required String email,
    required String password,
  });

  Future<DemoUserSession> register({
    required String fullName,
    required String email,
    required String password,
  });

  Future<DemoUserSession?> restoreSession();

  Future<void> logout();

  Future<ChatMessageEntity> sendMessage({
    required String message,
    String? conversationId,
  });

  Future<List<AppointmentBookingEntity>> listAppointments();

  Future<AppointmentBookingEntity> bookAppointment(String slotId);

  Future<AppointmentBookingEntity> cancelAppointment(String bookingId);
}
