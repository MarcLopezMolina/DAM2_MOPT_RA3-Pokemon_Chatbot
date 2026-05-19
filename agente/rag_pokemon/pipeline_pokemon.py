from __future__ import annotations

from pathlib import Path
from datetime import datetime
from functools import lru_cache
import re
import unicodedata

import pandas as pd

from llm_pokemon import generar_respuesta_llm


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dataSetFinal.xlsx"
LOG_ESCALADOS = BASE_DIR / "logs_escalado.txt"


STAT_COLUMNS = ["HP", "Attack", "Defense", "Sp.Atk", "Sp.Def", "Speed"]

TYPE_TRANSLATIONS = {
    "normal": "Normal",
    "fuego": "Fire",
    "fire": "Fire",
    "agua": "Water",
    "water": "Water",
    "planta": "Grass",
    "hierba": "Grass",
    "grass": "Grass",
    "electrico": "Electric",
    "eléctrico": "Electric",
    "electric": "Electric",
    "hielo": "Ice",
    "ice": "Ice",
    "lucha": "Fighting",
    "fighting": "Fighting",
    "veneno": "Poison",
    "poison": "Poison",
    "tierra": "Ground",
    "ground": "Ground",
    "volador": "Flying",
    "flying": "Flying",
    "psiquico": "Psychic",
    "psíquico": "Psychic",
    "psychic": "Psychic",
    "bicho": "Bug",
    "bug": "Bug",
    "roca": "Rock",
    "rock": "Rock",
    "fantasma": "Ghost",
    "ghost": "Ghost",
    "dragon": "Dragon",
    "dragón": "Dragon",
    "siniestro": "Dark",
    "dark": "Dark",
    "acero": "Steel",
    "steel": "Steel",
    "hada": "Fairy",
    "fairy": "Fairy",
}

ERRORES_COMUNES = {
    "picachu": "pikachu",
    "pikatchu": "pikachu",
    "charisar": "charizard",
    "charizad": "charizard",
    "squirtel": "squirtle",
    "pecharun": "pecharunt",
    "abilididades": "habilidades",
    "avildiades": "habilidades",
    "estadisticas": "estadísticas",
    "generacion": "generación",
    "cuanto": "cuánto",
    "cual": "cuál",
    "mas": "más",
}


def normalizar_texto(texto: str) -> str:
    texto = str(texto).lower().strip()
    texto = unicodedata.normalize("NFD", texto)
    texto = "".join(char for char in texto if unicodedata.category(char) != "Mn")
    texto = texto.replace("_", " ")
    texto = texto.replace("-", " ")
    texto = texto.replace("(", " ")
    texto = texto.replace(")", " ")
    texto = texto.replace(".", " ")
    texto = " ".join(texto.split())
    return texto


def preprocesar_input(texto: str) -> str:
    texto = str(texto).lower().strip()
    texto = " ".join(texto.split())

    for mal, bien in ERRORES_COMUNES.items():
        texto = texto.replace(mal, bien)

    return texto


@lru_cache(maxsize=1)
def cargar_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el dataset en: {DATA_PATH}")

    df = pd.read_excel(DATA_PATH)
    df.columns = [str(col).strip() for col in df.columns]
    return df


def obtener_columna_nombre(df: pd.DataFrame) -> str | None:
    for columna in ["Name", "Nombre", "name", "nombre"]:
        if columna in df.columns:
            return columna
    return None


def encontrar_columna(df: pd.DataFrame, posibles: list[str]) -> str | None:
    mapa = {normalizar_texto(col): col for col in df.columns}

    for posible in posibles:
        key = normalizar_texto(posible)
        if key in mapa:
            return mapa[key]

    for posible in posibles:
        key = normalizar_texto(posible)
        for col_norm, col_real in mapa.items():
            if key in col_norm or col_norm in key:
                return col_real

    return None


def valor_vacio(valor) -> bool:
    if pd.isna(valor):
        return True

    texto = str(valor).strip()
    return texto == "" or texto.lower() == "nan"


def formatear_valor(valor) -> str:
    if pd.isna(valor):
        return ""

    if isinstance(valor, float) and valor.is_integer():
        return str(int(valor))

    return str(valor)


