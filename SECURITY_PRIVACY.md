# Cyberbullying Shield - Security and Privacy

## Security architecture

- The Flutter client uses Firebase Authentication and per-user Realtime Database rules.
- The FastAPI service applies an origin allowlist, request-size limits, rate limiting and security response headers.
- The YouTube Data API key is read only from the Render `YOUTUBE_API_KEY` secret. It is never embedded in Flutter or sent by the browser.
- Harmful detections can be sealed in the Evidence Vault with a SHA-256 integrity fingerprint.
- Security actions are recorded in an append-only audit trail. A user can erase the entire trail to exercise their privacy rights.
- Administrative access is limited by Firebase role rules and the configured administrator identity.

## Privacy and consent

Users must accept the data-processing notice before registration. The Privacy Center lets a signed-in user:

- choose a 30-day, 90-day, or 365-day retention period;
- export all stored personal data as JSON;
- permanently erase analyses, evidence, audit records, notifications, blocked-user entries, and privacy settings.

The default retention period is 90 days. This project should not ingest private conversations without permission. Reports and training exports should be anonymized before research use.

## Threat model

Primary risks include stolen API keys, unauthorized database access, abusive request flooding, altered evidence, exposed personal text, and incorrect automated moderation. Current controls reduce these risks, but production use still requires independent penetration testing, secret rotation, server-side Firebase token verification, and human review for consequential decisions.

## Incident response

1. Revoke or rotate any exposed API key immediately.
2. Review Render and Firebase logs.
3. Preserve relevant evidence hashes and timestamps.
4. Notify affected users when legally required.
5. Patch, test and document the root cause before redeployment.
