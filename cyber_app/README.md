# Cyberbullying Shield

Final-year project mobile/web client for ML-assisted cyberbullying detection.

Production API: `https://cyberbullying-shield-api.onrender.com`

## Implemented features

- Firebase email/password authentication and password reset
- FastAPI connection to the trained TF-IDF + Logistic Regression model
- Prediction confidence and supplementary Bangla/Banglish keyword flags
- Persistent analysis history in Firebase Realtime Database
- Dashboard totals and recent activity
- Report and block-user workflow
- In-app persistent notifications
- Admin report review (confirm/dismiss)
- YouTube comment scanning
- Optional automatic removal for a channel owner using a short-lived OAuth token

## Run locally

Start the API from the repository root:

```bash
./.venv/bin/python3 -m uvicorn api:app --reload --host 127.0.0.1 --port 8000
```

Start Flutter from `cyber_app` (replace the admin email when needed):

```bash
flutter run -d chrome --dart-define=API_URL=http://127.0.0.1:8000 --dart-define=ADMIN_EMAIL=smriazul2002@gmail.com
```

For Android Emulator use `http://10.0.2.2:8000` as `API_URL`. A physical phone must use the computer's LAN address and the API must bind to `0.0.0.0`.

## Database security rules

Review `database.rules.json`, then deploy it to the configured Firebase project:

```bash
firebase deploy --only database --config firebase.database.json --project cyberbullyinapp-d427c
```

## YouTube protection

Scanning needs a YouTube Data API v3 key. Automatic deletion additionally needs a short-lived OAuth access token belonging to the channel owner with the `youtube.force-ssl` scope. The app sends the token to the local API for the deletion request and does not persist it.

## Known limitation

The TF-IDF model has limited contextual understanding and may flag non-personal or negated uses of toxic vocabulary. Automatic moderation should be reviewed by a human before production use.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Learn Flutter](https://docs.flutter.dev/get-started/learn-flutter)
- [Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Flutter learning resources](https://docs.flutter.dev/reference/learning-resources)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
