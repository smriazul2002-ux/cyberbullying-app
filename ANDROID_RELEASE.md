# Android release guide

The Android application name is **Cyberbullying Shield**. The current Firebase package remains `com.example.cyber_app`; changing it requires registering a new Android app in Firebase and downloading a matching `google-services.json`.

## Create a private upload key

```bash
keytool -genkeypair -v -keystore upload-keystore.jks -keyalg RSA -keysize 2048 -validity 10000 -alias upload
cp key.properties.example key.properties
```

Update `key.properties` with the real passwords. Never commit `key.properties` or the keystore.

## Build

```bash
flutter build appbundle --release \
  --dart-define=API_URL=https://cyberbullying-shield-api.onrender.com \
  --dart-define=ADMIN_EMAIL=smriazul2002@gmail.com
```

The Play Store artifact is generated at `build/app/outputs/bundle/release/app-release.aab`. Google Play publishing requires a Play Console developer account, privacy-policy URL, screenshots, content rating and Data Safety form.
