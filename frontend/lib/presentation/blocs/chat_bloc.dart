import 'package:flutter/foundation.dart';

import '../../domain/entities/appointment_slot.dart';
import '../../domain/entities/message.dart';
import '../../domain/repositories/chat_repository.dart';

class ChatBloc extends ChangeNotifier {
  ChatBloc({required ChatRepository repository}) : _repository = repository;

  final ChatRepository _repository;

  DemoUserSession? currentSession;
  bool isBusy = false;
  bool isRefreshingAppointments = false;
  String? errorMessage;
  String? appointmentsErrorMessage;
  String? conversationId;
  Map<String, dynamic>? latestHistoryPayload;
  String? latestHistoryMessage;
  List<AppointmentBookingEntity> appointments = [];
  List<AppointmentSlotEntity> suggestedSlots = [];
  final List<ChatMessageEntity> messages = [
    const ChatMessageEntity(
      content: 'Merhaba, ben Akıllı Tıbbi Asistan. Size sağlık bilgisi, kişisel geçmiş özeti ve randevu işlemlerinde yardımcı olabilirim.',
      isUser: false,
    ),
  ];

  Future<bool> restoreSession() async {
    currentSession = await _repository.restoreSession();
    if (currentSession != null) {
      await refreshAppointments(silent: true);
      notifyListeners();
      return true;
    }
    return false;
  }

