import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() {
  runApp(MyApp());
}

class MyApp extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      home: Home(),
      debugShowCheckedModeBanner: false,
    );
  }
}

class Home extends StatefulWidget {
  @override
  _HomeState createState() => _HomeState();
}

class _HomeState extends State<Home> {
  String result = "";
  TextEditingController controller = TextEditingController();

  Future<void> checkText() async {
    final response = await http.post(
      Uri.parse("http://127.0.0.1:5000/predict"),
      headers: {"Content-Type": "application/json"},
      body: jsonEncode({"text": controller.text}),
    );

    final data = jsonDecode(response.body);

    setState(() {
      if (data["result"] == 1) {
        result =
            "😡 Cyberbullying (${(data["confidence"] * 100).toStringAsFixed(2)}%)";
      } else {
        result =
            "😊 Safe (${(data["confidence"] * 100).toStringAsFixed(2)}%)";
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text("🚫 Cyberbullying Detector")),
      body: Padding(
        padding: EdgeInsets.all(20),
        child: Column(
          children: [
            TextField(
              controller: controller,
              decoration: InputDecoration(
                hintText: "Enter text...",
                border: OutlineInputBorder(),
              ),
            ),
            SizedBox(height: 20),
            ElevatedButton(
              onPressed: checkText,
              child: Text("Check"),
            ),
            SizedBox(height: 20),
            Text(result, style: TextStyle(fontSize: 20)),
          ],
        ),
      ),
    );
  }
}