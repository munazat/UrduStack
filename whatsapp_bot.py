"""
WhatsApp bot for checking Roman-Urdu job scams.

Forward a suspicious job ad from WhatsApp and get an instant verdict:
risk score, threat type, flagged phrases, and specific advice.

Setup (Twilio free sandbox — no paid account needed):
  1. Go to https://console.twilio.com → Messaging → Try it out →
     Send a WhatsApp message → Join the sandbox.
  2. Scan the QR code with your phone to join.
  3. Set the webhook URL for incoming messages to your server:
     https://<your-server>/whatsapp/webhook
  4. Set environment variables:
     TWILIO_AUTH_TOKEN  — from your Twilio console
  5. Run:
     python whatsapp_bot.py

The bot runs on port 5000. Use ngrok (ngrok http 5000) or Colab to
expose it to Twilio's webhook.
"""

import os

from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

from app.utils.risk import compute_risk_score, categorize_risk

app = Flask(__name__)

_TWILIO_FROM = os.getenv("TWILIO_FROM", "whatsapp:+14155238886")
_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")

if _AUTH_TOKEN:
    app.config["TWILIO_AUTH_TOKEN"] = _AUTH_TOKEN


def _format_verdict(text: str) -> str:
    """Run UrduStack pipeline and format a WhatsApp-friendly verdict."""
    score, confidence, risk_level, flagged, explanation = compute_risk_score(text)
    cat_result = categorize_risk(flagged)

    cat_labels = {
        "job_scam": "Fake Job Posting",
        "phishing": "Phishing",
        "harassment": "Harassment/Abuse",
    }

    if score >= 0.7:
        header = "SCAM DETECTED"
    elif score >= 0.4:
        header = "SOME RISK"
    else:
        header = "LOOKS SAFE"

    lines = [f"*{header}* (score: {score:.2f})"]

    if cat_result["categories"]:
        types = ", ".join(cat_labels.get(c, c) for c in cat_result["categories"])
        lines.append(f"Type: {types}")

    if flagged:
        phrase_list = ", ".join(f'"{p["phrase"]}"' for p in flagged[:3])
        lines.append(f"Flagged: {phrase_list}")

    if cat_result.get("advice"):
        lines.append(f"\n{cat_result['advice']}")
    elif risk_level == "low":
        lines.append("No significant risk indicators found.")

    return "\n".join(lines)


@app.route("/whatsapp/webhook", methods=["POST"])
def whatsapp_webhook():
    """Handle incoming WhatsApp messages via Twilio."""
    incoming = request.values.get("Body", "").strip()
    resp = MessagingResponse()

    if not incoming:
        resp.message("Forward a suspicious job ad or message here to check it.")
        return str(resp)

    if incoming.lower() in ("help", "hi", "hello", "start"):
        resp.message(
            "*UrduStack Job Scam Checker*\n\n"
            "Forward any suspicious job posting, WhatsApp message, "
            "or text here. I'll tell you if it's a scam, what type, "
            "and what to do.\n\n"
            "Works with English, Roman Urdu, and mixed text."
        )
        return str(resp)

    try:
        verdict = _format_verdict(incoming)
        resp.message(verdict)
    except Exception as exc:
        resp.message(f"Sorry, something went wrong: {exc}")

    return str(resp)


@app.route("/health")
def health():
    return {"status": "ok", "bot": "whatsapp"}


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"WhatsApp bot running on port {port}")
    print(f"Set Twilio webhook URL to: https://<your-server>/whatsapp/webhook")
    app.run(host="0.0.0.0", port=port)
