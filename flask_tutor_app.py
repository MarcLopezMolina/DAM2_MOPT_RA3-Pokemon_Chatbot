from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from flask import Flask, jsonify, render_template, request


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENT_BASE_URL = os.environ.get("AGENT_BASE_URL", "http://127.0.0.1:5000/agent").rstrip("/")
TUTOR_USER_ID = os.environ.get("TUTOR_USER_ID", "joan")


def create_tutor_app() -> Flask:
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, "flask_tutor", "templates"),
        static_folder=os.path.join(BASE_DIR, "flask_tutor", "static"),
        static_url_path="/tutor-static",
    )

    @app.get("/")
    def index():
        return render_template(
            "flask_tutor.html",
            agent_base_url=AGENT_BASE_URL,
            user_id=TUTOR_USER_ID,
            asset_version=asset_version(),
        )

    @app.post("/api/message")
    def message():
        payload = request.get_json(silent=True) or {}
        text = str(payload.get("message", "")).strip()
        user_id = str(payload.get("user_id", TUTOR_USER_ID)).strip() or TUTOR_USER_ID

        if not text:
            return jsonify(
                {
                    "ok": False,
                    "reply": "Escribe una accion antes de continuar.",
                    "error": "empty_message",
                }
            ), 400

        response, status = call_agent("/chat", {"user_id": user_id, "message": text})
        return jsonify(response), status

    @app.get("/api/llm/status")
    def llm_status():
        response, status = call_agent_get("/llm/status")
        return jsonify(response), status

    @app.get("/api/config")
    def config():
        return jsonify(
            {
                "agent_base_url": AGENT_BASE_URL,
                "user_id": TUTOR_USER_ID,
                "mode": "guided_tutor",
            }
        )

    return app


def asset_version() -> int:
    static_dir = os.path.join(BASE_DIR, "flask_tutor", "static")
    asset_paths = [
        os.path.join(static_dir, "flask_tutor.css"),
        os.path.join(static_dir, "flask_tutor.js"),
    ]
    return int(max(os.path.getmtime(path) for path in asset_paths))


def call_agent(path: str, payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    outbound = urllib.request.Request(
        f"{AGENT_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    return open_agent_request(outbound)


def call_agent_get(path: str) -> tuple[dict[str, Any], int]:
    outbound = urllib.request.Request(f"{AGENT_BASE_URL}{path}", method="GET")
    return open_agent_request(outbound)


def open_agent_request(outbound: urllib.request.Request) -> tuple[dict[str, Any], int]:
    try:
        with urllib.request.urlopen(outbound, timeout=120) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body), exc.code
        except json.JSONDecodeError:
            return {"ok": False, "reply": body, "error": "agent_http_error"}, exc.code
    except urllib.error.URLError as exc:
        return (
            {
                "ok": False,
                "reply": f"No puedo conectar con el agente en {AGENT_BASE_URL}: {exc.reason}",
                "error": "agent_connection_error",
            },
            503,
        )
    except TimeoutError:
        return (
            {
                "ok": False,
                "reply": "La peticion al agente ha agotado el tiempo de espera.",
                "error": "agent_timeout",
            },
            504,
        )


app = create_tutor_app()


if __name__ == "__main__":
    port = int(os.environ.get("TUTOR_PORT", "5051"))
    app.run(debug=True, port=port)
