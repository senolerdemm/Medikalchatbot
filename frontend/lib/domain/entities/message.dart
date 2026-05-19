class SourceDocument {
  final String title;
  final String source;
  final String excerpt;
  final double score;
  final String? url;

  const SourceDocument({
    required this.title,
    required this.source,
    required this.excerpt,
    required this.score,
    this.url,
  });
}

class ChatMessageEntity {
  final String content;
  final bool isUser;
  final String handledBy;
  final String uiAction;
  final String conversationId;
  final Map<String, dynamic> payload;
  final List<SourceDocument> sources;

  const ChatMessageEntity({
    required this.content,
    required this.isUser,
    this.handledBy = '',
    this.uiAction = 'none',
    this.conversationId = '',
    this.payload = const {},
    this.sources = const [],
  });
}

class DemoUserSession {
  final String token;
  final String patientId;
  final String email;
  final String fullName;

  const DemoUserSession({
    required this.token,
    required this.patientId,
    required this.email,
    required this.fullName,
  });
}
