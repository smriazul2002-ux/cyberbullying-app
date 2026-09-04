import 'dart:convert';
import 'dart:math' as math;
import 'dart:ui' as ui;

import 'package:file_saver/file_saver.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

const _apiUrl = String.fromEnvironment('API_URL',
    defaultValue: 'https://cyberbullying-shield-api.onrender.com');
const _adminEmail = String.fromEnvironment('ADMIN_EMAIL', defaultValue: '');

class _Db {
  _Db(this.user);
  final User user;
  String get root => Firebase.app().options.databaseURL!;

  Future<dynamic> call(String path,
      {String method = 'GET', Object? body}) async {
    final token = await user.getIdToken();
    final uri = Uri.parse('$root/$path.json?auth=$token');
    final headers = {'Content-Type': 'application/json'};
    final encoded = body == null ? null : jsonEncode(body);
    late http.Response response;
    if (method == 'POST') {
      response = await http.post(uri, headers: headers, body: encoded);
    } else if (method == 'PUT') {
      response = await http.put(uri, headers: headers, body: encoded);
    } else if (method == 'PATCH') {
      response = await http.patch(uri, headers: headers, body: encoded);
    } else if (method == 'DELETE') {
      response = await http.delete(uri, headers: headers);
    } else {
      response = await http.get(uri, headers: headers);
    }
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw Exception('Database ${response.statusCode}: ${response.body}');
    }
    return response.body.isEmpty || response.body == 'null'
        ? null
        : jsonDecode(response.body);
  }

  List<Map<String, dynamic>> records(dynamic raw) {
    if (raw is! Map) return [];
    final rows = raw.entries
        .map((e) => <String, dynamic>{
              'id': e.key.toString(),
              ...Map<String, dynamic>.from(e.value as Map),
            })
        .toList();
    rows.sort((a, b) => '${b['createdAt']}'.compareTo('${a['createdAt']}'));
    return rows;
  }

  Future<List<Map<String, dynamic>>> history() async =>
      records(await call('analyses/${user.uid}'));
  String _analysisKey(Map<String, dynamic> data) {
    final value =
        '${data['source'] ?? 'Detector'}|${data['externalId'] ?? ''}|${data['text'] ?? ''}'
            .trim()
            .toLowerCase();
    var hash = 0x811c9dc5;
    for (final byte in utf8.encode(value)) {
      hash ^= byte;
      hash = (hash * 0x01000193) & 0xffffffff;
    }
    return 'a_${hash.toRadixString(16).padLeft(8, '0')}';
  }

  Future<void> save(Map<String, dynamic> data) =>
      call('analyses/${user.uid}/${_analysisKey(data)}',
          method: 'PATCH', body: data);
  Future<void> deleteAnalysis(String id) =>
      call('analyses/${user.uid}/$id', method: 'DELETE');
  Future<void> clearHistory() => call('analyses/${user.uid}', method: 'DELETE');
  Future<void> reviewStatus(String analysisId, String value) =>
      call('analyses/${user.uid}/$analysisId', method: 'PATCH', body: {
        'reviewStatus': value,
        'reviewedAt': DateTime.now().toIso8601String(),
      });
  Future<void> feedback(String analysisId, bool correct,
          {String? correctedLabel}) =>
      call('analyses/${user.uid}/$analysisId', method: 'PATCH', body: {
        'feedback': correct ? 'correct' : 'wrong',
        if (correctedLabel != null) 'correctedLabel': correctedLabel,
        'feedbackAt': DateTime.now().toIso8601String(),
      });
  Future<void> report(Map<String, dynamic> data) =>
      call('reports', method: 'POST', body: data);
  Future<List<Map<String, dynamic>>> reports() async =>
      records(await call('reports'));
  Future<void> status(String id, String value) =>
      call('reports/$id', method: 'PATCH', body: {'status': value});
  Future<void> notify(String title, String message) =>
      call('notifications/${user.uid}', method: 'POST', body: {
        'title': title,
        'message': message,
        'read': false,
        'createdAt': DateTime.now().toIso8601String(),
      });
  Future<List<Map<String, dynamic>>> notices() async =>
      records(await call('notifications/${user.uid}'));
  Future<void> read(String id) => call('notifications/${user.uid}/$id',
      method: 'PATCH', body: {'read': true});
  Future<void> block(String email) => call(
          'blocked/${user.uid}/${email.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]'), '_')}',
          method: 'PUT',
          body: {
            'email': email,
            'createdAt': DateTime.now().toIso8601String(),
          });
  Future<List<Map<String, dynamic>>> blocked() async =>
      records(await call('blocked/${user.uid}'));
}

class CompleteHomeScreen extends StatefulWidget {
  const CompleteHomeScreen({super.key});
  @override
  State<CompleteHomeScreen> createState() => _CompleteHomeScreenState();
}

class _CompleteHomeScreenState extends State<CompleteHomeScreen> {
  int selected = 0;
  @override
  Widget build(BuildContext context) {
    final user = FirebaseAuth.instance.currentUser!;
    final db = _Db(user);
    final isAdmin = _adminEmail.isNotEmpty &&
        user.email?.toLowerCase() == _adminEmail.toLowerCase();
    final pages = <Widget>[
      _Dashboard(db),
      _Analytics(db),
      _Detector(db),
      _SocialProtection(db),
      _ReviewQueue(db),
      _DatasetManager(db),
      _History(db),
      _Protection(db),
      _Notices(db),
      if (isAdmin) _Admin(db),
      _Profile(db),
    ];
    final labels = <String>[
      'Dashboard',
      'Analytics',
      'Detector',
      'Facebook & Instagram',
      'Review Queue',
      'Training Dataset',
      'History',
      'YouTube Protection',
      'Notifications',
      if (isAdmin) 'Admin',
      'Profile'
    ];
    final icons = <IconData>[
      Icons.dashboard,
      Icons.analytics,
      Icons.search,
      Icons.forum,
      Icons.fact_check,
      Icons.dataset,
      Icons.history,
      Icons.shield,
      Icons.notifications,
      if (isAdmin) Icons.admin_panel_settings,
      Icons.person
    ];
    if (selected >= pages.length) selected = 0;
    return Scaffold(
      appBar: AppBar(title: Text(labels[selected]), actions: [
        IconButton(
            onPressed: FirebaseAuth.instance.signOut,
            icon: const Icon(Icons.logout))
      ]),
      drawer: NavigationDrawer(
        selectedIndex: selected,
        onDestinationSelected: (i) {
          setState(() => selected = i);
          Navigator.pop(context);
        },
        children: [
          Padding(
              padding: const EdgeInsets.all(20),
              child: Text(user.email ?? '',
                  style: const TextStyle(fontWeight: FontWeight.bold))),
          for (var i = 0; i < labels.length; i++)
            NavigationDrawerDestination(
                icon: Icon(icons[i]), label: Text(labels[i])),
        ],
      ),
      body: pages[selected],
    );
  }
}

