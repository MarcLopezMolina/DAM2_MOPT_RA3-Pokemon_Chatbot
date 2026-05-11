from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
INDEX_PATH = VECTORSTORE_DIR / "pokemon.index"
CHUNKS_PATH = VECTORSTORE_DIR / "chunks.txt"


class PokemonFAISSRAG:
    def __init__(self) -> None:
        if not INDEX_PATH.exists():
            raise FileNotFoundError(
                f"No existe el índice FAISS en: {INDEX_PATH}. "
                "Ejecuta primero crear_faiss.py"
            )

        if not CHUNKS_PATH.exists():
            raise FileNotFoundError(
                f"No existe el archivo de chunks en: {CHUNKS_PATH}. "
                "Ejecuta primero crear_faiss.py"
            )

        self.modelo = SentenceTransformer("all-MiniLM-L6-v2")
        self.index = faiss.read_index(str(INDEX_PATH))
        self.chunks = self.cargar_chunks()

    def cargar_chunks(self) -> list[str]:
        with open(CHUNKS_PATH, "r", encoding="utf-8") as file:
            contenido = file.read()

        chunks = contenido.split("\n---CHUNK---\n")
        chunks = [chunk.replace("\\n", "\n").strip() for chunk in chunks if chunk.strip()]

        return chunks

    def recuperar_chunks(self, pregunta: str, k: int = 3) -> list[str]:
        embedding = self.modelo.encode([pregunta], convert_to_numpy=True)
        embedding = np.array(embedding).astype("float32")

        distancias, indices = self.index.search(embedding, k)

        resultados = []

        for indice in indices[0]:
            if 0 <= indice < len(self.chunks):
                resultados.append(self.chunks[indice])

        return resultados


def recuperar_chunks(pregunta: str, k: int = 3) -> list[str]:
    rag = PokemonFAISSRAG()
    return rag.recuperar_chunks(pregunta, k=k)


def main() -> None:
    rag = PokemonFAISSRAG()

    print("RAG FAISS Pokémon activo. Escribe una pregunta o 'salir'.")

    while True:
        pregunta = input("\nPregunta> ").strip()

        if pregunta.lower() == "salir":
            break

        chunks = rag.recuperar_chunks(pregunta)

        print("\nChunks recuperados:")

        for i, chunk in enumerate(chunks, start=1):
            print(f"\n--- Chunk {i} ---")
            print(chunk)


if __name__ == "__main__":
    main()