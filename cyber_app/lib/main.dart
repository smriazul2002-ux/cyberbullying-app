import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

import 'firebase_options.dart';
import 'complete_home.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Cyberbullying Shield',
      theme: ThemeData(primarySwatch: Colors.deepPurple, useMaterial3: true),
      home: const AuthGate(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class AuthGate extends StatelessWidget {
  const AuthGate({super.key});

  @override
  Widget build(BuildContext context) {
    return StreamBuilder<User?>(
      stream: FirebaseAuth.instance.authStateChanges(),
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator()),
          );
        }
        if (snapshot.hasData) {
          return const CompleteHomeScreen();
        }
        return const LoginScreen();
      },
    );
  }
}

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  final TextEditingController emailController = TextEditingController();
  final TextEditingController passwordController = TextEditingController();
  bool isLoading = false;
  String errorMessage = "";

  Future<void> login() async {
    setState(() {
      isLoading = true;
      errorMessage = "";
    });
    try {
      await FirebaseAuth.instance.signInWithEmailAndPassword(
        email: emailController.text.trim(),
        password: passwordController.text,
      );
    } on FirebaseAuthException catch (e) {
      setState(() => errorMessage = e.message ?? "Login failed");
    } finally {
      setState(() => isLoading = false);
    }
  }

  Future<void> register() async {
    setState(() {
      isLoading = true;
      errorMessage = "";
    });
    try {
      await FirebaseAuth.instance.createUserWithEmailAndPassword(
        email: emailController.text.trim(),
        password: passwordController.text,
      );
    } on FirebaseAuthException catch (e) {
      setState(() => errorMessage = e.message ?? "Registration failed");
    } finally {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.shield, size: 64, color: Colors.deepPurple),
              const SizedBox(height: 12),
              const Text(
                "Cyberbullying Shield",
                style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 32),
              TextField(
                controller: emailController,
                keyboardType: TextInputType.emailAddress,
                decoration: InputDecoration(
                  labelText: "Email",
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 16),
              TextField(
                controller: passwordController,
                obscureText: true,
                decoration: InputDecoration(
                  labelText: "Password",
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(12),
                  ),
                ),
              ),
              const SizedBox(height: 24),
              if (errorMessage.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Text(
                    errorMessage,
                    style: const TextStyle(color: Colors.red),
                    textAlign: TextAlign.center,
                  ),
                ),
              Row(
                children: [
                  Expanded(
                    child: ElevatedButton(
                      onPressed: isLoading ? null : login,
                      child: isLoading
                          ? const SizedBox(
                              height: 18,
                              width: 18,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text("Login"),
                    ),
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: OutlinedButton(
                      onPressed: isLoading ? null : register,
                      child: const Text("Register"),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class MainScreen extends StatefulWidget {
  const MainScreen({super.key});

  @override
  State<MainScreen> createState() => _MainScreenState();
}

class _MainScreenState extends State<MainScreen> {
  int currentIndex = 0;

  final List<Widget> tabs = const [
    DetectorTab(),
    ProtectorTab(),
    InfoTab(),
  ];

  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser;

    return Scaffold(
      appBar: AppBar(
        title: const Text("Cyberbullying Shield"),
        centerTitle: true,
        elevation: 0,
        actions: [
          IconButton(
            icon: const Icon(Icons.logout),
            tooltip: "Logout",
            onPressed: () async {
              await FirebaseAuth.instance.signOut();
            },
          ),
        ],
      ),
      body: Column(
        children: [
          Container(
            width: double.infinity,
            padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
            color: Colors.deepPurple.withValues(alpha: 0.06),
            child: Text(
              user?.email ?? "",
              style: const TextStyle(fontSize: 12, color: Colors.grey),
            ),
          ),
          Expanded(child: tabs[currentIndex]),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: currentIndex,
        onDestinationSelected: (index) {
          setState(() => currentIndex = index);
        },
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: "Detector"),
          NavigationDestination(
              icon: Icon(Icons.shield_outlined), label: "Protector"),
          NavigationDestination(icon: Icon(Icons.info_outline), label: "Info"),
        ],
      ),
    );
  }
}

class DetectorTab extends StatefulWidget {
  const DetectorTab({super.key});

  @override
  State<DetectorTab> createState() => _DetectorTabState();
}

class _DetectorTabState extends State<DetectorTab> {
  String result = "";
  bool isBullying = false;
  bool isLoading = false;
  bool hasChecked = false;

  final TextEditingController controller = TextEditingController();

  static const String apiUrl =
      "https://cyberbullying-shield-api.onrender.com/predict";

  Future<void> checkText() async {
    if (controller.text.trim().isEmpty) {
      setState(() {
        result = "Please enter some text first.";
        hasChecked = true;
      });
      return;
    }

    setState(() => isLoading = true);

    try {
      final response = await http.post(
        Uri.parse(apiUrl),
        headers: {"Content-Type": "application/json"},
        body: jsonEncode({"text": controller.text}),
      );

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        final prediction = data["prediction"];
        final confidence = (data["confidence"] as num) * 100;

        setState(() {
          isBullying = prediction == "Cyberbullying";
          result = isBullying
              ? "Cyberbullying (${confidence.toStringAsFixed(2)}%)"
              : "Safe (${confidence.toStringAsFixed(2)}%)";
          hasChecked = true;
        });
      } else {
        setState(() {
          result = "Server error: ${response.statusCode}";
          hasChecked = true;
        });
      }
    } catch (e) {
      setState(() {
        result = "Could not reach the API. Make sure api.py is running.";
        hasChecked = true;
      });
    } finally {
      setState(() => isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const Text(
            "Paste any comment or message below to check it for cyberbullying.",
            style: TextStyle(fontSize: 14, color: Colors.grey),
          ),
          const SizedBox(height: 16),
          TextField(
            controller: controller,
            maxLines: 4,
            decoration: InputDecoration(
              hintText: "Enter text to check...",
              border:
                  OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
            ),
          ),
          const SizedBox(height: 20),
          ElevatedButton(
            onPressed: isLoading ? null : checkText,
            child: isLoading
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2))
                : const Text("Check"),
          ),
          const SizedBox(height: 24),
          if (hasChecked)
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: isBullying
                    ? Colors.red.withValues(alpha: 0.1)
                    : Colors.green.withValues(alpha: 0.1),
                borderRadius: BorderRadius.circular(12),
                border:
                    Border.all(color: isBullying ? Colors.red : Colors.green),
              ),
              child: Text(result,
                  style: const TextStyle(fontSize: 18),
                  textAlign: TextAlign.center),
            ),
        ],
      ),
    );
  }
}