Widget _resultTile(Map<String, dynamic> row) {
  final harmful = row['prediction'] == 'Cyberbullying';
  final confidence = ((row['confidence'] ?? 0) as num) * 100;
  final category = '${row['category'] ?? (harmful ? 'Cyberbullying' : 'Safe')}';
  final risk = '${row['risk_level'] ?? (harmful ? 'Medium' : 'Low')}';
  final reasons = row['reasons'] is List
      ? (row['reasons'] as List).map((e) => '$e').join(', ')
      : '';
  final source = '${row['source'] ?? 'Detector'}';
  final modelVersion =
      '${row['model_version'] ?? row['modelVersion'] ?? 'Legacy'}';
  final riskColor = switch (risk) {
    'Critical' => Colors.red.shade900,
    'High' => Colors.red,
    'Medium' => Colors.orange,
    _ => Colors.green,
  };
  return Card(
      child: ListTile(
    leading: Icon(harmful ? Icons.warning : Icons.check_circle,
        color: harmful ? Colors.red : Colors.green),
    title: Text('${row['text'] ?? ''}',
        maxLines: 3, overflow: TextOverflow.ellipsis),
    subtitle: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Text('${row['prediction']} • ${confidence.toStringAsFixed(2)}%'),
      Text('$category • $risk risk',
          style: TextStyle(color: riskColor, fontWeight: FontWeight.w600)),
      Text('Source: $source • Model: $modelVersion'),
      if (reasons.isNotEmpty)
        Text('Reason: $reasons', maxLines: 2, overflow: TextOverflow.ellipsis),
    ]),
    isThreeLine: true,
  ));
}

class _Dashboard extends StatelessWidget {
  const _Dashboard(this.db);
  final _Db db;
  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: db.history(),
      builder: (_, s) {
        if (s.hasError) return _error('${s.error}');
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        final rows = s.data!;
        final harmful =
            rows.where((r) => r['prediction'] == 'Cyberbullying').length;
        return ListView(padding: const EdgeInsets.all(16), children: [
          Wrap(spacing: 12, runSpacing: 12, children: [
            _metric('Scanned', rows.length, Colors.deepPurple),
            _metric('Harmful', harmful, Colors.red),
            _metric('Safe', rows.length - harmful, Colors.green)
          ]),
          const SizedBox(height: 20),
          _SafetyChart(harmful: harmful, safe: rows.length - harmful),
          const SizedBox(height: 24),
          const Text('Recent activity',
              style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold)),
          ...rows.take(5).map(_resultTile),
        ]);
      });
}

class _Analytics extends StatelessWidget {
  const _Analytics(this.db);
  final _Db db;

  Map<String, int> _count(List<Map<String, dynamic>> rows, String field,
      {String fallback = 'Direct detector'}) {
    final values = <String, int>{};
    for (final row in rows) {
      final value = '${row[field] ?? fallback}';
      values[value] = (values[value] ?? 0) + 1;
    }
    final entries = values.entries.toList()
      ..sort((a, b) => b.value.compareTo(a.value));
    return Map.fromEntries(entries);
  }

  Widget _section(String title, Map<String, int> values, int total) => Card(
      child: Padding(
          padding: const EdgeInsets.all(16),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title,
                style:
                    const TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            if (values.isEmpty) const Text('No data yet'),
            ...values.entries.map((entry) {
              final percentage = total == 0 ? 0.0 : entry.value * 100 / total;
              return Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(children: [
                          Expanded(child: Text(entry.key)),
                          Text(
                              '${entry.value} (${percentage.toStringAsFixed(1)}%)')
                        ]),
                        const SizedBox(height: 5),
                        LinearProgressIndicator(
                            value: percentage / 100,
                            minHeight: 9,
                            borderRadius: BorderRadius.circular(8))
                      ]));
            })
          ])));

  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: db.history(),
      builder: (_, snapshot) {
        if (snapshot.hasError) return _error('${snapshot.error}');
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final rows = snapshot.data!;
        final harmful =
            rows.where((row) => row['prediction'] == 'Cyberbullying').toList();
        final offenders = <String, int>{};
        for (final row in harmful) {
          final offender = '${row['offender'] ?? row['author'] ?? ''}'.trim();
          if (offender.isNotEmpty && offender.toLowerCase() != 'unknown') {
            offenders[offender] = (offenders[offender] ?? 0) + 1;
          }
        }
        final repeatOffenders = offenders.entries
            .where((e) => e.value >= 2)
            .toList()
          ..sort((a, b) => b.value.compareTo(a.value));
        return ListView(padding: const EdgeInsets.all(16), children: [
          const Text('Advanced Analytics',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const Text('Live statistics calculated from Firebase history.'),
          const SizedBox(height: 12),
          _TimelineChart(rows: rows),
          Card(
              child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text('Repeat offenders',
                            style: TextStyle(
                                fontSize: 18, fontWeight: FontWeight.bold)),
                        const SizedBox(height: 8),
                        if (repeatOffenders.isEmpty)
                          const Text('No repeat offender detected yet.'),
                        ...repeatOffenders.map((entry) => ListTile(
                              contentPadding: EdgeInsets.zero,
                              leading: const Icon(Icons.person_off,
                                  color: Colors.red),
                              title: Text(entry.key),
                              subtitle: Text('${entry.value} harmful comments'),
                              trailing: Chip(
                                  label: Text(entry.value >= 3
                                      ? 'Block recommended'
                                      : 'Warning recommended')),
                            ))
                      ]))),
          _section('Results', _count(rows, 'prediction', fallback: 'Unknown'),
              rows.length),
          _section(
              'Detected categories',
              _count(harmful, 'category', fallback: 'General harassment'),
              harmful.length),
          _section('Risk levels',
              _count(rows, 'risk_level', fallback: 'Unknown'), rows.length),
          _section('Sources / platforms', _count(rows, 'source'), rows.length),
          _section(
              'Human feedback',
              _count(rows.where((row) => row['feedback'] != null).toList(),
                  'feedback',
                  fallback: 'Not reviewed'),
              rows.where((row) => row['feedback'] != null).length),
          _section(
              'Corrected labels',
              _count(
                  rows.where((row) => row['correctedLabel'] != null).toList(),
                  'correctedLabel',
                  fallback: 'Unspecified'),
              rows.where((row) => row['correctedLabel'] != null).length),
        ]);
      });
}

