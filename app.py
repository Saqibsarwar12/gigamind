from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

GIGAMIND_URL = "https://ai.gigamind.dev/claude-code/v1/messages"
GIGAMIND_KEY = os.getenv("GIGAMIND_KEY", "")
PROXY_KEY = os.getenv("PROXY_KEY", "")

@app.get("/")
def home():
    return jsonify({
        "ok": True,
        "service": "gigamind-render-proxy",
        "endpoint": "/v1/chat/completions"
    })

@app.post("/v1/chat/completions")
def chat_completions():
    auth = request.headers.get("Authorization", "")
    if auth != f"Bearer {PROXY_KEY}":
        return jsonify({"error": {"message": "Unauthorized"}}), 401

    data = request.get_json(force=True, silent=True) or {}

    model = data.get("model", "claude-3.5-sonnet")
    messages = data.get("messages", [])
    max_tokens = data.get("max_tokens", 512)

    gigamind_payload = {
        "model": model,
        "messages": messages,
        "max_tokens_to_sample": max_tokens
    }

    headers = {
        "Content-Type": "application/json",
        "x-api-key": GIGAMIND_KEY
    }

    try:
        resp = requests.post(
            GIGAMIND_URL,
            json=gigamind_payload,
            headers=headers,
            timeout=60
        )
    except Exception as e:
        return jsonify({"error": {"message": f"Upstream request failed: {str(e)}"}}), 502

    try:
        raw = resp.json()
    except Exception:
        return jsonify({
            "error": {
                "message": "Upstream returned non-JSON response",
                "status_code": resp.status_code,
                "text": resp.text[:1000]
            }
        }), 502

    if resp.status_code != 200:
        return jsonify(raw), resp.status_code

    text = ""
    if isinstance(raw.get("content"), list):
        for item in raw["content"]:
            if item.get("type") == "text":
                text += item.get("text", "")

    return jsonify({
        "id": raw.get("id", "gigamind-chatcmpl"),
        "object": "chat.completion",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": raw.get("usage", {})
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