def fila_a_contexto(row: pd.Series) -> str:
    lineas = []

    for columna, valor in row.items():
        if valor_vacio(valor):
            continue

        lineas.append(f"{columna}: {formatear_valor(valor)}")

    return "\n".join(lineas)


def dataframe_a_contexto(df: pd.DataFrame, limite: int = 25) -> str:
    bloques = []

    for _, row in df.head(limite).iterrows():
        bloques.append(fila_a_contexto(row))

    return "\n\n---\n\n".join(bloques)


def detectar_pokemons_en_pregunta(pregunta: str) -> list[str]:
    df = cargar_dataset()
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return []

    pregunta_norm = normalizar_texto(pregunta)
    nombres = df[columna_nombre].dropna().astype(str).tolist()
    nombres = sorted(nombres, key=len, reverse=True)

    encontrados = []
    vistos = set()

    for nombre in nombres:
        nombre_norm = normalizar_texto(nombre)

        if nombre_norm in pregunta_norm and nombre_norm not in vistos:
            encontrados.append(nombre)
            vistos.add(nombre_norm)

    return encontrados


def obtener_fila_pokemon(nombre: str) -> pd.Series | None:
    df = cargar_dataset()
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    objetivo = normalizar_texto(nombre)

    for _, row in df.iterrows():
        if normalizar_texto(row.get(columna_nombre, "")) == objetivo:
            return row

    return None


def detectar_id_en_pregunta(pregunta: str) -> int | None:
    pregunta_norm = normalizar_texto(pregunta)

    patrones = [
        r"\bpokemon\s+(\d+)\b",
        r"\bpokemon\s*#\s*(\d+)\b",
        r"\bid\s+(\d+)\b",
        r"\bnumero\s+(\d+)\b",
        r"\bnum\s+(\d+)\b",
        r"\b#\s*(\d+)\b",
    ]

    for patron in patrones:
        match = re.search(patron, pregunta_norm)
        if match:
            return int(match.group(1))

    return None


def obtener_fila_por_id(numero: int) -> pd.Series | None:
    df = cargar_dataset()

    columna_id = encontrar_columna(
        df,
        ["id", "ID", "#", "Number", "Número", "numero", "Pokedex Number"],
    )

    if columna_id is None:
        return None

    ids = pd.to_numeric(df[columna_id], errors="coerce")
    resultado = df[ids == numero]

    if resultado.empty:
        return None

    return resultado.iloc[0]


def detectar_tipos_en_pregunta(pregunta: str) -> list[str]:
    pregunta_norm = normalizar_texto(pregunta)
    encontrados = []

    for palabra, tipo_en in TYPE_TRANSLATIONS.items():
        palabra_norm = normalizar_texto(palabra)

        if re.search(rf"\b{re.escape(palabra_norm)}\b", pregunta_norm):
            if tipo_en not in encontrados:
                encontrados.append(tipo_en)

    return encontrados


def contexto_por_id(pregunta: str) -> str | None:
    pokemon_id = detectar_id_en_pregunta(pregunta)

    if pokemon_id is None:
        return None

    row = obtener_fila_por_id(pokemon_id)

    if row is None:
        return ""

    return fila_a_contexto(row)


def contexto_por_nombres(pregunta: str) -> str | None:
    nombres = detectar_pokemons_en_pregunta(pregunta)

    if not nombres:
        return None

    bloques = []

    for nombre in nombres[:6]:
        row = obtener_fila_pokemon(nombre)

        if row is not None:
            bloques.append(fila_a_contexto(row))

    if not bloques:
        return ""

    return "\n\n---\n\n".join(bloques)