class _TimelineChart extends StatelessWidget {
  const _TimelineChart({required this.rows});
  final List<Map<String, dynamic>> rows;

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final days = List.generate(7, (index) {
      final date = now.subtract(Duration(days: 6 - index));
      return DateTime(date.year, date.month, date.day);
    });
    final safe = List<int>.filled(7, 0);
    final harmful = List<int>.filled(7, 0);
    for (final row in rows) {
      final created = DateTime.tryParse('${row['createdAt'] ?? ''}')?.toLocal();
      if (created == null) continue;
      final day = DateTime(created.year, created.month, created.day);
      final index = days.indexOf(day);
      if (index < 0) continue;
      if (row['prediction'] == 'Cyberbullying') {
        harmful[index]++;
      } else {
        safe[index]++;
      }
    }
    final labels = days.map((d) => '${d.day}/${d.month}').toList();
    return Card(
        child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(children: [
              const Align(
                  alignment: Alignment.centerLeft,
                  child: Text('7-day detection timeline',
                      style: TextStyle(
                          fontSize: 18, fontWeight: FontWeight.bold))),
              const SizedBox(height: 14),
              SizedBox(
                  height: 210,
                  width: double.infinity,
                  child: CustomPaint(
                      painter: _TimelinePainter(
                          safe: safe, harmful: harmful, labels: labels))),
              const Wrap(spacing: 24, children: [
                Text('● Safe', style: TextStyle(color: Colors.green)),
                Text('● Cyberbullying', style: TextStyle(color: Colors.red)),
              ])
            ])));
  }
}

class _TimelinePainter extends CustomPainter {
  const _TimelinePainter(
      {required this.safe, required this.harmful, required this.labels});
  final List<int> safe;
  final List<int> harmful;
  final List<String> labels;

  @override
  void paint(Canvas canvas, Size size) {
    const left = 24.0;
    const bottom = 28.0;
    final graphHeight = size.height - bottom - 10;
    final graphWidth = size.width - left - 10;
    final maximum = math.max(1, [...safe, ...harmful].fold<int>(0, math.max));
    final axis = Paint()
      ..color = Colors.grey.shade400
      ..strokeWidth = 1;
    canvas.drawLine(Offset(left, 5), Offset(left, graphHeight), axis);
    canvas.drawLine(
        Offset(left, graphHeight), Offset(size.width - 5, graphHeight), axis);

    void drawLine(List<int> values, Color color) {
      final paint = Paint()
        ..color = color
        ..strokeWidth = 3
        ..style = PaintingStyle.stroke;
      final path = Path();
      for (var i = 0; i < values.length; i++) {
        final x = left + graphWidth * i / (values.length - 1);
        final y = graphHeight - (values[i] / maximum) * (graphHeight - 15);
        if (i == 0) {
          path.moveTo(x, y);
        } else {
          path.lineTo(x, y);
        }
        canvas.drawCircle(Offset(x, y), 4, Paint()..color = color);
      }
      canvas.drawPath(path, paint);
    }

    drawLine(safe, Colors.green);
    drawLine(harmful, Colors.red);
    for (var i = 0; i < labels.length; i++) {
      final painter = TextPainter(
          text: TextSpan(
              text: labels[i],
              style: const TextStyle(fontSize: 10, color: Colors.black54)),
          textDirection: TextDirection.ltr)
        ..layout();
      final x = left + graphWidth * i / (labels.length - 1);
      painter.paint(canvas, Offset(x - painter.width / 2, graphHeight + 6));
    }
  }

  @override
  bool shouldRepaint(covariant _TimelinePainter oldDelegate) =>
      oldDelegate.safe != safe || oldDelegate.harmful != harmful;
}

class _SafetyChart extends StatelessWidget {
  const _SafetyChart({required this.harmful, required this.safe});
  final int harmful, safe;
  @override
  Widget build(BuildContext context) {
    final total = harmful + safe;
    final harmfulPct = total == 0 ? 0.0 : harmful * 100 / total;
    final safePct = total == 0 ? 0.0 : safe * 100 / total;
    return Card(
        child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(children: [
              const Text('Cyberbullying Analysis',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
              const SizedBox(height: 18),
              SizedBox(
                  width: 270,
                  height: 270,
                  child: Stack(alignment: Alignment.center, children: [
                    CustomPaint(
                        size: const Size.square(270),
                        painter: _DonutPainter(
                            safeFraction: total == 0 ? 0 : safe / total)),
                    Column(mainAxisSize: MainAxisSize.min, children: [
                      Text('$total',
                          style: const TextStyle(
                              fontSize: 34, fontWeight: FontWeight.bold)),
                      const Text('Comments checked')
                    ])
                  ])),
              const SizedBox(height: 18),
              Wrap(spacing: 28, runSpacing: 10, children: [
                Text('🔴 Cyberbullying ${harmfulPct.toStringAsFixed(1)}%',
                    style: const TextStyle(fontWeight: FontWeight.w600)),
                Text('🟢 Safe ${safePct.toStringAsFixed(1)}%',
                    style: const TextStyle(fontWeight: FontWeight.w600))
              ]),
            ])));
  }
}