  Future<bool> login({
    required String email,
    required String password,
  }) async {
    try {
      isBusy = true;
      errorMessage = null;
      notifyListeners();
      currentSession = await _repository.login(email: email, password: password);
      await refreshAppointments(silent: true);
      return true;
    } catch (error) {
      errorMessage = error.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<bool> register({
    required String fullName,
    required String email,
    required String password,
  }) async {
    try {
      isBusy = true;
      errorMessage = null;
      notifyListeners();
      currentSession = await _repository.register(
        fullName: fullName,
        email: email,
        password: password,
      );
      await refreshAppointments(silent: true);
      return true;
    } catch (error) {
      errorMessage = error.toString().replaceFirst('Exception: ', '');
      return false;
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> logout() async {
    await _repository.logout();
    currentSession = null;
    conversationId = null;
    appointments = [];
    suggestedSlots = [];
    latestHistoryPayload = null;
    latestHistoryMessage = null;
    messages
      ..clear()
      ..add(const ChatMessageEntity(
        content: 'Merhaba, ben Akıllı Tıbbi Asistan. Size sağlık bilgisi, kişisel geçmiş özeti ve randevu işlemlerinde yardımcı olabilirim.',
        isUser: false,
      ));
    notifyListeners();
  }

  Future<void> sendMessage(String text) async {
    if (text.trim().isEmpty) return;
    messages.add(ChatMessageEntity(content: text.trim(), isUser: true));
    isBusy = true;
    errorMessage = null;
    notifyListeners();
    try {
      final response = await _repository.sendMessage(
        message: text.trim(),
        conversationId: conversationId,
      );
      conversationId = response.conversationId.isNotEmpty ? response.conversationId : conversationId;
      _captureSuggestedSlots(response);
      _captureHistoryPayload(response);
      messages.add(response);
      if (response.uiAction == 'show_appointment_options') {
        await refreshAppointments(silent: true);
      }
    } catch (error) {
      errorMessage = error.toString().replaceFirst('Exception: ', '');
      messages.add(
        ChatMessageEntity(
          content: errorMessage ?? 'Bir hata olustu.',
          isUser: false,
        ),
      );
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> refreshAppointments({bool silent = false}) async {
    isRefreshingAppointments = true;
    if (!silent) {
      appointmentsErrorMessage = null;
    }
    notifyListeners();
    try {
      appointments = await _repository.listAppointments();
      appointmentsErrorMessage = null;
    } catch (error) {
      appointments = [];
      appointmentsErrorMessage =
          error.toString().replaceFirst('Exception: ', '');
      if (!silent) {
        errorMessage = error.toString().replaceFirst('Exception: ', '');
      }
    } finally {
      isRefreshingAppointments = false;
      notifyListeners();
    }
  }

  Future<void> bookSuggestedSlot(AppointmentSlotEntity slot) async {
    try {
      isBusy = true;
      errorMessage = null;
      notifyListeners();
      final booking = await _repository.bookAppointment(slot.slotId);
      messages.add(
        ChatMessageEntity(
          content:
              'Randevu oluşturuldu: ${booking.slot.hospitalName} / ${booking.slot.specialty} / ${booking.slot.physicianName} / ${_formatDateTime(booking.slot.startAt)}',
          isUser: false,
          handledBy: 'Randevu Ajanı',
          uiAction: 'show_appointment_options',
          payload: {
            'action': 'book',
            'booked': true,
            'booking': {
              'booking_id': booking.bookingId,
              'status': booking.status,
              'slot': {
                'slot_id': booking.slot.slotId,
                'hospital_name': booking.slot.hospitalName,
                'city': booking.slot.city,
                'physician_name': booking.slot.physicianName,
                'specialty': booking.slot.specialty,
                'start_at': booking.slot.startAt.toIso8601String(),
                'is_available': booking.slot.isAvailable,
              },
            },
          },
        ),
      );
      suggestedSlots = suggestedSlots
          .where((candidate) => candidate.slotId != slot.slotId)
          .toList();
      await refreshAppointments(silent: true);
    } catch (error) {
      errorMessage = error.toString().replaceFirst('Exception: ', '');
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  Future<void> cancelBooking(String bookingId) async {
    try {
      isBusy = true;
      errorMessage = null;
      notifyListeners();
      final cancelled = await _repository.cancelAppointment(bookingId);
      messages.add(
        ChatMessageEntity(
          content:
              '${cancelled.slot.hospitalName} / ${cancelled.slot.specialty} randevunuz iptal edildi.',
          isUser: false,
          handledBy: 'Randevu Ajanı',
          uiAction: 'show_appointment_options',
          payload: {
            'action': 'cancel',
            'cancelled': true,
            'booking': {
              'booking_id': cancelled.bookingId,
              'status': cancelled.status,
              'slot': {
                'slot_id': cancelled.slot.slotId,
                'hospital_name': cancelled.slot.hospitalName,
                'city': cancelled.slot.city,
                'physician_name': cancelled.slot.physicianName,
                'specialty': cancelled.slot.specialty,
                'start_at': cancelled.slot.startAt.toIso8601String(),
                'is_available': cancelled.slot.isAvailable,
              },
            },
          },
        ),
      );
      await refreshAppointments(silent: true);
    } catch (error) {
      errorMessage = error.toString().replaceFirst('Exception: ', '');
    } finally {
      isBusy = false;
      notifyListeners();
    }
  }

  void _captureSuggestedSlots(ChatMessageEntity response) {
    final payloadSlots = response.payload['slot_options'];
    if (payloadSlots is! List) {
      return;
    }
    suggestedSlots = payloadSlots
        .whereType<Map>()
        .map((item) => Map<String, dynamic>.from(item))
        .map(
          (slot) => AppointmentSlotEntity(
            slotId: slot['slot_id'] as String? ?? '',
            hospitalName: slot['hospital_name'] as String? ?? '',
            city: slot['city'] as String? ?? '',
            physicianName: slot['physician_name'] as String? ?? '',
            specialty: slot['specialty'] as String? ?? '',
            startAt: DateTime.tryParse(slot['start_at'] as String? ?? '') ??
                DateTime.now(),
            isAvailable: true,
          ),
        )
        .where((slot) => slot.slotId.isNotEmpty)
        .toList();
  }

  void _captureHistoryPayload(ChatMessageEntity response) {
    if (response.uiAction != 'show_history_summary') {
      return;
    }
    latestHistoryPayload = Map<String, dynamic>.from(response.payload);
    latestHistoryMessage = response.content;
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
}
