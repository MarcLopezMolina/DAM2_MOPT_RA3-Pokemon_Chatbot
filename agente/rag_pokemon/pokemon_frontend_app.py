from __future__ import annotations

import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path

import pandas as pd
from flask import Flask, jsonify, render_template_string, request


BASE_DIR = Path(__file__).resolve().parent

# Esto permite que el frontend funcione tanto si está en la raíz del proyecto
# como si lo has metido dentro de la carpeta rag_pokemon.
if (BASE_DIR / "agente_pokemon.py").exists():
    RAG_DIR = BASE_DIR
else:
    RAG_DIR = BASE_DIR / "rag_pokemon"

DATA_PATH = RAG_DIR / "data" / "dataSetFinal.xlsx"

if str(RAG_DIR) not in sys.path:
    sys.path.append(str(RAG_DIR))

from agente_pokemon import PokemonAgent  # noqa: E402


HTML_TEMPLATE = r"""
<!doctype html>
<html lang="es">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Agente Pokémon con IA + RAG</title>
    <style>
      :root {
        --bg: #f5f7f8;
        --surface: #ffffff;
        --ink: #152025;
        --muted: #61717a;
        --line: #ccd6dc;
        --accent: #e3350d;
        --accent-dark: #b82b0b;
        --soft: #fff1ed;
        --code-bg: #101719;
        --code-ink: #eef7f4;
      }

      * {
        box-sizing: border-box;
      }

      body {
        margin: 0;
        color: var(--ink);
        background: var(--bg);
        font-family: Arial, Helvetica, sans-serif;
      }

      button,
      input {
        font: inherit;
      }

      main {
        width: min(1180px, 100%);
        min-height: 100vh;
        margin: 0 auto;
        padding: 18px;
      }

      h1,
      h2,
      p {
        margin-top: 0;
      }

      h1 {
        margin-bottom: 6px;
        font-size: 30px;
        line-height: 1.15;
      }

      h2 {
        margin-bottom: 10px;
        font-size: 20px;
      }

      p {
        line-height: 1.45;
      }

      .panel,
      .agent-card,
      .answer-box,
      .media-box {
        border: 1px solid var(--line);
        border-radius: 10px;
        background: var(--surface);
      }

      .panel {
        padding: 16px;
      }

      .intro {
        margin-bottom: 14px;
      }

      .intro p {
        margin-bottom: 0;
        color: var(--muted);
      }

      .input-row {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 10px;
        margin-bottom: 14px;
      }

      input {
        width: 100%;
        min-height: 44px;
        border: 1px solid var(--line);
        border-radius: 8px;
        padding: 8px 12px;
      }

      button {
        min-height: 44px;
        border: 1px solid var(--accent);
        border-radius: 8px;
        padding: 8px 14px;
        color: #ffffff;
        background: var(--accent);
        cursor: pointer;
      }

      button:hover {
        background: var(--accent-dark);
      }

      button.secondary {
        color: var(--accent);
        background: #ffffff;
      }

      button.secondary:hover {
        background: var(--soft);
      }

      .examples,
      .agent-grid,
      .image-grid {
        display: grid;
        gap: 12px;
      }

      .examples {
        grid-template-columns: repeat(4, minmax(0, 1fr));
        margin-bottom: 14px;
      }

      .agent-grid {
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin-bottom: 14px;
      }

      .image-grid {
        grid-template-columns: repeat(4, minmax(0, 1fr));
      }

      .agent-card {
        min-height: 145px;
        padding: 14px;
      }

      .agent-card.active {
        border-color: var(--accent);
        box-shadow: 0 0 0 3px rgba(227, 53, 13, 0.14);
      }

      .agent-card strong {
        display: block;
        margin-bottom: 8px;
        color: var(--accent-dark);
      }

      .agent-card p {
        margin-bottom: 0;
        color: var(--muted);
      }

      .answer-box,
      .media-box {
        padding: 16px;
        margin-bottom: 14px;
        background: #fffdfc;
      }

      .answer-box strong,
      .media-box strong {
        display: block;
        margin-bottom: 8px;
        color: var(--accent-dark);
      }

      #reply {
        white-space: pre-wrap;
        margin-bottom: 0;
      }

      .image-card {
        border: 1px solid var(--line);
        border-radius: 10px;
        padding: 12px;
        background: #fff;
      }

      .image-card h3 {
        margin: 0 0 10px;
        font-size: 17px;
      }

      .image-card p {
        margin: 6px 0 0;
        color: var(--muted);
        font-size: 14px;
      }

      .image-main {
        width: 100%;
        aspect-ratio: 1 / 1;
        object-fit: contain;
        border-radius: 8px;
        background: #f7f7f7;
        border: 1px solid #ececec;
      }

      .image-sprite {
        width: 72px;
        height: 72px;
        object-fit: contain;
        margin-top: 10px;
        border-radius: 8px;
        background: #f7f7f7;
        border: 1px solid #ececec;
      }

      .empty-media {
        color: var(--muted);
      }

      pre {
        overflow: auto;
        max-height: 360px;
        margin: 14px 0 0;
        border-radius: 8px;
        padding: 12px;
        color: var(--code-ink);
        background: var(--code-bg);
      }

      code {
        font-family: Consolas, "Courier New", monospace;
        font-size: 13px;
        line-height: 1.5;
      }

      .loading {
        opacity: 0.65;
      }

      @media (max-width: 980px) {
        .examples,
        .agent-grid,
        .image-grid {
          grid-template-columns: repeat(2, minmax(0, 1fr));
        }
      }

      @media (max-width: 760px) {
        .input-row,
        .examples,
        .agent-grid,
        .image-grid {
          grid-template-columns: 1fr;
        }
      }
    </style>
  </head>

  <body>
    <main>
      <section class="panel intro">
        <h1>Agente Pokémon con IA + RAG</h1>
        <p>
          Este agente analiza la intención, consulta el dataset Pokémon y además
          muestra imágenes de los Pokémon detectados en la consulta.
        </p>
      </section>

      <section class="panel">
        <div class="input-row">
          <input id="message-input" value="quien gana entre Charmander y Squirtle" aria-label="Pregunta Pokémon">
          <button type="button" id="send-button">Preguntar</button>
        </div>

        <div class="examples">
          <button type="button" class="secondary" data-message="cuanto pesa pikachu">Peso</button>
          <button type="button" class="secondary" data-message="cual es el pokemon 385">Pokémon por ID</button>
          <button type="button" class="secondary" data-message="cual es la estadistica más alta de Rhyperior">Estadística</button>
          <button type="button" class="secondary" data-message="compara Pikachu y Charizard">Comparar</button>
          <button type="button" class="secondary" data-message="quien gana entre Charmander y Squirtle">Batalla</button>
          <button type="button" class="secondary" data-message="dime pokemon de tipo dragon">Tipo</button>
          <button type="button" class="secondary" data-message="dime datos de Charmander">Datos</button>
          <button type="button" class="secondary" data-message="mi cuenta se ha borrado">Escalado</button>
        </div>

        <section class="agent-grid">
          <article class="agent-card" id="general-agent">
            <strong>Agente general</strong>
            <p id="general-copy">Responde preguntas generales sobre Pokémon.</p>
          </article>

          <article class="agent-card" id="rag-agent">
            <strong>Agente RAG / Dataset</strong>
            <p id="rag-copy">Consulta FAISS y el Excel cuando hacen falta datos concretos.</p>
          </article>

          <article class="agent-card" id="human-agent">
            <strong>Escalado humano</strong>
            <p id="human-copy">Solo se activa cuando el sistema no puede responder con seguridad.</p>
          </article>
        </section>

        <section class="answer-box">
          <strong>Respuesta del agente</strong>
          <p id="reply">Esperando pregunta.</p>
        </section>

        <section class="media-box">
          <strong>Imágenes detectadas</strong>
          <div id="image-grid" class="image-grid"></div>
          <p id="empty-media" class="empty-media">Todavía no hay imágenes.</p>
        </section>

        <pre><code id="result-json">{}</code></pre>
      </section>
    </main>

    <script>
      const input = document.querySelector("#message-input");
      const sendButton = document.querySelector("#send-button");

      const generalAgent = document.querySelector("#general-agent");
      const ragAgent = document.querySelector("#rag-agent");
      const humanAgent = document.querySelector("#human-agent");

      const generalCopy = document.querySelector("#general-copy");
      const ragCopy = document.querySelector("#rag-copy");
      const humanCopy = document.querySelector("#human-copy");

      const reply = document.querySelector("#reply");
      const resultJson = document.querySelector("#result-json");
      const imageGrid = document.querySelector("#image-grid");
      const emptyMedia = document.querySelector("#empty-media");

      async function send(message = input.value) {
        const cleanMessage = message.trim();

        if (!cleanMessage) {
          reply.textContent = "Escribe una pregunta.";
          return;
        }

        document.body.classList.add("loading");

        try {
          const response = await fetch("/api/pokemon", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message: cleanMessage })
          });

          const result = await response.json();
          render(result);
        } catch (error) {
          render({
            ok: false,
            error: "frontend_error",
            message: "No se ha podido conectar con el backend.",
            detail: String(error),
            images: []
          });
        } finally {
          document.body.classList.remove("loading");
        }
      }

      function render(result) {
        const intent = result.intent || "unknown";
        const usedRag = result.state && result.state.used_rag;
        const isEscalated = result.escalated === true;

        generalAgent.classList.toggle("active", intent === "general_question");
        ragAgent.classList.toggle("active", usedRag && !isEscalated);
        humanAgent.classList.toggle("active", isEscalated);

        generalCopy.textContent =
          intent === "general_question"
            ? "El agente ha respondido directamente."
            : "No se usa para esta consulta.";

        ragCopy.textContent =
          usedRag && !isEscalated
            ? "El agente ha usado el pipeline RAG y el dataset."
            : "No se usa o no ha sido suficiente.";

        humanCopy.textContent =
          isEscalated
            ? "La consulta se ha escalado a humano."
            : "No ha sido necesario escalar.";

        reply.textContent = result.message || result.error || "Sin respuesta.";
        resultJson.textContent = JSON.stringify(result, null, 2);

        renderImages(result.images || []);
      }

      function renderImages(images) {
        imageGrid.innerHTML = "";

        if (!images.length) {
          emptyMedia.style.display = "block";
          return;
        }

        emptyMedia.style.display = "none";

        images.forEach((item) => {
          const card = document.createElement("article");
          card.className = "image-card";

          const title = document.createElement("h3");
          title.textContent = item.name || "Pokémon";

          const artwork = document.createElement("img");
          artwork.className = "image-main";
          artwork.src = item.official_artwork || item.sprite || "";
          artwork.alt = item.name || "Pokémon";

          const sprite = document.createElement("img");
          sprite.className = "image-sprite";
          sprite.src = item.sprite || item.official_artwork || "";
          sprite.alt = item.name || "Sprite Pokémon";

          const meta = document.createElement("p");
          const idText = item.id ? `#${item.id}` : "Sin ID";
          const types = item.types && item.types.length ? item.types.join(", ") : "Tipo no disponible";
          meta.textContent = `${idText} · ${types}`;

          card.appendChild(title);
          card.appendChild(artwork);

          if (item.sprite || item.official_artwork) {
            card.appendChild(sprite);
          }

          card.appendChild(meta);
          imageGrid.appendChild(card);
        });
      }

      sendButton.addEventListener("click", () => send());

      input.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          send();
        }
      });

      document.querySelectorAll("[data-message]").forEach((button) => {
        button.addEventListener("click", () => {
          input.value = button.dataset.message || "";
          send(input.value);
        });
      });

      send();
    </script>
  </body>
</html>
"""