class _DonutPainter extends CustomPainter {
  const _DonutPainter({required this.safeFraction});
  final double safeFraction;

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height / 2);
    final radius = math.min(size.width, size.height) / 2 - 12;
    final strokeWidth = radius * .42;
    final rect =
        Rect.fromCircle(center: center, radius: radius - strokeWidth / 2);
    final paint = Paint()
      ..style = PaintingStyle.stroke
      ..strokeWidth = strokeWidth
      ..strokeCap = StrokeCap.butt;
    if (safeFraction <= 0) {
      paint.color = const Color(0xFFE0E0E0);
      canvas.drawArc(rect, 0, math.pi * 2, false, paint);
      return;
    }
    final start = -math.pi / 2;
    final safeSweep = math.pi * 2 * safeFraction;
    paint.color = const Color(0xFF49D77C);
    canvas.drawArc(rect, start, safeSweep, false, paint);
    paint.color = const Color(0xFFFF6F72);
    canvas.drawArc(
        rect, start + safeSweep, math.pi * 2 - safeSweep, false, paint);
  }

  @override
  bool shouldRepaint(covariant _DonutPainter oldDelegate) =>
      oldDelegate.safeFraction != safeFraction;
}

class _SocialProtection extends StatefulWidget {
  const _SocialProtection(this.db);
  final _Db db;
  @override
  State<_SocialProtection> createState() => _SocialProtectionState();
}

class _SocialProtectionState extends State<_SocialProtection> {
  final comments = TextEditingController();
  String platform = 'Facebook';
  bool busy = false;
  String error = '';
  List<Map<String, dynamic>> results = [];
  @override
  void dispose() {
    comments.dispose();
    super.dispose();
  }

  Future<void> scan() async {
    final lines = comments.text
        .split('\n')
        .map((e) => e.trim())
        .where((e) => e.isNotEmpty)
        .toList();
    if (lines.isEmpty) return;
    setState(() {
      busy = true;
      error = '';
      results = [];
    });
    try {
      final found = <Map<String, dynamic>>[];
      for (final line in lines.take(100)) {
        final response = await http.post(Uri.parse('$_apiUrl/predict'),
            headers: {'Content-Type': 'application/json'},
            body: jsonEncode({'text': line}));
        if (response.statusCode != 200) {
          throw Exception('API ${response.statusCode}: ${response.body}');
        }
        final data = Map<String, dynamic>.from(jsonDecode(response.body));
        data.addAll({
          'source': platform,
          'reviewStatus': data['prediction'] == 'Cyberbullying'
              ? 'pending'
              : 'not_required',
          'createdAt': DateTime.now().toIso8601String()
        });
        await widget.db.save(data);
        found.add(data);
      }
      final flagged =
          found.where((e) => e['prediction'] == 'Cyberbullying').length;
      await widget.db.notify('$platform scan complete',
          'Checked ${found.length}; flagged $flagged. Review flagged comments before taking action.');
      if (mounted) setState(() => results = found);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final flagged =
        results.where((e) => e['prediction'] == 'Cyberbullying').length;
    return ListView(padding: const EdgeInsets.all(18), children: [
      const Text(
          'Paste comments below, one comment per line. Emoji inside a comment is also checked.'),
      const SizedBox(height: 12),
      SegmentedButton<String>(segments: const [
        ButtonSegment(
            value: 'Facebook',
            label: Text('Facebook'),
            icon: Icon(Icons.facebook)),
        ButtonSegment(
            value: 'Instagram',
            label: Text('Instagram'),
            icon: Icon(Icons.camera_alt))
      ], selected: {
        platform
      }, onSelectionChanged: (v) => setState(() => platform = v.first)),
      const SizedBox(height: 12),
      TextField(
          controller: comments,
          minLines: 7,
          maxLines: 12,
          decoration: const InputDecoration(
              labelText: 'Comments (one per line)',
              hintText: 'Great video 😊\nYou are stupid 🤬\nI will hurt you 🔪',
              border: OutlineInputBorder())),
      const SizedBox(height: 12),
      FilledButton.icon(
          onPressed: busy ? null : scan,
          icon: const Icon(Icons.security),
          label: Text(busy ? 'Checking...' : 'Check comments')),
      if (error.isNotEmpty)
        Padding(
            padding: const EdgeInsets.all(12),
            child: Text(error, style: const TextStyle(color: Colors.red))),
      if (results.isNotEmpty) ...[
        Padding(
            padding: const EdgeInsets.symmetric(vertical: 12),
            child: Text(
                'Checked ${results.length} • Flagged $flagged • Review before manually hiding/removing',
                style: const TextStyle(fontWeight: FontWeight.bold))),
        ...results.map(_resultTile)
      ],
    ]);
  }
}

Widget _metric(String label, int value, Color color) => SizedBox(
    width: 170,
    child: Card(
        child: Padding(
            padding: const EdgeInsets.all(18),
            child: Column(children: [
              Text('$value',
                  style: TextStyle(
                      fontSize: 30, color: color, fontWeight: FontWeight.bold)),
              Text(label)
            ]))));
Widget _error(String message) => Center(
    child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(message, style: const TextStyle(color: Colors.red))));

class _Detector extends StatefulWidget {
  const _Detector(this.db);
  final _Db db;
  @override
  State<_Detector> createState() => _DetectorState();
}

class _DetectorState extends State<_Detector> {
  final text = TextEditingController();
  final offender = TextEditingController();
  Map<String, dynamic>? result;
  bool busy = false;
  String error = '';
  @override
  void dispose() {
    text.dispose();
    offender.dispose();
    super.dispose();
  }

  Future<void> analyze() async {
    if (text.text.trim().isEmpty) return;
    setState(() {
      busy = true;
      error = '';
    });
    try {
      final response = await http.post(Uri.parse('$_apiUrl/predict'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({'text': text.text.trim()}));
      if (response.statusCode != 200) {
        throw Exception('API ${response.statusCode}: ${response.body}');
      }
      final data = Map<String, dynamic>.from(jsonDecode(response.body));
      data['source'] = 'Detector';
      data['reviewStatus'] =
          data['prediction'] == 'Cyberbullying' ? 'pending' : 'not_required';
      data['createdAt'] = DateTime.now().toIso8601String();
      await widget.db.save(data);
      if (data['prediction'] == 'Cyberbullying') {
        await widget.db.notify('Cyberbullying detected',
            'A harmful message was saved in your history.');
      }
      if (mounted) setState(() => result = data);
    } catch (e) {
      if (mounted) setState(() => error = '$e');
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  Future<void> reportAndBlock() async {
    if (result == null) return;
    final email = offender.text.trim();
    result!['offender'] = email;
    result!['reviewStatus'] = 'pending';
    await widget.db.save(result!);
    await widget.db.report({
      'text': result!['text'],
      'prediction': result!['prediction'],
      'confidence': result!['confidence'],
      'reportedUser': email,
      'reportedBy': FirebaseAuth.instance.currentUser!.email,
      'reporterUid': FirebaseAuth.instance.currentUser!.uid,
      'status': 'pending',
      'createdAt': DateTime.now().toIso8601String(),
    });
    if (email.isNotEmpty) await widget.db.block(email);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
          content: Text('Report saved. Supplied offender was blocked.')));
    }
  }

