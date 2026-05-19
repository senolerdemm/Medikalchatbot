import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

class FastApiClient {
  FastApiClient({
    http.Client? httpClient,
    String? baseUrl,
  })  : _httpClient = httpClient ?? http.Client(),
        baseUrl = _normalizeBaseUrl(baseUrl ?? defaultBaseUrl);

  static const String _envBaseUrl = String.fromEnvironment('API_BASE_URL');

  static String get defaultBaseUrl {
    if (_envBaseUrl.isNotEmpty) {
      return _envBaseUrl;
    }
    if (kIsWeb) {
      return 'http://127.0.0.1:8000/api/v1';
    }
    if (defaultTargetPlatform == TargetPlatform.android) {
      return 'http://10.0.2.2:8000/api/v1';
    }
    return 'http://127.0.0.1:8000/api/v1';
  }

  final http.Client _httpClient;
  final String baseUrl;

  Future<Map<String, dynamic>> login({
    required String email,
    required String password,
  }) async {
    final response = await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/auth/login'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({'email': email, 'password': password}),
      ),
    );
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> register({
    required String fullName,
    required String email,
    required String password,
  }) async {
    final response = await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/auth/register'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'full_name': fullName,
          'email': email,
          'password': password,
        }),
      ),
    );
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> currentUser(String token) async {
    final response = await _request(
      () => _httpClient.get(
        Uri.parse('$baseUrl/auth/me'),
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return _decodeResponse(response);
  }

  Future<void> logout(String token) async {
    await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/auth/logout'),
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
  }

  Future<Map<String, dynamic>> sendMessage({
    required String token,
    required String message,
    String? conversationId,
  }) async {
    final response = await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/chat'),
        headers: {
          'Authorization': 'Bearer $token',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'message': message,
          'conversation_id': conversationId,
        }),
      ),
    );
    return _decodeResponse(response);
  }

  Future<List<dynamic>> listAppointments(String token) async {
    final response = await _request(
      () => _httpClient.get(
        Uri.parse('$baseUrl/appointments'),
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return _decodeListResponse(response);
  }

  Future<Map<String, dynamic>> bookAppointment(
    String token,
    String slotId,
  ) async {
    final response = await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/appointments/$slotId/book'),
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return _decodeResponse(response);
  }

  Future<Map<String, dynamic>> cancelAppointment(
    String token,
    String bookingId,
  ) async {
    final response = await _request(
      () => _httpClient.post(
        Uri.parse('$baseUrl/appointments/$bookingId/cancel'),
        headers: {'Authorization': 'Bearer $token'},
      ),
    );
    return _decodeResponse(response);
  }

  Future<http.Response> _request(Future<http.Response> Function() fn) async {
    try {
      return await fn();
    } catch (_) {
      throw Exception(
        'Backend bağlantısı kurulamadı. API adresi: $baseUrl. Backend servisinin açık olduğunu kontrol edin.',
      );
    }
  }

  Map<String, dynamic> _decodeResponse(http.Response response) {
    final rawBody = utf8.decode(response.bodyBytes);
    final decoded = _tryDecodeJson(rawBody);
    if (response.statusCode >= 400) {
      throw Exception(
        decoded is Map<String, dynamic>
            ? decoded['detail'] ?? 'API isteği başarısız oldu.'
            : (rawBody.isNotEmpty ? rawBody : 'API isteği başarısız oldu.'),
      );
    }
    if (decoded is! Map) {
      throw Exception('API beklenen JSON cevabını döndürmedi.');
    }
    return Map<String, dynamic>.from(decoded);
  }

  List<dynamic> _decodeListResponse(http.Response response) {
    final rawBody = utf8.decode(response.bodyBytes);
    final decoded = _tryDecodeJson(rawBody);
    if (response.statusCode >= 400) {
      throw Exception(
        decoded is Map<String, dynamic>
            ? decoded['detail'] ?? 'API isteği başarısız oldu.'
            : (rawBody.isNotEmpty ? rawBody : 'API isteği başarısız oldu.'),
      );
    }
    if (decoded is! List) {
      throw Exception('API beklenen liste cevabını döndürmedi.');
    }
    return List<dynamic>.from(decoded);
  }

  dynamic _tryDecodeJson(String rawBody) {
    try {
      return jsonDecode(rawBody);
    } catch (_) {
      return rawBody;
    }
  }

  static String _normalizeBaseUrl(String baseUrl) {
    if (baseUrl.endsWith('/')) {
      return baseUrl.substring(0, baseUrl.length - 1);
    }
    return baseUrl;
  }
}