def contexto_por_tipo(pregunta: str) -> str | None:
    pregunta_norm = normalizar_texto(pregunta)

    if "tipo" not in pregunta_norm and "tipos" not in pregunta_norm:
        return None

    tipos = detectar_tipos_en_pregunta(pregunta)

    if not tipos:
        return None

    df = cargar_dataset()
    col_nombre = obtener_columna_nombre(df)
    col_tipo_1 = encontrar_columna(df, ["Type_1", "Type 1", "Tipo 1"])
    col_tipo_2 = encontrar_columna(df, ["Type_2", "Type 2", "Tipo 2"])

    if col_nombre is None or col_tipo_1 is None:
        return None

    df_temp = df.copy()
    df_temp[col_tipo_1] = df_temp[col_tipo_1].fillna("").astype(str).str.strip()

    if col_tipo_2:
        df_temp[col_tipo_2] = df_temp[col_tipo_2].fillna("").astype(str).str.strip()
    else:
        df_temp["__Type_2__"] = ""
        col_tipo_2 = "__Type_2__"

    tipo_1_lower = df_temp[col_tipo_1].str.lower()
    tipo_2_lower = df_temp[col_tipo_2].str.lower()

    if len(tipos) == 1:
        tipo = tipos[0]
        tipo_lower = tipo.lower()

        resultado = df_temp[
            (tipo_1_lower == tipo_lower)
            | (tipo_2_lower == tipo_lower)
        ]

        if resultado.empty:
            return (
                "RESPUESTA_CALCULADA:\n"
                f"No he encontrado Pokémon de tipo {tipo} en el dataset."
            )

        nombres = resultado[col_nombre].dropna().astype(str).head(20).tolist()

        return (
            "RESPUESTA_CALCULADA:\n"
            f"Algunos Pokémon de tipo {tipo} son: "
            + ", ".join(nombres)
            + "."
        )

    tipo_a = tipos[0]
    tipo_b = tipos[1]

    tipo_a_lower = tipo_a.lower()
    tipo_b_lower = tipo_b.lower()

    resultado = df_temp[
        (
            (tipo_1_lower == tipo_a_lower)
            & (tipo_2_lower == tipo_b_lower)
        )
        |
        (
            (tipo_1_lower == tipo_b_lower)
            & (tipo_2_lower == tipo_a_lower)
        )
    ]

    if resultado.empty:
        return (
            "RESPUESTA_CALCULADA:\n"
            f"No he encontrado Pokémon que sean de tipo {tipo_a} y {tipo_b} en el dataset."
        )

    nombres = resultado[col_nombre].dropna().astype(str).head(20).tolist()

    return (
        "RESPUESTA_CALCULADA:\n"
        f"Pokémon encontrados de tipo {tipo_a} y {tipo_b}: "
        + ", ".join(nombres)
        + "."
    )


def campo_pedido(pregunta: str) -> tuple[str, list[str], str] | None:
    pregunta_norm = normalizar_texto(pregunta)

    campos = [
        ("peso", ["Weight(kg)", "Weight", "Peso"], "kg"),
        ("altura", ["Height(m)", "Height", "Altura"], "m"),
        ("HP", ["HP"], ""),
        ("ataque", ["Attack", "Ataque"], ""),
        ("defensa", ["Defense", "Defensa"], ""),
        ("ataque especial", ["Sp.Atk", "Sp. Atk", "Special Attack"], ""),
        ("defensa especial", ["Sp.Def", "Sp. Def", "Special Defense"], ""),
        ("velocidad", ["Speed", "Velocidad"], ""),
        ("estadísticas totales", ["Total_Stats", "Total Stats", "Total"], ""),
        ("captura", ["Capture_Rate", "Capture Rate"], ""),
        ("felicidad", ["Base_Happiness", "Base Happiness"], ""),
    ]

    claves = {
        "peso": ["peso", "pesa", "weight"],
        "altura": ["altura", "mide", "height"],
        "HP": ["hp", "vida"],
        "ataque": ["ataque", "attack"],
        "defensa": ["defensa", "defense"],
        "ataque especial": ["ataque especial", "sp atk", "sp.atk"],
        "defensa especial": ["defensa especial", "sp def", "sp.def"],
        "velocidad": ["velocidad", "rapido", "speed"],
        "estadísticas totales": ["total", "total stats", "estadisticas totales"],
        "captura": ["captura", "capture rate"],
        "felicidad": ["felicidad", "happiness"],
    }

    for label, columnas, unidad in campos:
        for clave in claves[label]:
            if normalizar_texto(clave) in pregunta_norm:
                return label, columnas, unidad

    return None