  @override
  Widget build(BuildContext context) =>
      ListView(padding: const EdgeInsets.all(18), children: [
        TextField(
            controller: text,
            minLines: 4,
            maxLines: 7,
            decoration: const InputDecoration(
                labelText: 'Message or comment', border: OutlineInputBorder())),
        const SizedBox(height: 12),
        FilledButton.icon(
            onPressed: busy ? null : analyze,
            icon: const Icon(Icons.psychology),
            label: Text(busy ? 'Analyzing...' : 'Analyze with ML model')),
        if (error.isNotEmpty)
          Padding(
              padding: const EdgeInsets.all(12),
              child: Text(error, style: const TextStyle(color: Colors.red))),
        if (result != null) ...[
          const SizedBox(height: 14),
          _resultTile(result!),
          TextField(
              controller: offender,
              decoration: const InputDecoration(
                  labelText: 'Offender email (optional)',
                  border: OutlineInputBorder())),
          OutlinedButton.icon(
              onPressed: reportAndBlock,
              icon: const Icon(Icons.report),
              label: const Text('Report / block user')),
        ],
      ]);
}

class _ReviewQueue extends StatefulWidget {
  const _ReviewQueue(this.db);
  final _Db db;
  @override
  State<_ReviewQueue> createState() => _ReviewQueueState();
}

class _ReviewQueueState extends State<_ReviewQueue> {
  String filter = 'pending';

  Future<void> _setStatus(Map<String, dynamic> row, String status) async {
    await widget.db.reviewStatus('${row['id']}', status);
    if (mounted) setState(() {});
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: widget.db.history(),
      builder: (_, snapshot) {
        if (snapshot.hasError) return _error('${snapshot.error}');
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final flagged = snapshot.data!
            .where((row) => row['prediction'] == 'Cyberbullying')
            .toList();
        final rows = filter == 'all'
            ? flagged
            : flagged
                .where((row) => '${row['reviewStatus'] ?? 'pending'}' == filter)
                .toList();
        return ListView(padding: const EdgeInsets.all(16), children: [
          const Text('Flagged comments from every platform appear here.',
              style: TextStyle(fontSize: 16, fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'pending', label: Text('Pending')),
                ButtonSegment(value: 'confirmed', label: Text('Confirmed')),
                ButtonSegment(value: 'ignored', label: Text('Ignored')),
                ButtonSegment(value: 'all', label: Text('All')),
              ],
              selected: {
                filter
              },
              onSelectionChanged: (value) =>
                  setState(() => filter = value.first)),
          const SizedBox(height: 12),
          if (rows.isEmpty)
            const Card(
                child: ListTile(
                    leading: Icon(Icons.verified, color: Colors.green),
                    title: Text('No comments in this queue.')))
          else
            ...rows.map((row) => Column(children: [
                  _resultTile(row),
                  Padding(
                      padding: const EdgeInsets.fromLTRB(12, 0, 12, 10),
                      child: Row(children: [
                        Text('Status: ${row['reviewStatus'] ?? 'pending'}'),
                        const Spacer(),
                        TextButton.icon(
                            onPressed: () => _setStatus(row, 'ignored'),
                            icon: const Icon(Icons.visibility_off),
                            label: const Text('Ignore')),
                        const SizedBox(width: 8),
                        FilledButton.icon(
                            onPressed: () => _setStatus(row, 'confirmed'),
                            icon: const Icon(Icons.check),
                            label: const Text('Confirm')),
                      ]))
                ]))
        ]);
      });
}

class _DatasetManager extends StatelessWidget {
  const _DatasetManager(this.db);
  final _Db db;

  String _cell(Object? value) =>
      '"${'$value'.replaceAll('"', '""').replaceAll('\n', ' ')}"';

  Future<void> _export(List<Map<String, dynamic>> rows) async {
    final lines = <String>[
      'text,label,original_prediction,category,source,model_version,feedback,created_at',
      ...rows.map((row) {
        final label = row['correctedLabel'] ??
            (row['prediction'] == 'Safe' ? 'Safe' : row['category']);
        return [
          row['text'],
          label,
          row['prediction'],
          row['category'],
          row['source'] ?? 'Detector',
          row['model_version'] ?? 'Legacy',
          row['feedback'],
          row['createdAt'],
        ].map(_cell).join(',');
      })
    ];
    await FileSaver.instance.saveFile(
        name: 'reviewed_training_dataset',
        bytes: Uint8List.fromList(utf8.encode(lines.join('\n'))),
        fileExtension: 'csv',
        mimeType: MimeType.csv);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: db.history(),
      builder: (_, snapshot) {
        if (snapshot.hasError) return _error('${snapshot.error}');
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final all = snapshot.data!;
        final reviewed = all
            .where((row) =>
                row['feedback'] == 'correct' || row['feedback'] == 'wrong')
            .toList();
        final corrected =
            reviewed.where((row) => row['correctedLabel'] != null).length;
        return ListView(padding: const EdgeInsets.all(16), children: [
          const Text('Human-reviewed Training Dataset',
              style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold)),
          const Text(
              'Only reviewed predictions are exported, so they can be used to improve the next model.'),
          const SizedBox(height: 12),
          Wrap(spacing: 12, runSpacing: 12, children: [
            _metric('All records', all.length, Colors.deepPurple),
            _metric('Reviewed', reviewed.length, Colors.blue),
            _metric('Corrected', corrected, Colors.orange),
          ]),
          const SizedBox(height: 12),
          FilledButton.icon(
              onPressed: reviewed.isEmpty ? null : () => _export(reviewed),
              icon: const Icon(Icons.download),
              label: const Text('Download training CSV')),
          const SizedBox(height: 12),
          if (reviewed.isEmpty)
            const Card(
                child: ListTile(
                    title: Text('No reviewed data yet'),
                    subtitle: Text(
                        'Open History and use thumbs up or thumbs down first.')))
          else
            ...reviewed.map((row) => Card(
                    child: ListTile(
                  leading:
                      const Icon(Icons.verified_user, color: Colors.deepPurple),
                  title: Text('${row['text'] ?? ''}',
                      maxLines: 2, overflow: TextOverflow.ellipsis),
                  subtitle: Text(
                      'Training label: ${row['correctedLabel'] ?? (row['prediction'] == 'Safe' ? 'Safe' : row['category'])}\nSource: ${row['source'] ?? 'Detector'}'),
                  isThreeLine: true,
                )))
        ]);
      });
}

