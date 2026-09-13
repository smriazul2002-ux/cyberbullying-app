# Research documentation and demo plan

## Research objective

Evaluate whether a hybrid word/character TF-IDF model with explainable safety rules can detect English, Bangla and Banglish cyberbullying while supporting accountable human review.

## Methodology

Record dataset provenance, consent, anonymization, class balance and label guidelines. Split data by source or author to reduce leakage. Report accuracy, precision, recall and F1, plus language- and category-specific confusion matrices. Freeze a holdout set before training and promote a model only when predefined safety metrics improve.

## Required limitations statement

The classifier can misunderstand context, sarcasm, reclaimed language and cultural nuance. Confidence is not certainty. The system must assist—not replace—trained human moderation, especially for threats, self-harm, account sanctions or legal decisions.

## Demo video script (4-5 minutes)

1. Explain the cyberbullying problem and project goal.
2. Sign in and analyze one safe, one insulting and one critical-threat example.
3. Add conversation context and show category, risk, reasons and model version.
4. Scan a YouTube video while explaining that the API key stays on the server.
5. Confirm/ignore an item in Review Queue and show Model Evaluation.
6. Show Evidence Vault, Audit Log and Security Center.
7. Open Privacy Center, change retention, export data and explain deletion.
8. Finish with evaluation metrics, limitations and future verified-dataset work.

Do not display API keys, OAuth tokens, email addresses or private comments while recording.
