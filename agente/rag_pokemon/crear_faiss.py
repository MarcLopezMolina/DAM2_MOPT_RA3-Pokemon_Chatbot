from __future__ import annotations

from pathlib import Path

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dataSetFinal.xlsx"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
INDEX_PATH = VECTORSTORE_DIR / "pokemon.index"
CHUNKS_PATH = VECTORSTORE_DIR / "chunks.txt"


def fila_a_chunk(row: pd.Series) -> str:
    lineas = []

    for columna, valor in row.items():
        if pd.isna(valor):
            valor = ""

        lineas.append(f"{columna}: {valor}")

    return "\n".join(lineas)


def crear_indice_faiss() -> None:
    VECTORSTORE_DIR.mkdir(exist_ok=True)

    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No se ha encontrado el Excel en: {DATA_PATH}")

    df = pd.read_excel(DATA_PATH)
    df.columns = [str(columna).strip() for columna in df.columns]

    chunks = []

    for _, row in df.iterrows():
        chunk = fila_a_chunk(row)
        chunks.append(chunk)

    print("Generando embeddings. Puede tardar un poco...")

    modelo = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = modelo.encode(chunks, convert_to_numpy=True)

    embeddings = np.array(embeddings).astype("float32")

    dimension = embeddings.shape[1]
    index = faiss.IndexFlatL2(dimension)
    index.add(embeddings)

    faiss.write_index(index, str(INDEX_PATH))

    with open(CHUNKS_PATH, "w", encoding="utf-8") as file:
        for chunk in chunks:
            file.write(chunk.replace("\n", "\\n"))
            file.write("\n---CHUNK---\n")

    print("Índice FAISS creado correctamente.")
    print(f"Chunks guardados: {len(chunks)}")
    print(f"Columnas usadas: {len(df.columns)}")
    print("Columnas del dataset:")
    print(df.columns.tolist())
    print(f"Ruta índice: {INDEX_PATH}")
    print(f"Ruta chunks: {CHUNKS_PATH}")


if __name__ == "__main__":
    crear_indice_faiss()