class _History extends StatefulWidget {
  const _History(this.db);
  final _Db db;
  @override
  State<_History> createState() => _HistoryState();
}

class _HistoryState extends State<_History> {
  final search = TextEditingController();
  String sourceFilter = 'All';
  String riskFilter = 'All';

  @override
  void dispose() {
    search.dispose();
    super.dispose();
  }

  String _csvCell(Object? value) =>
      '"${'$value'.replaceAll('"', '""').replaceAll('\n', ' ')}"';

  Future<void> _exportCsv(List<Map<String, dynamic>> rows) async {
    final lines = <String>[
      'Text,Prediction,Confidence,Category,Risk,Source,Model Version,Review Status,Feedback,Corrected Label,Created At',
      ...rows.map((row) => [
            row['text'],
            row['prediction'],
            row['confidence'],
            row['category'],
            row['risk_level'],
            row['source'] ?? 'Detector',
            row['model_version'] ?? row['modelVersion'] ?? 'Legacy',
            row['reviewStatus'] ?? 'not reviewed',
            row['feedback'] ?? 'not reviewed',
            row['correctedLabel'] ?? '',
            row['createdAt']
          ].map(_csvCell).join(','))
    ];
    await FileSaver.instance.saveFile(
        name: 'cyberbullying_history',
        bytes: Uint8List.fromList(utf8.encode(lines.join('\n'))),
        fileExtension: 'csv',
        mimeType: MimeType.csv);
  }

  String _pdfText(Object? value) => '$value'
      .replaceAll(RegExp(r'[\u{1F000}-\u{1FAFF}]', unicode: true), '[emoji]')
      .replaceAll(RegExp(r'[\u{2600}-\u{27BF}]', unicode: true), '[symbol]')
      .replaceAll('\uFE0F', '');

  Future<Uint8List> _renderUnicodeText(String value) async {
    final painter = TextPainter(
        text: TextSpan(
            text: _pdfText(value),
            style: const TextStyle(
                fontFamily: 'Noto Sans Bengali',
                fontSize: 28,
                color: Colors.black)),
        textDirection: TextDirection.ltr,
        maxLines: 5)
      ..layout(maxWidth: 900);
    final recorder = ui.PictureRecorder();
    final canvas = Canvas(recorder);
    painter.paint(canvas, const Offset(4, 4));
    final picture = recorder.endRecording();
    final image = await picture.toImage(math.max(1, painter.width.ceil() + 8),
        math.max(1, painter.height.ceil() + 8));
    final bytes = await image.toByteData(format: ui.ImageByteFormat.png);
    image.dispose();
    return bytes!.buffer.asUint8List();
  }

  Future<void> _exportPdf(List<Map<String, dynamic>> rows) async {
    final harmful =
        rows.where((row) => row['prediction'] == 'Cyberbullying').length;
    final latin =
        pw.Font.ttf(await rootBundle.load('assets/fonts/NotoSans.ttf'));
    final bangla =
        pw.Font.ttf(await rootBundle.load('assets/fonts/NotoSansBengali.ttf'));
    final commentImages = await Future.wait(
        rows.map((row) => _renderUnicodeText('${row['text'] ?? ''}')));
    final document = pw.Document();
    document.addPage(pw.MultiPage(
        pageFormat: PdfPageFormat.a4,
        theme: pw.ThemeData.withFont(
            base: latin, bold: latin, fontFallback: [bangla]),
        build: (_) => [
              pw.Text('Cyberbullying Shield - Analysis Report',
                  style: pw.TextStyle(
                      fontSize: 22, fontWeight: pw.FontWeight.bold)),
              pw.SizedBox(height: 8),
              pw.Text('Generated: ${DateTime.now()}'),
              pw.Text('Total checked: ${rows.length}'),
              pw.Text('Cyberbullying: $harmful'),
              pw.Text('Safe: ${rows.length - harmful}'),
              pw.SizedBox(height: 16),
              pw.TableHelper.fromTextArray(
                  headers: const [
                    'Comment',
                    'Result',
                    'Category',
                    'Risk',
                    'Feedback'
                  ],
                  columnWidths: const {
                    0: pw.FlexColumnWidth(3)
                  },
                  data: List.generate(rows.length, (index) {
                    final row = rows[index];
                    return [
                      pw.Image(pw.MemoryImage(commentImages[index]),
                          fit: pw.BoxFit.contain),
                      _pdfText(row['prediction']),
                      _pdfText(row['category'] ?? '-'),
                      _pdfText(row['risk_level'] ?? '-'),
                      _pdfText(row['feedback'] ?? 'not reviewed')
                    ];
                  }))
            ]));
    await FileSaver.instance.saveFile(
        name: 'cyberbullying_report',
        bytes: await document.save(),
        fileExtension: 'pdf',
        mimeType: MimeType.pdf);
  }

