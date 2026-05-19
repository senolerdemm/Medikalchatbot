import 'package:shared_preferences/shared_preferences.dart';

import '../../domain/entities/appointment_slot.dart';
import '../../domain/entities/message.dart';
import '../../domain/repositories/chat_repository.dart';
import '../datasources/remote/fastapi_client.dart';
import '../models/message_model.dart';

class ChatRepositoryImpl implements ChatRepository {
  ChatRepositoryImpl({
    required FastApiClient remoteClient,
  }) : _remoteClient = remoteClient;

  static const _tokenKey = 'session_token';
  static const _patientIdKey = 'session_patient_id';
  static const _emailKey = 'session_email';
  static const _fullNameKey = 'session_full_name';

  final FastApiClient _remoteClient;

  @override
  Future<DemoUserSession> login({
    required String email,
    required String password,
  }) async {
    final response = await _remoteClient.login(
      email: email,
      password: password,
    );
    final user = Map<String, dynamic>.from(response['user'] as Map);
    final session = DemoUserSession(
      token: response['token'] as String,
      patientId: user['patient_id'] as String,
      email: user['email'] as String,
      fullName: user['full_name'] as String,
    );
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, session.token);
    await prefs.setString(_patientIdKey, session.patientId);
    await prefs.setString(_emailKey, session.email);
    await prefs.setString(_fullNameKey, session.fullName);
    return session;
  }

  @override
  Future<DemoUserSession> register({
    required String fullName,
    required String email,
    required String password,
  }) async {
    final response = await _remoteClient.register(
      fullName: fullName,
      email: email,
      password: password,
    );
    final user = Map<String, dynamic>.from(response['user'] as Map);
    final session = DemoUserSession(
      token: response['token'] as String,
      patientId: user['patient_id'] as String,
      email: user['email'] as String,
      fullName: user['full_name'] as String,
    );
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_tokenKey, session.token);
    await prefs.setString(_patientIdKey, session.patientId);
    await prefs.setString(_emailKey, session.email);
    await prefs.setString(_fullNameKey, session.fullName);
    return session;
  }

  @override
  Future<DemoUserSession?> restoreSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    final patientId = prefs.getString(_patientIdKey);
    final email = prefs.getString(_emailKey);
    final fullName = prefs.getString(_fullNameKey);
    if (token == null || patientId == null || email == null || fullName == null) {
      return null;
    }
    try {
      final me = await _remoteClient.currentUser(token);
      return DemoUserSession(
        token: token,
        patientId: me['patient_id'] as String? ?? patientId,
        email: me['email'] as String? ?? email,
        fullName: me['full_name'] as String? ?? fullName,
      );
    } catch (_) {
      await logout();
      return null;
    }
  }

  @override
  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token != null) {
      try {
        await _remoteClient.logout(token);
      } catch (_) {
        // Local session should still be cleared even if backend logout fails.
      }
    }
    await prefs.remove(_tokenKey);
    await prefs.remove(_patientIdKey);
    await prefs.remove(_emailKey);
    await prefs.remove(_fullNameKey);
  }

  @override
  Future<ChatMessageEntity> sendMessage({
    required String message,
    String? conversationId,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null) {
      throw Exception('Oturum bulunamadı.');
    }
    final response = await _remoteClient.sendMessage(
      token: token,
      message: message,
      conversationId: conversationId,
    );
    return ChatMessageModel.fromApi(response);
  }

  @override
  Future<List<AppointmentBookingEntity>> listAppointments() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null) {
      return [];
    }
    final response = await _remoteClient.listAppointments(token);
    return response.map((item) {
      final row = Map<String, dynamic>.from(item as Map);
      final slot = Map<String, dynamic>.from(row['slot'] as Map);
      return AppointmentBookingEntity(
        bookingId: row['booking_id'] as String,
        status: row['status'] as String,
        slot: AppointmentSlotEntity(
          slotId: slot['slot_id'] as String,
          hospitalName: slot['hospital_name'] as String,
          city: slot['city'] as String,
          physicianName: slot['physician_name'] as String,
          specialty: slot['specialty'] as String,
          startAt: DateTime.parse(slot['start_at'] as String),
          isAvailable: slot['is_available'] as bool? ?? true,
        ),
      );
    }).toList();
  }

  @override
  Future<AppointmentBookingEntity> bookAppointment(String slotId) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null) {
      throw Exception('Oturum bulunamadı.');
    }
    final response = await _remoteClient.bookAppointment(token, slotId);
    return _mapBooking(response);
  }

  @override
  Future<AppointmentBookingEntity> cancelAppointment(String bookingId) async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString(_tokenKey);
    if (token == null) {
      throw Exception('Oturum bulunamadı.');
    }
    final response = await _remoteClient.cancelAppointment(token, bookingId);
    return _mapBooking(response);
  }

  AppointmentBookingEntity _mapBooking(Map<String, dynamic> raw) {
    final row = Map<String, dynamic>.from(raw);
    final slot = Map<String, dynamic>.from(row['slot'] as Map);
    return AppointmentBookingEntity(
      bookingId: row['booking_id'] as String,
      status: row['status'] as String,
      slot: AppointmentSlotEntity(
        slotId: slot['slot_id'] as String,
        hospitalName: slot['hospital_name'] as String,
        city: slot['city'] as String,
        physicianName: slot['physician_name'] as String,
        specialty: slot['specialty'] as String,
        startAt: DateTime.parse(slot['start_at'] as String),
        isAvailable: slot['is_available'] as bool? ?? true,
      ),
    );
  }
}
