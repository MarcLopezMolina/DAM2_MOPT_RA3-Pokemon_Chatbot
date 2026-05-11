from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from flask import Flask, jsonify, render_template_string, request


BASIC_AGENT_URL = os.environ.get("BASIC_AGENT_URL", "http://127.0.0.1:5100").rstrip("/")
STUDENT_ID = os.environ.get("BASIC_STUDENT_ID", "demo")


HTML = r"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Cliente demo agente basico</title>
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: #f4f7f6;
        color: #172326;
        font-family: Arial, Helvetica, sans-serif;
      }
      main {
        width: min(980px, 100%);
        margin: 0 auto;
        padding: 18px;
        display: grid;
        gap: 12px;
      }
      .panel {
        border: 1px solid #c6d5d1;
        border-radius: 8px;
        padding: 14px;
        background: #ffffff;
      }
      textarea {
        width: 100%;
        min-height: 120px;
        border: 1px solid #c6d5d1;
        border-radius: 6px;
        padding: 10px;
        font-family: Consolas, "Courier New", monospace;
      }
      button {
        min-height: 40px;
        border: 1px solid #0f6b5f;
        border-radius: 6px;
        padding: 8px 12px;
        color: #ffffff;
        background: #0f6b5f;
        cursor: pointer;
      }
      button.secondary {
        color: #0f6b5f;
        background: #ffffff;
      }
      .actions {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 8px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .box {
        border: 1px solid #c6d5d1;
        border-radius: 8px;
        padding: 12px;
        background: #fbfdfc;
      }
      .box strong {
        display: block;
        margin-bottom: 6px;
        color: #084d45;
      }
      pre {
        overflow: auto;
        margin: 0;
        border-radius: 6px;
        padding: 10px;
        color: #edf7f4;
        background: #101719;
      }
      code {
        font-family: Consolas, "Courier New", monospace;
        font-size: 13px;
      }
      @media (max-width: 760px) {
        .grid { grid-template-columns: 1fr; }
      }
    </style>
  </head>
  <body>
    <main>
      <section class="panel">
        <h1>Cliente demo del agente basico</h1>
        <p>Minimo visible: mensaje, intencion, estado y artefacto.</p>
      </section>

      <section class="panel">
        <label for="message"><strong>Mensaje</strong></label>
        <textarea id="message">def saludar(nombre):
    return f"Hola, {nombre}"</textarea>
        <div class="actions">
          <button type="button" id="send">Enviar</button>
          <button type="button" class="secondary" data-message="siguiente">siguiente</button>
          <button type="button" class="secondary" data-message="estado">estado</button>
          <button type="button" class="secondary" data-message="reset">reset</button>
        </div>
      </section>

      <section class="grid">
        <article class="box">
          <strong>Analisis de intencion</strong>
          <p id="intent">Sin mensaje.</p>
        </article>
        <article class="box">
          <strong>Estado</strong>
          <pre><code id="state">Sin estado.</code></pre>
        </article>
        <article class="box">
          <strong>Artefacto</strong>
          <pre><code id="artifact">Sin artefacto.</code></pre>
        </article>
      </section>

      <section class="panel">
        <h2>Respuesta</h2>
        <p id="reply">Esperando interaccion.</p>
      </section>
    </main>

    <script>
      window.APP_CONFIG = {{ config | tojson }};

      const message = document.querySelector("#message");
      const intent = document.querySelector("#intent");
      const state = document.querySelector("#state");
      const artifact = document.querySelector("#artifact");
      const reply = document.querySelector("#reply");

      async function send(text) {
        const payload = {
          student_id: window.APP_CONFIG.student_id,
          message: text.trim()
        };

        if (!payload.message) {
          reply.textContent = "Escribe un mensaje.";
          return;
        }

        const response = await fetch("/api/message", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        });
        const data = await response.json();

        intent.textContent = data.intent || data.error || "unknown";
        state.textContent = JSON.stringify(data.state || null, null, 2);
        artifact.textContent = data.artifact ? JSON.stringify(data.artifact, null, 2) : "Sin artefacto.";
        reply.textContent = data.message || "Sin respuesta.";
      }

      document.querySelector("#send").addEventListener("click", () => send(message.value));
      document.querySelectorAll("[data-message]").forEach((button) => {
        button.addEventListener("click", () => {
          message.value = button.dataset.message;
          send(message.value);
        });
      });
    </script>
  </body>
</html>
"""


def create_client_app() -> Flask:
    app = Flask(__name__)

    @app.get("/")
    def index():
        return render_template_string(
            HTML,
            config={"agent_url": BASIC_AGENT_URL, "student_id": STUDENT_ID},
        )

    @app.route("/api/message", methods=["GET", "POST"])
    def message():
        if request.method == "GET":
            return jsonify(
                {
                    "ok": False,
                    "error": "method_requires_post",
                    "message": (
                        "Este endpoint espera POST con JSON. Abre la interfaz en / "
                        "o envia {'student_id': 'demo', 'message': 'estado'} por POST."
                    ),
                }
            ), 405

        payload = request.get_json(silent=True) or {}
        student_id = str(payload.get("student_id", STUDENT_ID)).strip() or STUDENT_ID
        text = str(payload.get("message", "")).strip()
        response, status = call_agent({"student_id": student_id, "message": text})
        return jsonify(response), status

    return app


def call_agent(payload: dict[str, Any]) -> tuple[dict[str, Any], int]:
    outbound = urllib.request.Request(
        f"{BASIC_AGENT_URL}/message",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(outbound, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), response.status
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            return json.loads(body), exc.code
        except json.JSONDecodeError:
            return {"ok": False, "error": "agent_http_error", "message": body}, exc.code
    except urllib.error.URLError as exc:
        return {
            "ok": False,
            "error": "agent_connection_error",
            "intent": "connection_error",
            "state": None,
            "artifact": None,
            "message": (
                f"No puedo conectar con el agente basico en {BASIC_AGENT_URL}. "
                "Arranca primero: python agente_flask.py"
            ),
        }, 503


app = create_client_app()


if __name__ == "__main__":
    port = int(os.environ.get("BASIC_CLIENT_PORT", "5101"))
    app.run(debug=True, port=port)