def contexto_ranking_o_global(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    col_nombre = obtener_columna_nombre(df)

    if col_nombre is None:
        return None

    campo = campo_pedido(pregunta)

    if campo is None:
        if "fuerte" in pregunta_norm:
            campo = ("ataque", ["Attack"], "")
        elif "rapido" in pregunta_norm or "rapida" in pregunta_norm:
            campo = ("velocidad", ["Speed"], "")
        else:
            return None

    label, columnas, _unidad = campo
    columna = encontrar_columna(df, columnas)

    if columna is None:
        return None

    df_temp = df.copy()
    df_temp[columna] = pd.to_numeric(df_temp[columna], errors="coerce")
    df_temp = df_temp.dropna(subset=[columna])

    if df_temp.empty:
        return None

    quiere_min = any(
        palabra in pregunta_norm
        for palabra in ["menor", "menos", "minimo", "minima", "mas bajo", "mas baja"]
    )

    if any(palabra in pregunta_norm for palabra in ["top", "ranking", "lista", "dime 5", "dime cinco"]):
        resultado = df_temp.sort_values(by=columna, ascending=quiere_min).head(10)
    else:
        if quiere_min:
            resultado = df_temp.loc[[df_temp[columna].idxmin()]]
        else:
            resultado = df_temp.loc[[df_temp[columna].idxmax()]]

    contexto = f"Consulta sobre {label}.\n\n"
    contexto += dataframe_a_contexto(resultado, limite=10)
    return contexto


def contexto_por_flags_o_generacion(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    resultado = df.copy()
    filtros = []

    if "legendario" in pregunta_norm or "legendaria" in pregunta_norm:
        col = encontrar_columna(df, ["Is_Legendary", "Legendary"])
        if col:
            resultado = resultado[resultado[col].astype(str).str.lower().isin(["true", "1", "verdadero"])]
            filtros.append("legendario")

    if "mitico" in pregunta_norm or "mythical" in pregunta_norm:
        col = encontrar_columna(df, ["Is_Mythical", "Mythical"])
        if col:
            resultado = resultado[resultado[col].astype(str).str.lower().isin(["true", "1", "verdadero"])]
            filtros.append("mítico")

    col_gen = encontrar_columna(df, ["Generation", "Generación"])

    if col_gen:
        for i in range(1, 10):
            if f"gen {i}" in pregunta_norm or f"generacion {i}" in pregunta_norm:
                resultado = resultado[
                    resultado[col_gen].astype(str).str.lower().isin(
                        [f"gen-{i}", f"gen {i}", str(i)]
                    )
                ]
                filtros.append(f"generación {i}")
                break

    if not filtros:
        return None

    if resultado.empty:
        return ""

    return "Filtros aplicados: " + ", ".join(filtros) + "\n\n" + dataframe_a_contexto(resultado, limite=25)


def contexto_comparacion_o_batalla(pregunta: str) -> str | None:
    pregunta_norm = normalizar_texto(pregunta)

    palabras = [
        "compara",
        "comparar",
        "diferencia",
        "quien gana",
        "ganaria",
        "batalla",
        "combate",
        "vs",
        "versus",
    ]

    if not any(palabra in pregunta_norm for palabra in palabras):
        return None

    nombres = detectar_pokemons_en_pregunta(pregunta)

    if len(nombres) < 2:
        return None

    row_1 = obtener_fila_pokemon(nombres[0])
    row_2 = obtener_fila_pokemon(nombres[1])

    if row_1 is None or row_2 is None:
        return ""

    nombre_1 = str(row_1.get("Name", nombres[0]))
    nombre_2 = str(row_2.get("Name", nombres[1]))

    total_1 = obtener_numero(row_1, ["Total_Stats", "Total Stats", "Total"])
    total_2 = obtener_numero(row_2, ["Total_Stats", "Total Stats", "Total"])

    ataque_1 = obtener_numero(row_1, ["Attack"])
    ataque_2 = obtener_numero(row_2, ["Attack"])

    defensa_1 = obtener_numero(row_1, ["Defense"])
    defensa_2 = obtener_numero(row_2, ["Defense"])

    velocidad_1 = obtener_numero(row_1, ["Speed"])
    velocidad_2 = obtener_numero(row_2, ["Speed"])

    tipo_1_a = str(row_1.get("Type_1", "")).strip()
    tipo_1_b = str(row_1.get("Type_2", "")).strip()
    tipo_2_a = str(row_2.get("Type_1", "")).strip()
    tipo_2_b = str(row_2.get("Type_2", "")).strip()

    tipos_1 = [t for t in [tipo_1_a, tipo_1_b] if t and t.lower() != "nan"]
    tipos_2 = [t for t in [tipo_2_a, tipo_2_b] if t and t.lower() != "nan"]

    ventaja_1 = tiene_ventaja_tipo(tipos_1, tipos_2)
    ventaja_2 = tiene_ventaja_tipo(tipos_2, tipos_1)

    ganador = None
    motivo = ""

    if ventaja_1 and not ventaja_2:
        ganador = nombre_1
        motivo = f"{nombre_1} tiene ventaja de tipo sobre {nombre_2}."
    elif ventaja_2 and not ventaja_1:
        ganador = nombre_2
        motivo = f"{nombre_2} tiene ventaja de tipo sobre {nombre_1}."
    elif total_1 is not None and total_2 is not None:
        if total_1 > total_2:
            ganador = nombre_1
            motivo = f"{nombre_1} tiene más estadísticas totales ({total_1}) que {nombre_2} ({total_2})."
        elif total_2 > total_1:
            ganador = nombre_2
            motivo = f"{nombre_2} tiene más estadísticas totales ({total_2}) que {nombre_1} ({total_1})."
        else:
            ganador = "empate aproximado"
            motivo = "Ambos tienen las mismas estadísticas totales."
    else:
        puntos_1 = sum(x for x in [ataque_1, defensa_1, velocidad_1] if x is not None)
        puntos_2 = sum(x for x in [ataque_2, defensa_2, velocidad_2] if x is not None)

        if puntos_1 > puntos_2:
            ganador = nombre_1
            motivo = f"{nombre_1} supera a {nombre_2} en la suma simple de ataque, defensa y velocidad."
        elif puntos_2 > puntos_1:
            ganador = nombre_2
            motivo = f"{nombre_2} supera a {nombre_1} en la suma simple de ataque, defensa y velocidad."
        else:
            ganador = "empate aproximado"
            motivo = "Los datos disponibles no dan una ventaja clara."

    respuesta = (
        f"En una estimación simple, ganaría {ganador}.\n\n"
        f"Motivo principal: {motivo}\n\n"
        f"Datos usados:\n"
        f"- {nombre_1}: tipos {', '.join(tipos_1) if tipos_1 else 'no disponibles'}, "
        f"Total_Stats={total_1}, Attack={ataque_1}, Defense={defensa_1}, Speed={velocidad_1}.\n"
        f"- {nombre_2}: tipos {', '.join(tipos_2) if tipos_2 else 'no disponibles'}, "
        f"Total_Stats={total_2}, Attack={ataque_2}, Defense={defensa_2}, Speed={velocidad_2}.\n\n"
        f"Esto es una comparación simplificada usando el dataset. En un combate real también influyen movimientos, nivel, habilidades y estrategia."
    )

    return "RESPUESTA_CALCULADA:\n" + respuesta


def contexto_estadistica_pokemon(pregunta: str) -> str | None:
    pregunta_norm = normalizar_texto(pregunta)

    if not any(
        frase in pregunta_norm
        for frase in [
            "estadistica mas alta",
            "estadistica mayor",
            "mejor estadistica",
            "estadistica mas baja",
            "estadistica menor",
            "peor estadistica",
        ]
    ):
        return None

    nombres = detectar_pokemons_en_pregunta(pregunta)

    if not nombres:
        return None

    row = obtener_fila_pokemon(nombres[0])

    if row is None:
        return ""

    estadisticas = []

    for col in STAT_COLUMNS:
        if col in row.index and not valor_vacio(row[col]):
            estadisticas.append(f"{col}: {formatear_valor(row[col])}")

    contexto = fila_a_contexto(row)
    contexto += "\n\nEstadísticas principales detectadas:\n" + "\n".join(estadisticas)

    return contexto


def contexto_general_pokemon(pregunta: str) -> str | None:
    contexto = contexto_por_id(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_comparacion_o_batalla(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_estadistica_pokemon(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_por_tipo(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_ranking_o_global(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_por_flags_o_generacion(pregunta)
    if contexto is not None:
        return contexto

    contexto = contexto_por_nombres(pregunta)
    if contexto is not None:
        return contexto

    return None


def es_respuesta_valida(respuesta: str, contexto: str | None) -> bool:
    respuesta_lower = respuesta.lower().strip()

    if not contexto:
        return False

    if len(respuesta_lower) < 10:
        return False

    frases_invalidas = [
        "no he podido resolver tu consulta con seguridad",
        "no tengo información suficiente",
        "no tengo informacion suficiente",
        "te paso con un agente humano",
    ]

    for frase in frases_invalidas:
        if frase in respuesta_lower:
            return False

    return True


def escalar_a_humano(pregunta: str) -> str:
    with open(LOG_ESCALADOS, "a", encoding="utf-8") as file:
        file.write(f"[{datetime.now().isoformat(timespec='seconds')}] {pregunta}\n")

    return (
        "No he podido resolver tu consulta con seguridad usando el dataset disponible. "
        "Te paso con un agente humano."
    )


def manejar_pregunta(pregunta: str) -> str:
    pregunta_limpia = preprocesar_input(pregunta)

    contexto = contexto_general_pokemon(pregunta_limpia)

    if contexto is None:
        return escalar_a_humano(pregunta)

    if contexto == "":
        return escalar_a_humano(pregunta)

    respuesta = generar_respuesta_llm(pregunta_limpia, contexto)

    if not es_respuesta_valida(respuesta, contexto):
        return escalar_a_humano(pregunta)

    return respuesta


def main() -> None:
    print("Pipeline Pokémon con IA local activo. Escribe una pregunta o 'salir'.")

    while True:
        pregunta = input("\nPregunta> ").strip()

        if pregunta.lower() == "salir":
            break

        respuesta = manejar_pregunta(pregunta)

        print("\nRespuesta:")
        print(respuesta)

def obtener_numero(row: pd.Series, columnas: list[str]) -> float | None:
    for columna in columnas:
        if columna in row.index:
            valor = pd.to_numeric(row.get(columna), errors="coerce")

            if pd.isna(valor):
                return None

            if float(valor).is_integer():
                return int(valor)

            return float(valor)

    return None


def tiene_ventaja_tipo(tipos_atacante: list[str], tipos_defensor: list[str]) -> bool:
    ventajas = {
        "Fire": ["Grass", "Ice", "Bug", "Steel"],
        "Water": ["Fire", "Ground", "Rock"],
        "Grass": ["Water", "Ground", "Rock"],
        "Electric": ["Water", "Flying"],
        "Ice": ["Grass", "Ground", "Flying", "Dragon"],
        "Fighting": ["Normal", "Ice", "Rock", "Dark", "Steel"],
        "Poison": ["Grass", "Fairy"],
        "Ground": ["Fire", "Electric", "Poison", "Rock", "Steel"],
        "Flying": ["Grass", "Fighting", "Bug"],
        "Psychic": ["Fighting", "Poison"],
        "Bug": ["Grass", "Psychic", "Dark"],
        "Rock": ["Fire", "Ice", "Flying", "Bug"],
        "Ghost": ["Psychic", "Ghost"],
        "Dragon": ["Dragon"],
        "Dark": ["Psychic", "Ghost"],
        "Steel": ["Ice", "Rock", "Fairy"],
        "Fairy": ["Fighting", "Dragon", "Dark"],
    }

    tipos_atacante_norm = [str(t).strip().title() for t in tipos_atacante]
    tipos_defensor_norm = [str(t).strip().title() for t in tipos_defensor]

    for tipo_atacante in tipos_atacante_norm:
        fuertes_contra = ventajas.get(tipo_atacante, [])

        for tipo_defensor in tipos_defensor_norm:
            if tipo_defensor in fuertes_contra:
                return True

    return False


if __name__ == "__main__":
    main()