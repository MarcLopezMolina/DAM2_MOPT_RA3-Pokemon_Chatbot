from __future__ import annotations

import os

from flask import Flask, jsonify, request

from agente.agente.agente_basico import BasicAgent


def create_agent_app() -> Flask:
    app = Flask(__name__)
    agents: dict[str, BasicAgent] = {}

    def agent_for(student_id: str) -> BasicAgent:
        if student_id not in agents:
            agents[student_id] = BasicAgent()
        return agents[student_id]

    @app.get("/ping")
    def ping():
        return jsonify({"ok": True, "message": "Agente basico activo"})

    @app.post("/message")
    def message():
        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("student_id", "demo")).strip() or "demo"
        text = str(payload.get("message", "")).strip()

        if not text:
            return jsonify({"ok": False, "error": "empty_message", "message": "Falta el mensaje."}), 400

        if text.lower() == "reset":
            agents[student_id] = BasicAgent()
            response = agents[student_id].run("estado")
            return jsonify({"ok": True, **response.to_dict()})

        response = agent_for(student_id).run(text)
        return jsonify({"ok": True, **response.to_dict()})

    return app


app = create_agent_app()


if __name__ == "__main__":
    port = int(os.environ.get("BASIC_AGENT_PORT", "5100"))
    app.run(debug=True, port=port)

