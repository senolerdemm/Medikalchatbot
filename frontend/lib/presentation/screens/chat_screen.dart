import 'package:flutter/material.dart';
import 'package:medical_chatbot/domain/entities/message.dart';
import 'package:medical_chatbot/main.dart';
import 'package:medical_chatbot/presentation/blocs/chat_bloc.dart';
import 'package:medical_chatbot/presentation/screens/appointments_screen.dart';
import 'package:medical_chatbot/presentation/screens/history_screen.dart';
import 'package:medical_chatbot/presentation/screens/result_screen.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key, required this.bloc});

  final ChatBloc bloc;

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();
  String? _lastShownBookingId;

  @override
  void initState() {
    super.initState();
    widget.bloc.addListener(_handleBlocUpdate);
  }

  @override
  void dispose() {
    widget.bloc.removeListener(_handleBlocUpdate);
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  void _handleBlocUpdate() {
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (_scrollController.hasClients) {
        _scrollController.animateTo(
          _scrollController.position.maxScrollExtent,
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOut,
        );
      }
    });
    if (!mounted || widget.bloc.messages.isEmpty) return;
    final last = widget.bloc.messages.last;
    if (!last.isUser &&
        last.uiAction == 'show_appointment_options' &&
        (last.payload['booked'] == true)) {
      final booking = Map<String, dynamic>.from(
        last.payload['booking'] as Map? ?? {},
      );
      final bookingId = booking['booking_id']?.toString();
      if (bookingId == null || bookingId.isEmpty || bookingId == _lastShownBookingId) {
        return;
      }
      _lastShownBookingId = bookingId;
      final slot = Map<String, dynamic>.from(booking['slot'] as Map? ?? {});
      Navigator.push(
        context,
        MaterialPageRoute(
          builder: (_) => ResultScreen(
            bookingPayload: {
              'booking_id': bookingId,
              'status': booking['status'] ?? 'confirmed',
              'slot': slot,
            },
          ),
        ),
      );
    }
  }

  Future<void> _sendMessage() async {
    final text = _controller.text.trim();
    if (text.isEmpty) return;
    _controller.clear();
    await widget.bloc.sendMessage(text);
  }

  void _openHistoryScreen({
    required String summaryMessage,
    required Map<String, dynamic> payload,
  }) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => HistoryScreen(
          summaryMessage: summaryMessage,
          payload: payload,
        ),
      ),
    );
  }

  Widget _buildMessageBubble(ChatMessageEntity message) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;
    if (message.isUser) {
      return Align(
        alignment: Alignment.centerRight,
        child: Container(
          margin: const EdgeInsets.only(left: 64, bottom: 12),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          decoration: BoxDecoration(
            color: scheme.primary,
            borderRadius: BorderRadius.circular(18),
          ),
          child: Text(
            message.content,
            style: TextStyle(
              color: isDark ? const Color(0xFF0A0E1A) : Colors.white,
            ),
          ),
        ),
      );
    }

    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: isDark ? const Color(0xFF141928) : Colors.white,
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (message.handledBy.isNotEmpty)
            Container(
              margin: const EdgeInsets.only(bottom: 10),
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
              decoration: BoxDecoration(
                color: scheme.primary.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(20),
              ),
              child: Text(
                message.handledBy,
                style: TextStyle(
                  color: scheme.primary,
                  fontWeight: FontWeight.w600,
                  fontSize: 12,
                ),
              ),
            ),
          Text(
            message.content,
            style: TextStyle(color: scheme.onSurface, height: 1.45),
          ),
          if (message.uiAction == 'show_appointment_options') ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => AppointmentsScreen(bloc: widget.bloc),
                ),
              ),
              icon: const Icon(Icons.calendar_today_outlined),
              label: const Text('Randevuları Gör'),
            ),
          ],
          if (message.uiAction == 'show_history_summary') ...[
            const SizedBox(height: 10),
            OutlinedButton.icon(
              onPressed: () => _openHistoryScreen(
                summaryMessage: message.content,
                payload: message.payload,
              ),
              icon: const Icon(Icons.history_edu_outlined),
              label: const Text('Geçmiş Özetini Gör'),
            ),
          ],
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return AnimatedBuilder(
      animation: widget.bloc,
      builder: (context, _) => Scaffold(
        appBar: AppBar(
          title: const Text(appDisplayName),
          actions: [
            IconButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => AppointmentsScreen(bloc: widget.bloc),
                ),
              ),
              icon: const Icon(Icons.calendar_month_outlined),
            ),
            IconButton(
              onPressed: widget.bloc.latestHistoryPayload == null
                  ? null
                  : () => _openHistoryScreen(
                      summaryMessage:
                          widget.bloc.latestHistoryMessage ?? 'Geçmiş özeti',
                      payload: widget.bloc.latestHistoryPayload!,
                    ),
              icon: const Icon(Icons.history_outlined),
            ),
            IconButton(
              onPressed: () async {
                final navigator = Navigator.of(context);
                await widget.bloc.logout();
                if (!mounted) return;
                navigator.pop();
              },
              icon: const Icon(Icons.logout),
            ),
            Padding(
              padding: const EdgeInsets.only(right: 8),
              child: GestureDetector(
                onTap: () => themeNotifier.value =
                    isDark ? ThemeMode.light : ThemeMode.dark,
                child: Icon(
                  isDark ? Icons.light_mode_outlined : Icons.dark_mode_outlined,
                  color: scheme.primary,
                ),
              ),
            ),
          ],
        ),
        body: Column(
          children: [
            Expanded(
              child: ListView.builder(
                controller: _scrollController,
                padding: const EdgeInsets.all(16),
                itemCount: widget.bloc.messages.length,
                itemBuilder: (context, index) =>
                    _buildMessageBubble(widget.bloc.messages[index]),
              ),
            ),
            if (widget.bloc.isBusy)
              const Padding(
                padding: EdgeInsets.only(bottom: 8),
                child: CircularProgressIndicator(strokeWidth: 2),
              ),
            if (widget.bloc.errorMessage != null)
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                child: Text(
                  widget.bloc.errorMessage!,
                  style: const TextStyle(color: Colors.redAccent),
                ),
              ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _controller,
                      decoration: const InputDecoration(
                        hintText: 'Sağlık sorusu veya randevu talebi yazın...',
                        border: OutlineInputBorder(),
                      ),
                      onSubmitted: (_) => _sendMessage(),
                    ),
                  ),
                  const SizedBox(width: 12),
                  FilledButton(
                    onPressed: widget.bloc.isBusy ? null : _sendMessage,
                    child: const Icon(Icons.send),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