class ProtectorTab extends StatefulWidget {
  const ProtectorTab({super.key});

  @override
  State<ProtectorTab> createState() => _ProtectorTabState();
}

class _ProtectorTabState extends State<ProtectorTab> {
  bool isConnected = false;

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.deepPurple.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(12),
            ),
            child: const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text("YouTube Channel Protection",
                    style:
                        TextStyle(fontSize: 16, fontWeight: FontWeight.bold)),
                SizedBox(height: 8),
                Text(
                    "Connect your OWN YouTube channel to automatically detect and remove cyberbullying comments, and block repeat offenders from commenting again.",
                    style: TextStyle(fontSize: 14)),
                SizedBox(height: 8),
                Text(
                    "Note: This only works for channels you own and manage, since YouTube only allows channel owners to moderate their own comments via official API permissions.",
                    style: TextStyle(fontSize: 12, color: Colors.grey)),
              ],
            ),
          ),
          const SizedBox(height: 24),
          if (!isConnected)
            ElevatedButton.icon(
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                      content: Text(
                          "YouTube OAuth connection coming in the next build phase.")),
                );
              },
              icon: const Icon(Icons.link),
              label: const Text("Connect YouTube Channel"),
            ),
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 12),
          const Text("Once connected, this tab will show:",
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const ListTile(
              leading: Icon(Icons.check_circle_outline),
              title: Text("Auto-removed comments log"),
              dense: true),
          const ListTile(
              leading: Icon(Icons.block),
              title: Text("Blocked users list"),
              dense: true),
          const ListTile(
              leading: Icon(Icons.notifications_active_outlined),
              title: Text("Real-time protection status"),
              dense: true),
        ],
      ),
    );
  }
}

class InfoTab extends StatelessWidget {
  const InfoTab({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text("About This App",
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          const SizedBox(height: 12),
          const Text(
              "Cyberbullying Shield is a three-part system designed to detect and reduce cyberbullying across platforms:"),
          const SizedBox(height: 16),
          _infoCard("Detector",
              "Check any text or comment for cyberbullying using a trained machine learning model."),
          _infoCard("Protector",
              "Connect your own YouTube channel to automatically remove harmful comments and block repeat offenders."),
          _infoCard("Browser Extension",
              "A companion Chrome extension highlights harmful comments in real time directly on Facebook, YouTube, and X while you browse."),
          const SizedBox(height: 20),
          const Divider(),
          const SizedBox(height: 12),
          const Text("Known Limitations",
              style: TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 8),
          const Text(
              "The model is trained on English text and may not reliably classify Bengali or other languages. Automatic moderation only works on platforms/content you own, due to platform API restrictions.",
              style: TextStyle(color: Colors.grey)),
        ],
      ),
    );
  }

  Widget _infoCard(String title, String description) {
    return Container(
      margin: const EdgeInsets.only(bottom: 12),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
          const SizedBox(height: 6),
          Text(description),
        ],
      ),
    );
  }
}