  Future<void> _deleteOne(Map<String, dynamic> row) async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
              title: const Text('Delete this history item?'),
              content: Text('${row['text'] ?? ''}',
                  maxLines: 3, overflow: TextOverflow.ellipsis),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(dialogContext, false),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () => Navigator.pop(dialogContext, true),
                    child: const Text('Delete'))
              ],
            ));
    if (confirmed == true) {
      await widget.db.deleteAnalysis('${row['id']}');
      if (mounted) setState(() {});
    }
  }

  Future<void> _clearAll() async {
    final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => AlertDialog(
              title: const Text('Clear all history?'),
              content: const Text(
                  'This permanently deletes your analysis history and cannot be undone.'),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(dialogContext, false),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () => Navigator.pop(dialogContext, true),
                    child: const Text('Clear all'))
              ],
            ));
    if (confirmed == true) {
      await widget.db.clearHistory();
      if (mounted) setState(() {});
    }
  }

  Future<void> _sendFeedback(Map<String, dynamic> row, bool correct) async {
    String? correctedLabel;
    if (!correct) {
      correctedLabel = await _chooseCorrectLabel();
      if (correctedLabel == null) return;
    }
    await widget.db
        .feedback('${row['id']}', correct, correctedLabel: correctedLabel);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(correct
              ? 'Feedback saved: prediction is correct'
              : 'Feedback saved: prediction needs correction')));
      setState(() {});
    }
  }

  Future<String?> _chooseCorrectLabel() async {
    String selectedLabel = 'Safe';
    return showDialog<String>(
        context: context,
        builder: (dialogContext) => AlertDialog(
              title: const Text('Select the correct label'),
              content: DropdownButtonFormField<String>(
                  initialValue: selectedLabel,
                  decoration: const InputDecoration(
                      labelText: 'Correct classification',
                      border: OutlineInputBorder()),
                  items: const [
                    'Safe',
                    'Insult',
                    'Threat',
                    'Hate speech',
                    'Sexual harassment',
                    'Body shaming',
                    'Self-harm encouragement',
                    'General harassment'
                  ]
                      .map((label) =>
                          DropdownMenuItem(value: label, child: Text(label)))
                      .toList(),
                  onChanged: (value) {
                    if (value != null) selectedLabel = value;
                  }),
              actions: [
                TextButton(
                    onPressed: () => Navigator.pop(dialogContext),
                    child: const Text('Cancel')),
                FilledButton(
                    onPressed: () =>
                        Navigator.pop(dialogContext, selectedLabel),
                    child: const Text('Save correction'))
              ],
            ));
  }

  Widget _historyCard(Map<String, dynamic> row) => Column(children: [
        _resultTile(row),
        if (row['correctedLabel'] != null)
          Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              child: Align(
                  alignment: Alignment.centerLeft,
                  child: Text('Human correction: ${row['correctedLabel']}',
                      style: const TextStyle(
                          color: Colors.deepPurple,
                          fontWeight: FontWeight.bold)))),
        Padding(
            padding: const EdgeInsets.fromLTRB(12, 0, 12, 8),
            child: Row(children: [
              const Text('Was this prediction correct?'),
              const Spacer(),
              IconButton.filledTonal(
                  tooltip: 'Correct prediction',
                  onPressed: () => _sendFeedback(row, true),
                  icon: Icon(Icons.thumb_up,
                      color:
                          row['feedback'] == 'correct' ? Colors.green : null)),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                  tooltip: 'Wrong prediction',
                  onPressed: () => _sendFeedback(row, false),
                  icon: Icon(Icons.thumb_down,
                      color: row['feedback'] == 'wrong' ? Colors.red : null)),
              const SizedBox(width: 8),
              IconButton.filledTonal(
                  tooltip: 'Delete item',
                  onPressed: () => _deleteOne(row),
                  icon: const Icon(Icons.delete_outline)),
            ]))
      ]);

  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: widget.db.history(),
      builder: (_, s) {
        if (s.hasError) return _error('${s.error}');
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        final allRows = s.data!;
        final query = search.text.trim().toLowerCase();
        final rows = allRows.where((row) {
          final matchesText = query.isEmpty ||
              '${row['text'] ?? ''}'.toLowerCase().contains(query) ||
              '${row['category'] ?? ''}'.toLowerCase().contains(query);
          final matchesSource = sourceFilter == 'All' ||
              '${row['source'] ?? 'Detector'}' == sourceFilter;
          final matchesRisk = riskFilter == 'All' ||
              '${row['risk_level'] ?? 'Low'}' == riskFilter;
          return matchesText && matchesSource && matchesRisk;
        }).toList();
        return ListView(padding: const EdgeInsets.all(12), children: [
          TextField(
              controller: search,
              onChanged: (_) => setState(() {}),
              decoration: const InputDecoration(
                  prefixIcon: Icon(Icons.search),
                  labelText: 'Search comment or category',
                  border: OutlineInputBorder())),
          const SizedBox(height: 10),
          Wrap(spacing: 10, runSpacing: 10, children: [
            DropdownButton<String>(
                value: sourceFilter,
                items: const [
                  'All',
                  'Detector',
                  'Facebook',
                  'Instagram',
                  'YouTube'
                ]
                    .map((value) => DropdownMenuItem(
                        value: value, child: Text('Source: $value')))
                    .toList(),
                onChanged: (value) =>
                    setState(() => sourceFilter = value ?? 'All')),
            DropdownButton<String>(
                value: riskFilter,
                items: const ['All', 'Low', 'Medium', 'High', 'Critical']
                    .map((value) => DropdownMenuItem(
                        value: value, child: Text('Risk: $value')))
                    .toList(),
                onChanged: (value) =>
                    setState(() => riskFilter = value ?? 'All')),
            Chip(label: Text('${rows.length} results')),
          ]),
          const SizedBox(height: 8),
          Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
                onPressed: allRows.isEmpty ? null : () => _exportCsv(rows),
                icon: const Icon(Icons.table_view),
                label: const Text('Download CSV')),
            OutlinedButton.icon(
                onPressed: allRows.isEmpty ? null : () => _exportPdf(rows),
                icon: const Icon(Icons.picture_as_pdf),
                label: const Text('Download PDF')),
            OutlinedButton.icon(
                onPressed: allRows.isEmpty ? null : _clearAll,
                icon: const Icon(Icons.delete_sweep),
                label: const Text('Clear all')),
          ]),
          const SizedBox(height: 8),
          if (rows.isEmpty)
            const ListTile(title: Text('No matching analyses found.'))
          else
            ...rows.map(_historyCard)
        ]);
      });
}

class _Notices extends StatefulWidget {
  const _Notices(this.db);
  final _Db db;
  @override
  State<_Notices> createState() => _NoticesState();
}

class _NoticesState extends State<_Notices> {
  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: widget.db.notices(),
      builder: (_, s) {
        if (s.hasError) return _error('${s.error}');
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        return ListView(
            padding: const EdgeInsets.all(12),
            children: s.data!
                .map((n) => Card(
                        child: ListTile(
                      leading: Icon(
                          n['read'] == true
                              ? Icons.notifications_none
                              : Icons.notifications_active,
                          color: Colors.deepPurple),
                      title: Text('${n['title'] ?? ''}'),
                      subtitle: Text('${n['message'] ?? ''}'),
                      onTap: () async {
                        await widget.db.read('${n['id']}');
                        if (mounted) setState(() {});
                      },
                    )))
                .toList());
      });
}

