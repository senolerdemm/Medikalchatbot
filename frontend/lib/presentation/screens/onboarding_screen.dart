import 'package:flutter/material.dart';
import 'package:medical_chatbot/data/datasources/remote/fastapi_client.dart';
import 'package:medical_chatbot/data/repositories/chat_repository_impl.dart';
import 'package:medical_chatbot/main.dart';
import 'package:medical_chatbot/presentation/blocs/chat_bloc.dart';
import 'package:medical_chatbot/presentation/screens/chat_screen.dart';

class OnboardingScreen extends StatefulWidget {
  const OnboardingScreen({super.key});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _fullNameController = TextEditingController();
  final _emailController = TextEditingController(text: 'senol@example.com');
  final _passwordController = TextEditingController(text: '1234');
  late final ChatBloc _chatBloc;
  bool _isRegisterMode = false;

  final _demoUsers = const [
    ('senol@example.com', 'Alerji ve KBB geçmişi'),
    ('ayse@example.com', 'Diyabet ve dahiliye geçmişi'),
    ('mehmet@example.com', 'Kardiyoloji ve randevu geçmişi'),
  ];

  @override
  void initState() {
    super.initState();
    _chatBloc = ChatBloc(
      repository: ChatRepositoryImpl(remoteClient: FastApiClient()),
    );
    _chatBloc.restoreSession().then((loggedIn) {
      if (loggedIn && mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ChatScreen(bloc: _chatBloc)),
        );
      }
    });
  }

  @override
  void dispose() {
    _fullNameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final success = _isRegisterMode
        ? await _chatBloc.register(
            fullName: _fullNameController.text.trim(),
            email: _emailController.text.trim(),
            password: _passwordController.text.trim(),
          )
        : await _chatBloc.login(
            email: _emailController.text.trim(),
            password: _passwordController.text.trim(),
          );
    if (!mounted) return;
    if (success) {
      Navigator.pushReplacement(
        context,
        MaterialPageRoute(builder: (_) => ChatScreen(bloc: _chatBloc)),
      );
      return;
    }
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(_chatBloc.errorMessage ?? 'Giriş başarısız.')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final isDark = Theme.of(context).brightness == Brightness.dark;

    return Scaffold(
      appBar: AppBar(
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 14),
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
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 460),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                Container(
                  width: 84,
                  height: 84,
                  margin: const EdgeInsets.only(bottom: 20),
                  decoration: BoxDecoration(
                    color: scheme.primary.withValues(alpha: 0.12),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    Icons.health_and_safety_outlined,
                    color: scheme.primary,
                    size: 44,
                  ),
                ),
                Text(
                  appDisplayName,
                  style: TextStyle(
                    color: scheme.onSurface,
                    fontSize: 30,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 10),
                Text(
                  appFormalName,
                  style: TextStyle(
                    color: scheme.primary,
                    fontSize: 15,
                    fontWeight: FontWeight.w600,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'E-posta ve şifre ile giriş yapın. İsterseniz hızlıca yeni hesap da oluşturabilirsiniz.',
                  style: TextStyle(
                    color: scheme.onSurface.withValues(alpha: 0.6),
                    fontSize: 15,
                    height: 1.5,
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  'API adresi: ${FastApiClient.defaultBaseUrl}',
                  style: TextStyle(
                    color: scheme.onSurface.withValues(alpha: 0.45),
                    fontSize: 12,
                  ),
                ),
                const SizedBox(height: 28),
                ..._demoUsers.map(
                  (user) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(Icons.person_outline, color: scheme.primary),
                    title: Text(user.$1),
                    subtitle: Text(user.$2),
                    onTap: () {
                      _emailController.text = user.$1;
                      _passwordController.text = '1234';
                      setState(() {});
                    },
                  ),
                ),
                const SizedBox(height: 16),
                if (_isRegisterMode) ...[
                  TextField(
                    controller: _fullNameController,
                    decoration: const InputDecoration(
                      labelText: 'Ad Soyad',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 12),
                ],
                TextField(
                  controller: _emailController,
                  decoration: const InputDecoration(
                    labelText: 'E-posta',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: _passwordController,
                  obscureText: true,
                  decoration: const InputDecoration(
                    labelText: 'Şifre',
                    border: OutlineInputBorder(),
                  ),
                ),
                const SizedBox(height: 20),
                AnimatedBuilder(
                  animation: _chatBloc,
                  builder: (context, _) => ElevatedButton(
                    onPressed: _chatBloc.isBusy ? null : _submit,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: scheme.primary,
                      foregroundColor:
                          isDark ? const Color(0xFF0A0E1A) : Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                    ),
                    child: Text(
                      _chatBloc.isBusy
                          ? 'İşlem yapılıyor...'
                          : (_isRegisterMode ? 'Kayıt Ol' : 'Giriş Yap'),
                    ),
                  ),
                ),
                const SizedBox(height: 10),
                TextButton(
                  onPressed: () => setState(() => _isRegisterMode = !_isRegisterMode),
                  child: Text(
                    _isRegisterMode
                        ? 'Zaten hesabım var'
                        : 'Yeni hesap oluştur',
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
