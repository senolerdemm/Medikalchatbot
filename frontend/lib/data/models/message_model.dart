import '../../domain/entities/message.dart';

class ChatMessageModel {
  static ChatMessageEntity fromApi(Map<String, dynamic> json) {
    final sourceList = (json['sources'] as List<dynamic>? ?? [])
        .map(
          (item) => SourceDocument(
            title: item['title'] as String? ?? '',
            source: item['source'] as String? ?? '',
            excerpt: item['excerpt'] as String? ?? '',
            score: (item['score'] as num?)?.toDouble() ?? 0,
            url: item['url'] as String?,
          ),
        )
        .toList();

    return ChatMessageEntity(
      content: json['message'] as String? ?? '',
      isUser: false,
      handledBy: json['handled_by'] as String? ?? '',
      uiAction: json['ui_action'] as String? ?? 'none',
      conversationId: json['conversation_id'] as String? ?? '',
      payload: Map<String, dynamic>.from(json['payload'] as Map? ?? {}),
      sources: sourceList,
    );
  }
}