class _Profile extends StatelessWidget {
  const _Profile(this.db);
  final _Db db;
  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: db.blocked(),
      builder: (_, s) => ListView(padding: const EdgeInsets.all(18), children: [
            const CircleAvatar(radius: 42, child: Icon(Icons.person, size: 42)),
            const SizedBox(height: 10),
            Center(
                child: Text(FirebaseAuth.instance.currentUser?.email ?? '',
                    style: const TextStyle(fontWeight: FontWeight.bold))),
            const SizedBox(height: 24),
            const Text('Blocked users',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold)),
            if (s.hasData)
              ...s.data!.map((e) => ListTile(
                  leading: const Icon(Icons.block),
                  title: Text('${e['email'] ?? ''}'))),
            const Divider(),
            ListTile(
                leading: const Icon(Icons.logout),
                title: const Text('Logout'),
                onTap: FirebaseAuth.instance.signOut),
          ]));
}

class _Admin extends StatefulWidget {
  const _Admin(this.db);
  final _Db db;
  @override
  State<_Admin> createState() => _AdminState();
}

class _AdminState extends State<_Admin> {
  @override
  Widget build(BuildContext context) => FutureBuilder(
      future: widget.db.reports(),
      builder: (_, s) {
        if (s.hasError) return _error('Admin access failed: ${s.error}');
        if (!s.hasData) return const Center(child: CircularProgressIndicator());
        return ListView(
            padding: const EdgeInsets.all(12),
            children: s.data!
                .map((r) => Card(
                        child: ListTile(
                      title: Text('${r['text'] ?? ''}'),
                      subtitle: Text(
                          'Offender: ${r['reportedUser'] ?? 'unknown'} • ${r['status'] ?? 'pending'}'),
                      trailing: PopupMenuButton<String>(
                          onSelected: (value) async {
                            await widget.db.status('${r['id']}', value);
                            if (mounted) setState(() {});
                          },
                          itemBuilder: (_) => const [
                                PopupMenuItem(
                                    value: 'confirmed',
                                    child: Text('Confirm violation')),
                                PopupMenuItem(
                                    value: 'dismissed', child: Text('Dismiss'))
                              ]),
                    )))
                .toList());
      });
}

class _Protection extends StatefulWidget {
  const _Protection(this.db);
  final _Db db;
  @override
  State<_Protection> createState() => _ProtectionState();
}

class _ProtectionState extends State<_Protection> {
  final video = TextEditingController(),
      apiKey = TextEditingController(),
      accessToken = TextEditingController();
  bool remove = false, busy = false;
  String status = '';
  List<dynamic> comments = [];
  @override
  void dispose() {
    video.dispose();
    apiKey.dispose();
    accessToken.dispose();
    super.dispose();
  }

  String idFrom(String input) {
    final value = input.trim();
    final uri = Uri.tryParse(value);
    if (uri?.queryParameters['v'] != null) return uri!.queryParameters['v']!;
    if (uri != null && uri.pathSegments.isNotEmpty) {
      if (uri.host == 'youtu.be') return uri.pathSegments.first;
      final markerIndex = uri.pathSegments.indexWhere((segment) =>
          segment == 'live' || segment == 'shorts' || segment == 'embed');
      if (markerIndex >= 0 && markerIndex + 1 < uri.pathSegments.length) {
        return uri.pathSegments[markerIndex + 1];
      }
    }
    return value;
  }

  Future<void> scan() async {
    setState(() {
      busy = true;
      status = '';
    });
    try {
      final response = await http.post(Uri.parse('$_apiUrl/youtube/protect'),
          headers: {'Content-Type': 'application/json'},
          body: jsonEncode({
            'video_id': idFrom(video.text),
            'api_key': apiKey.text.trim(),
            'max_comments': 30,
            'auto_remove': remove,
            'oauth_access_token': accessToken.text.trim().isEmpty
                ? null
                : accessToken.text.trim(),
          }));
      if (response.statusCode != 200) throw Exception(response.body);
      final data = jsonDecode(response.body);
      final scanned = (data['comments'] as List)
          .map((comment) => Map<String, dynamic>.from(comment as Map))
          .toList();
      for (final comment in scanned) {
        comment.addAll({
          'source': 'YouTube',
          'externalId': comment['comment_id'],
          'reviewStatus': comment['prediction'] == 'Cyberbullying'
              ? 'pending'
              : 'not_required',
          'createdAt': DateTime.now().toIso8601String(),
        });
        await widget.db.save(comment);
      }
      comments = scanned;
      status =
          'Checked ${data['checked']}; flagged ${data['flagged']}; removed ${data['removed']}';
      await widget.db.notify('YouTube protection complete', status);
    } catch (e) {
      status = 'Protection failed: $e';
    } finally {
      if (mounted) setState(() => busy = false);
    }
  }

  @override
  Widget build(BuildContext context) =>
      ListView(padding: const EdgeInsets.all(18), children: [
        const Text(
            'Analyze comments on a video you own. Automatic removal needs a short-lived channel-owner OAuth token with the YouTube force-ssl scope.'),
        const SizedBox(height: 12),
        TextField(
            controller: video,
            decoration: const InputDecoration(
                labelText: 'YouTube URL or video ID',
                border: OutlineInputBorder())),
        TextField(
            controller: apiKey,
            obscureText: true,
            decoration: const InputDecoration(
                labelText: 'YouTube Data API key',
                border: OutlineInputBorder())),
        SwitchListTile(
            value: remove,
            onChanged: (v) => setState(() => remove = v),
            title: const Text('Automatically remove flagged comments')),
        if (remove)
          TextField(
              controller: accessToken,
              obscureText: true,
              decoration: const InputDecoration(
                  labelText: 'Owner OAuth access token',
                  border: OutlineInputBorder())),
        FilledButton.icon(
            onPressed: busy ? null : scan,
            icon: const Icon(Icons.shield),
            label: Text(busy ? 'Checking...' : 'Protect video')),
        if (status.isNotEmpty)
          Padding(padding: const EdgeInsets.all(12), child: Text(status)),
        ...comments.map((c) => _resultTile(Map<String, dynamic>.from(c))),
      ]);
}
