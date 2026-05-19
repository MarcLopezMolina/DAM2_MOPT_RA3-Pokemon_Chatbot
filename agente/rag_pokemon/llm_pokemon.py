from __future__ import annotations

import json
import urllib.error
import urllib.request


OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
OLLAMA_MODEL = "llama3.2:1b"


def generar_respuesta_llm(pregunta: str, contexto: str) -> str:
    pregunta = str(pregunta).strip()
    contexto = str(contexto).strip()

    if not contexto:
        return (
            "No he podido resolver tu consulta con seguridad usando el dataset disponible. "
            "Te paso con un agente humano."
        )

    if "RESPUESTA_CALCULADA:" in contexto:
        return contexto.split("RESPUESTA_CALCULADA:", 1)[1].strip()

    prompt = f"""
Eres un agente experto en Pokémon conectado a un sistema RAG.

REGLAS:
- Responde siempre en español.
- Usa solo la información del contexto.
- No inventes datos.
- Si el contexto contiene datos suficientes, responde de forma clara.
- Si el usuario pide un dato concreto, responde directamente.
- Si el usuario pide una lista, responde en lista.
- Si no puedes responder usando el contexto, responde exactamente:
No he podido resolver tu consulta con seguridad usando el dataset disponible. Te paso con un agente humano.

CONTEXTO:
{contexto}

PREGUNTA:
{pregunta}

RESPUESTA:
""".strip()

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 500,
        },
    }

    try:
        request = urllib.request.Request(
            OLLAMA_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            answer = str(data.get("response", "")).strip()

            if answer:
                return answer

            return respuesta_fallback(contexto)

    except Exception:
        return respuesta_fallback(contexto)


def respuesta_fallback(contexto: str) -> str:
    contexto = str(contexto).strip()

    if "RESPUESTA_CALCULADA:" in contexto:
        return contexto.split("RESPUESTA_CALCULADA:", 1)[1].strip()

    if not contexto:
        return (
            "No he podido resolver tu consulta con seguridad usando el dataset disponible. "
            "Te paso con un agente humano."
        )

    return (
        "No he podido conectar con la IA local, así que respondo usando directamente "
        "los datos recuperados del dataset:\n\n"
        f"{contexto[:2500]}"
    )