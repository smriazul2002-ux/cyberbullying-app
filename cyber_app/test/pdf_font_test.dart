import 'dart:io';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pdf/pdf.dart';
import 'package:pdf/widgets.dart' as pw;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('Bengali PDF fonts render a report', () async {
    final flutterFont = FontLoader('Noto Sans Bengali')
      ..addFont(rootBundle.load('assets/fonts/NotoSansBengali.ttf'));
    await flutterFont.load();
    final latin =
        pw.Font.ttf(await rootBundle.load('assets/fonts/NotoSans.ttf'));
    final bangla =
        pw.Font.ttf(await rootBundle.load('assets/fonts/NotoSansBengali.ttf'));
    final painter = TextPainter(
        text: const TextSpan(
            text: 'বাংলা মন্তব্য: তুমি খুব ভালো কাজ করেছ।',
            style: TextStyle(
                fontFamily: 'Noto Sans Bengali',
                fontSize: 28,
                color: Colors.black)),
        textDirection: TextDirection.ltr)
      ..layout(maxWidth: 900);
    final recorder = ui.PictureRecorder();
    painter.paint(Canvas(recorder), const Offset(4, 4));
    final image = await recorder
        .endRecording()
        .toImage(painter.width.ceil() + 8, painter.height.ceil() + 8);
    final imageData = await image.toByteData(format: ui.ImageByteFormat.png);
    final document = pw.Document()
      ..addPage(pw.MultiPage(
          pageFormat: PdfPageFormat.a4,
          theme: pw.ThemeData.withFont(
              base: latin, bold: latin, fontFallback: [bangla]),
          build: (_) => [
                pw.Text('Cyberbullying Shield - Analysis Report',
                    style: pw.TextStyle(
                        fontSize: 22, fontWeight: pw.FontWeight.bold)),
                pw.SizedBox(height: 12),
                pw.Image(pw.MemoryImage(imageData!.buffer.asUint8List())),
                pw.Text('Cyberbullying detected: 25%'),
              ]));
    final bytes = await document.save();
    expect(bytes.length, greaterThan(1000));
    await File('/tmp/cyberbullying_bangla_test.pdf').writeAsBytes(bytes);
  });
}