def normalize_text(text: str) -> str:
    text = str(text).lower().strip()
    text = unicodedata.normalize("NFD", text)
    text = "".join(char for char in text if unicodedata.category(char) != "Mn")
    text = text.replace("_", " ")
    text = text.replace("-", " ")
    text = text.replace("(", " ")
    text = text.replace(")", " ")
    text = text.replace(".", " ")
    text = " ".join(text.split())
    return text


@lru_cache(maxsize=1)
def load_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el dataset en: {DATA_PATH}")

    df = pd.read_excel(DATA_PATH)
    df.columns = [str(col).strip() for col in df.columns]
    return df


def get_name_column(df: pd.DataFrame) -> str | None:
    for col in ["Name", "Nombre", "name", "nombre"]:
        if col in df.columns:
            return col
    return None


def get_id_column(df: pd.DataFrame) -> str | None:
    possible = ["id", "ID", "#", "Number", "Número", "numero", "Pokedex Number"]
    normalized_map = {normalize_text(col): col for col in df.columns}

    for col in possible:
        key = normalize_text(col)
        if key in normalized_map:
            return normalized_map[key]

    return None


def detect_pokemon_names(message: str) -> list[str]:
    df = load_dataset()
    name_col = get_name_column(df)

    if name_col is None:
        return []

    text = normalize_text(message)
    names = df[name_col].dropna().astype(str).tolist()
    names = sorted(names, key=len, reverse=True)

    found: list[str] = []
    seen: set[str] = set()

    for name in names:
        normalized_name = normalize_text(name)
        if normalized_name in text and normalized_name not in seen:
            found.append(name)
            seen.add(normalized_name)

    return found


def detect_pokemon_id(message: str) -> int | None:
    normalized = normalize_text(message)

    patterns = [
        r"\bpokemon\s+(\d+)\b",
        r"\bpokemon\s*#\s*(\d+)\b",
        r"\bid\s+(\d+)\b",
        r"\bnumero\s+(\d+)\b",
        r"\bnúmero\s+(\d+)\b",
        r"\b#\s*(\d+)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return int(match.group(1))

    return None


def get_row_by_name(name: str) -> pd.Series | None:
    df = load_dataset()
    name_col = get_name_column(df)

    if name_col is None:
        return None

    target = normalize_text(name)

    for _, row in df.iterrows():
        if normalize_text(row.get(name_col, "")) == target:
            return row

    return None


def get_row_by_id(pokemon_id: int) -> pd.Series | None:
    df = load_dataset()
    id_col = get_id_column(df)

    if id_col is None:
        return None

    ids = pd.to_numeric(df[id_col], errors="coerce")
    result = df[ids == pokemon_id]

    if result.empty:
        return None

    return result.iloc[0]


def extract_names_from_text(text: str, limit: int = 6) -> list[str]:
    df = load_dataset()
    name_col = get_name_column(df)

    if name_col is None:
        return []

    normalized_text = normalize_text(text)
    names = df[name_col].dropna().astype(str).tolist()
    names = sorted(names, key=len, reverse=True)

    found: list[str] = []
    seen: set[str] = set()

    for name in names:
        normalized_name = normalize_text(name)
        if normalized_name in normalized_text and normalized_name not in seen:
            found.append(name)
            seen.add(normalized_name)

        if len(found) >= limit:
            break

    return found


def build_pokemon_references(user_message: str, agent_message: str) -> list[dict]:
    references: list[dict] = []
    seen_keys: set[str] = set()

    explicit_names = detect_pokemon_names(user_message)
    explicit_id = detect_pokemon_id(user_message)

    for name in explicit_names:
        row = get_row_by_name(name)
        if row is None:
            continue

        pokemon_id = get_pokemon_id_from_row(row)
        reference = {
            "name": get_pokemon_name_from_row(row),
            "id": pokemon_id,
            "types": get_pokemon_types_from_row(row),
        }

        key = f"name:{normalize_text(reference['name'])}"
        if key not in seen_keys:
            references.append(reference)
            seen_keys.add(key)

    if explicit_id is not None:
        row = get_row_by_id(explicit_id)
        if row is not None:
            reference = {
            "name": get_pokemon_name_from_row(row),
            "id": get_pokemon_id_from_row(row),
            "types": get_pokemon_types_from_row(row),
        }
            key = f"id:{reference['id']}"
            if key not in seen_keys:
                references.append(reference)
                seen_keys.add(key)

    if not references:
        fallback_names = extract_names_from_text(agent_message, limit=6)

        for name in fallback_names:
            row = get_row_by_name(name)
            if row is None:
                continue

            reference = {
            "name": get_pokemon_name_from_row(row),
            "id": get_pokemon_id_from_row(row),
            "types": get_pokemon_types_from_row(row),
        }

            key = f"name:{normalize_text(reference['name'])}"
            if key not in seen_keys:
                references.append(reference)
                seen_keys.add(key)

    return references


def get_pokemon_name_from_row(row: pd.Series) -> str:
    for col in ["Name", "Nombre", "name", "nombre"]:
        if col in row.index:
            return str(row.get(col, "")).strip()
    return ""


def get_pokemon_id_from_row(row: pd.Series) -> int | None:
    for col in ["id", "ID", "#", "Number", "Número", "numero", "Pokedex Number"]:
        if col in row.index:
            try:
                return int(float(row.get(col)))
            except (TypeError, ValueError):
                return None
    return None

def get_pokemon_types_from_row(row: pd.Series) -> list[str]:
    types = []

    for col in ["Type_1", "Type 1", "Tipo 1"]:
        if col in row.index and not pd.isna(row.get(col)):
            value = str(row.get(col)).strip()
            if value and value.lower() != "nan":
                types.append(value)
            break

    for col in ["Type_2", "Type 2", "Tipo 2"]:
        if col in row.index and not pd.isna(row.get(col)):
            value = str(row.get(col)).strip()
            if value and value.lower() != "nan":
                types.append(value)
            break

    return types


@lru_cache(maxsize=256)
def fetch_pokemon_media(identifier: str) -> dict:
    url = f"https://pokeapi.co/api/v2/pokemon/{identifier.lower()}"

    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return {
            "name": str(identifier).title(),
            "id": None,
            "sprite": None,
            "official_artwork": None,
            "types": [],
        }

    sprite = data.get("sprites", {}).get("front_default")
    other = data.get("sprites", {}).get("other", {})
    official_artwork = other.get("official-artwork", {}).get("front_default")
    home_artwork = other.get("home", {}).get("front_default")

    types = []
    for item in data.get("types", []):
        type_name = item.get("type", {}).get("name")
        if type_name:
            types.append(type_name.title())

    return {
        "name": str(data.get("name", identifier)).title(),
        "id": data.get("id"),
        "sprite": sprite,
        "official_artwork": official_artwork or home_artwork,
        "types": types,
    }


def build_images_payload(user_message: str, agent_message: str) -> list[dict]:
    references = build_pokemon_references(user_message, agent_message)
    images: list[dict] = []

    for ref in references:
        identifier = str(ref["id"]) if ref.get("id") is not None else str(ref["name"])
        media = fetch_pokemon_media(identifier)

        if not media.get("official_artwork") and ref.get("id") is not None:
            pokemon_id = ref["id"]
            media["official_artwork"] = (
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                f"sprites/pokemon/other/official-artwork/{pokemon_id}.png"
            )
            media["sprite"] = media.get("sprite") or (
                "https://raw.githubusercontent.com/PokeAPI/sprites/master/"
                f"sprites/pokemon/{pokemon_id}.png"
            )

        media["name"] = ref.get("name") or media.get("name") or "Pokémon"
        media["id"] = ref.get("id") or media.get("id")
        media["types"] = ref.get("types") or media.get("types") or []

        images.append(media)

    return images


def create_pokemon_frontend_app() -> Flask:
    app = Flask(__name__)
    agent = PokemonAgent()

    @app.get("/")
    def index():
        return render_template_string(HTML_TEMPLATE)

    @app.post("/api/pokemon")
    def ask_pokemon():
        try:
            payload = request.get_json(silent=True) or {}
            message = str(payload.get("message", "")).strip()

            if not message:
                return jsonify(
                    {
                        "ok": False,
                        "error": "empty_message",
                        "message": "Falta la pregunta.",
                        "images": [],
                    }
                ), 400

            response = agent.run(message)
            data = response.to_dict()

            data["ok"] = True
            data["escalated"] = "te paso con un agente humano" in response.message.lower()
            data["images"] = build_images_payload(message, response.message)
            data["image_count"] = len(data["images"])

            return jsonify(data)

        except Exception as exc:
            return jsonify(
                {
                    "ok": False,
                    "error": "backend_exception",
                    "message": "Ha ocurrido un error dentro del backend.",
                    "detail": str(exc),
                    "images": [],
                }
            ), 500

    return app


app = create_pokemon_frontend_app()


if __name__ == "__main__":
    port = int(os.environ.get("POKEMON_FRONTEND_PORT", "5058"))
    app.run(debug=True, port=port)