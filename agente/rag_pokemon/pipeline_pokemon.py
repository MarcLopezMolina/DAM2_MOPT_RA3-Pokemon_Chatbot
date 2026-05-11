from __future__ import annotations

from datetime import datetime
from pathlib import Path
import unicodedata
import re

import pandas as pd

from rag_faiss_pokemon import recuperar_chunks


BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "dataSetFinal.xlsx"
LOG_ESCALADOS = BASE_DIR / "logs_escalado.txt"


ERRORES_COMUNES = {
    "pecharun": "pecharunt",
    "picachu": "pikachu",
    "pikatchu": "pikachu",
    "charisar": "charizard",
    "charizad": "charizard",
    "abilididades": "habilidades",
    "avildiades": "habilidades",
    "avlidades": "habilidades",
    "estadisticas": "estadísticas",
    "generacion": "generación",
    "cuanto": "cuánto",
    "cual": "cuál",
    "mas": "más",
}


STAT_COLUMNS = ["HP", "Attack", "Defense", "Sp.Atk", "Sp.Def", "Speed"]


FIELD_ALIASES = [
    {
        "keys": ["peso", "pesa", "weight"],
        "columns": ["Weight(kg)", "Weight", "Peso"],
        "label": "peso",
        "unit": "kg",
    },
    {
        "keys": ["altura", "mide", "height"],
        "columns": ["Height(m)", "Height", "Altura"],
        "label": "altura",
        "unit": "m",
    },
    {
        "keys": ["habilidad", "habilidades", "ability", "abilities"],
        "columns": ["Abilities", "Habilidades"],
        "label": "habilidades",
        "unit": "",
    },
    {
        "keys": ["tipo", "tipos", "type"],
        "columns": ["Type_1", "Type 1", "Tipo 1"],
        "label": "tipo",
        "unit": "",
    },
    {
        "keys": ["segundo tipo", "tipo secundario", "type 2"],
        "columns": ["Type_2", "Type 2", "Tipo 2"],
        "label": "segundo tipo",
        "unit": "",
    },
    {
        "keys": ["vida", "hp"],
        "columns": ["HP"],
        "label": "HP",
        "unit": "",
    },
    {
        "keys": ["ataque especial", "special attack", "sp atk", "sp.atk"],
        "columns": ["Sp.Atk", "Sp. Atk", "Special Attack"],
        "label": "ataque especial",
        "unit": "",
    },
    {
        "keys": ["defensa especial", "special defense", "sp def", "sp.def"],
        "columns": ["Sp.Def", "Sp. Def", "Special Defense"],
        "label": "defensa especial",
        "unit": "",
    },
    {
        "keys": ["ataque", "attack"],
        "columns": ["Attack", "Ataque"],
        "label": "ataque",
        "unit": "",
    },
    {
        "keys": ["defensa", "defense"],
        "columns": ["Defense", "Defensa"],
        "label": "defensa",
        "unit": "",
    },
    {
        "keys": ["velocidad", "speed", "rápido", "rapido"],
        "columns": ["Speed", "Velocidad"],
        "label": "velocidad",
        "unit": "",
    },
    {
        "keys": ["total", "total stats", "estadísticas totales", "estadisticas totales"],
        "columns": ["Total_Stats", "Total Stats", "Total"],
        "label": "estadísticas totales",
        "unit": "",
    },
    {
        "keys": ["generación", "generacion", "generation"],
        "columns": ["Generation", "Generación"],
        "label": "generación",
        "unit": "",
    },
    {
        "keys": ["legendario", "legendaria", "legendary"],
        "columns": ["Is_Legendary", "Legendary", "Legendario"],
        "label": "legendario",
        "unit": "",
    },
    {
        "keys": ["mítico", "mitico", "mythical"],
        "columns": ["Is_Mythical", "Mythical"],
        "label": "mítico",
        "unit": "",
    },
    {
        "keys": ["pseudo legendario", "pseudo legendary"],
        "columns": ["Is_Pseudo_Legendary", "Pseudo Legendary"],
        "label": "pseudo legendario",
        "unit": "",
    },
    {
        "keys": ["baby", "bebé", "bebe"],
        "columns": ["Is_Baby", "Baby"],
        "label": "baby",
        "unit": "",
    },
    {
        "keys": ["captura", "capture rate"],
        "columns": ["Capture_Rate", "Capture Rate"],
        "label": "ratio de captura",
        "unit": "",
    },
    {
        "keys": ["felicidad", "happiness", "base happiness"],
        "columns": ["Base_Happiness", "Base Happiness"],
        "label": "felicidad base",
        "unit": "",
    },
    {
        "keys": ["egg cycles", "ciclos huevo", "huevo"],
        "columns": ["Egg_Cycles", "Egg Cycles"],
        "label": "ciclos de huevo",
        "unit": "",
    },
    {
        "keys": ["egg group", "grupo huevo"],
        "columns": ["Egg_Group_1", "Egg Group 1"],
        "label": "grupo huevo",
        "unit": "",
    },
    {
        "keys": ["mega", "mega evolución", "mega evolucion"],
        "columns": ["Mega Evolution", "Mega_Evolution"],
        "label": "mega evolución",
        "unit": "",
    },
]


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
    texto = texto.lower()
    texto = " ".join(texto.split())

    for mal, bien in ERRORES_COMUNES.items():
        texto = texto.replace(mal, bien)

    return texto


def cargar_dataset() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"No se encontró el dataset en: {DATA_PATH}")

    df = pd.read_excel(DATA_PATH)
    df.columns = [str(columna).strip() for columna in df.columns]
    return df


def obtener_columna_nombre(df: pd.DataFrame) -> str | None:
    for columna in ["Name", "Nombre", "name", "nombre"]:
        if columna in df.columns:
            return columna

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


def encontrar_columna(df: pd.DataFrame, posibles_columnas: list[str]) -> str | None:
    columnas_normalizadas = {
        normalizar_texto(columna): columna for columna in df.columns
    }

    for posible in posibles_columnas:
        posible_norm = normalizar_texto(posible)

        if posible_norm in columnas_normalizadas:
            return columnas_normalizadas[posible_norm]

    for posible in posibles_columnas:
        posible_norm = normalizar_texto(posible)

        for columna_norm, columna_real in columnas_normalizadas.items():
            if posible_norm in columna_norm or columna_norm in posible_norm:
                return columna_real

    return None


def detectar_pokemons_en_pregunta(pregunta: str) -> list[str]:
    df = cargar_dataset()
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return []

    pregunta_normalizada = normalizar_texto(pregunta)
    nombres = df[columna_nombre].dropna().astype(str).tolist()
    nombres = sorted(nombres, key=len, reverse=True)

    encontrados = []

    for nombre in nombres:
        if normalizar_texto(nombre) in pregunta_normalizada:
            encontrados.append(nombre)

    return encontrados


def obtener_fila_pokemon(nombre_pokemon: str) -> pd.Series | None:
    df = cargar_dataset()
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    nombre_normalizado = normalizar_texto(nombre_pokemon)

    for _, row in df.iterrows():
        if normalizar_texto(row.get(columna_nombre, "")) == nombre_normalizado:
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

    posibles_columnas_id = ["id", "ID", "#", "Number", "Número", "numero", "Pokedex Number"]

    columna_id = encontrar_columna(df, posibles_columnas_id)

    if columna_id is None:
        return None

    serie_id = pd.to_numeric(df[columna_id], errors="coerce")

    resultado = df[serie_id == numero]

    if resultado.empty:
        return None

    return resultado.iloc[0]


def fila_a_chunk(row: pd.Series) -> str:
    lineas = []

    for columna, valor in row.items():
        if pd.isna(valor):
            valor = ""

        lineas.append(f"{columna}: {valor}")

    return "\n".join(lineas)


def obtener_lineas_chunk(chunk: str) -> dict[str, str]:
    datos = {}

    for linea in chunk.splitlines():
        if ":" not in linea:
            continue

        campo, valor = linea.split(":", 1)
        datos[campo.strip()] = valor.strip()

    return datos


def extraer_valor_de_chunk(chunk: str, posibles_campos: list[str]) -> str:
    datos = obtener_lineas_chunk(chunk)
    posibles_normalizados = [normalizar_texto(campo) for campo in posibles_campos]

    for campo, valor in datos.items():
        campo_normalizado = normalizar_texto(campo)

        for posible in posibles_normalizados:
            if campo_normalizado == posible:
                return valor

    for campo, valor in datos.items():
        campo_normalizado = normalizar_texto(campo)

        for posible in posibles_normalizados:
            if posible in campo_normalizado or campo_normalizado in posible:
                return valor

    return "No disponible"


def formatear_datos_generales(row: pd.Series) -> str:
    nombre = formatear_valor(row.get("Name", row.get("Nombre", "Desconocido")))
    respuesta = f"Datos de {nombre}:\n"

    for campo, valor in row.items():
        if valor_vacio(valor):
            continue

        respuesta += f"- {campo}: {formatear_valor(valor)}\n"

    return respuesta.strip()


def campo_pedido_por_pregunta(pregunta: str) -> dict | None:
    pregunta_norm = normalizar_texto(pregunta)

    for campo in FIELD_ALIASES:
        for key in campo["keys"]:
            if normalizar_texto(key) in pregunta_norm:
                return campo

    return None


def responder_campo_pokemon(row: pd.Series, pregunta: str) -> str | None:
    df = cargar_dataset()
    nombre = formatear_valor(row.get("Name", row.get("Nombre", "Desconocido")))

    campo = campo_pedido_por_pregunta(pregunta)

    if campo is None:
        return None

    if campo["label"] == "tipo":
        col_tipo_1 = encontrar_columna(df, ["Type_1", "Type 1", "Tipo 1"])
        col_tipo_2 = encontrar_columna(df, ["Type_2", "Type 2", "Tipo 2"])

        tipo_1 = row.get(col_tipo_1, "") if col_tipo_1 else ""
        tipo_2 = row.get(col_tipo_2, "") if col_tipo_2 else ""

        if not valor_vacio(tipo_2):
            return f"{nombre} es de tipo {formatear_valor(tipo_1)} y {formatear_valor(tipo_2)}."

        return f"{nombre} es de tipo {formatear_valor(tipo_1)}."

    columna = encontrar_columna(df, campo["columns"])

    if columna is None:
        return None

    valor = row.get(columna, "")

    if valor_vacio(valor):
        return None

    valor_formateado = formatear_valor(valor)
    unidad = f" {campo['unit']}" if campo["unit"] else ""

    if campo["label"] == "peso":
        return f"{nombre} pesa {valor_formateado}{unidad}."

    if campo["label"] == "altura":
        return f"{nombre} mide {valor_formateado}{unidad}."

    if campo["label"] == "habilidades":
        return f"Las habilidades de {nombre} son: {valor_formateado}."

    return f"{nombre} tiene {campo['label']}: {valor_formateado}{unidad}."


def obtener_estadistica_mas_alta(row: pd.Series) -> str:
    nombre = formatear_valor(row.get("Name", row.get("Nombre", "Desconocido")))

    estadisticas = {}

    for columna in STAT_COLUMNS:
        if columna in row.index and not valor_vacio(row[columna]):
            try:
                estadisticas[columna] = float(row[columna])
            except ValueError:
                pass

    if not estadisticas:
        return f"No tengo información suficiente sobre las estadísticas de {nombre}."

    stat_mas_alta = max(estadisticas, key=estadisticas.get)
    valor = estadisticas[stat_mas_alta]

    if valor.is_integer():
        valor = int(valor)

    return f"La estadística más alta de {nombre} es {stat_mas_alta}, con un valor de {valor}."


def obtener_estadistica_mas_baja(row: pd.Series) -> str:
    nombre = formatear_valor(row.get("Name", row.get("Nombre", "Desconocido")))

    estadisticas = {}

    for columna in STAT_COLUMNS:
        if columna in row.index and not valor_vacio(row[columna]):
            try:
                estadisticas[columna] = float(row[columna])
            except ValueError:
                pass

    if not estadisticas:
        return f"No tengo información suficiente sobre las estadísticas de {nombre}."

    stat_mas_baja = min(estadisticas, key=estadisticas.get)
    valor = estadisticas[stat_mas_baja]

    if valor.is_integer():
        valor = int(valor)

    return f"La estadística más baja de {nombre} es {stat_mas_baja}, con un valor de {valor}."


def comparar_pokemons(nombres: list[str]) -> str:
    if len(nombres) < 2:
        return "Necesito al menos dos Pokémon para comparar."

    filas = []

    for nombre in nombres[:2]:
        row = obtener_fila_pokemon(nombre)

        if row is not None:
            filas.append(row)

    if len(filas) < 2:
        return "No he podido encontrar los dos Pokémon en el dataset."

    nombre_1 = formatear_valor(filas[0].get("Name", filas[0].get("Nombre", "Pokémon 1")))
    nombre_2 = formatear_valor(filas[1].get("Name", filas[1].get("Nombre", "Pokémon 2")))

    respuesta = f"Comparación entre {nombre_1} y {nombre_2}:\n"

    columnas_comparacion = [
        "Type_1",
        "Type_2",
        "HP",
        "Attack",
        "Defense",
        "Sp.Atk",
        "Sp.Def",
        "Speed",
        "Total_Stats",
        "Height(m)",
        "Weight(kg)",
        "Abilities",
    ]

    for columna in columnas_comparacion:
        if columna not in filas[0].index or columna not in filas[1].index:
            continue

        valor_1 = formatear_valor(filas[0].get(columna, ""))
        valor_2 = formatear_valor(filas[1].get(columna, ""))

        if valor_1 == "" and valor_2 == "":
            continue

        respuesta += f"- {columna}: {nombre_1} = {valor_1} | {nombre_2} = {valor_2}\n"

    return respuesta.strip()


def obtener_maximo_o_minimo_global(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    campo = campo_pedido_por_pregunta(pregunta)

    if campo is None:
        if "rapido" in pregunta_norm or "rapida" in pregunta_norm:
            campo = {
                "columns": ["Speed"],
                "label": "velocidad",
                "unit": "",
            }
        elif "fuerte" in pregunta_norm:
            campo = {
                "columns": ["Attack"],
                "label": "ataque",
                "unit": "",
            }
        else:
            return None

    columna = encontrar_columna(df, campo["columns"])

    if columna is None:
        return None

    serie = pd.to_numeric(df[columna], errors="coerce")

    if serie.dropna().empty:
        return None

    quiere_minimo = any(
        palabra in pregunta_norm
        for palabra in ["menos", "menor", "minimo", "minima", "mas bajo", "mas baja"]
    )

    if quiere_minimo:
        indice = serie.idxmin()
        tipo_busqueda = "menor"
    else:
        indice = serie.idxmax()
        tipo_busqueda = "mayor"

    row = df.loc[indice]
    nombre = formatear_valor(row[columna_nombre])
    valor = formatear_valor(row[columna])
    unidad = f" {campo.get('unit', '')}" if campo.get("unit") else ""

    return (
        f"El Pokémon con {tipo_busqueda} {campo['label']} es {nombre}, "
        f"con un valor de {valor}{unidad}."
    )


def obtener_ranking(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    if not any(palabra in pregunta_norm for palabra in ["top", "ranking", "mejores"]):
        return None

    campo = campo_pedido_por_pregunta(pregunta)

    if campo is None:
        return None

    columna = encontrar_columna(df, campo["columns"])

    if columna is None:
        return None

    df_temp = df.copy()
    df_temp[columna] = pd.to_numeric(df_temp[columna], errors="coerce")
    df_temp = df_temp.dropna(subset=[columna])

    if df_temp.empty:
        return None

    top = df_temp.sort_values(by=columna, ascending=False).head(10)

    respuesta = f"Top 10 Pokémon por {campo['label']}:\n"

    for posicion, (_, row) in enumerate(top.iterrows(), start=1):
        respuesta += (
            f"{posicion}. {formatear_valor(row[columna_nombre])} "
            f"- {formatear_valor(row[columna])}\n"
        )

    return respuesta.strip()


def listar_por_tipo(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    tipos = [
        "normal", "fire", "water", "grass", "electric", "ice",
        "fighting", "poison", "ground", "flying", "psychic",
        "bug", "rock", "ghost", "dragon", "dark", "steel", "fairy"
    ]

    tipo_detectado = None

    for tipo in tipos:
        if tipo in pregunta_norm:
            tipo_detectado = tipo
            break

    if tipo_detectado is None:
        return None

    col_tipo_1 = encontrar_columna(df, ["Type_1", "Type 1", "Tipo 1"])
    col_tipo_2 = encontrar_columna(df, ["Type_2", "Type 2", "Tipo 2"])

    if col_tipo_1 is None:
        return None

    filtro_1 = df[col_tipo_1].astype(str).str.lower() == tipo_detectado

    if col_tipo_2 is not None:
        filtro_2 = df[col_tipo_2].astype(str).str.lower() == tipo_detectado
        resultado = df[filtro_1 | filtro_2]
    else:
        resultado = df[filtro_1]

    if resultado.empty:
        return f"No he encontrado Pokémon de tipo {tipo_detectado.title()} en el dataset."

    nombres = resultado[columna_nombre].dropna().astype(str).head(25).tolist()

    return (
        f"Algunos Pokémon de tipo {tipo_detectado.title()} son: "
        + ", ".join(nombres)
        + "."
    )


def listar_por_generacion_o_flags(pregunta: str) -> str | None:
    df = cargar_dataset()
    pregunta_norm = normalizar_texto(pregunta)
    columna_nombre = obtener_columna_nombre(df)

    if columna_nombre is None:
        return None

    resultado = df.copy()
    filtros_aplicados = []

    if "legendario" in pregunta_norm or "legendaria" in pregunta_norm:
        col = encontrar_columna(df, ["Is_Legendary", "Legendary"])
        if col:
            resultado = resultado[resultado[col].astype(str).str.lower().isin(["true", "1", "verdadero"])]
            filtros_aplicados.append("legendarios")

    if "mitico" in pregunta_norm or "mythical" in pregunta_norm:
        col = encontrar_columna(df, ["Is_Mythical", "Mythical"])
        if col:
            resultado = resultado[resultado[col].astype(str).str.lower().isin(["true", "1", "verdadero"])]
            filtros_aplicados.append("míticos")

    if "baby" in pregunta_norm or "bebe" in pregunta_norm:
        col = encontrar_columna(df, ["Is_Baby", "Baby"])
        if col:
            resultado = resultado[resultado[col].astype(str).str.lower().isin(["true", "1", "verdadero"])]
            filtros_aplicados.append("baby")

    col_gen = encontrar_columna(df, ["Generation", "Generación"])

    if col_gen:
        for i in range(1, 10):
            if f"gen {i}" in pregunta_norm or f"gen-{i}" in pregunta_norm or f"generacion {i}" in pregunta_norm:
                resultado = resultado[resultado[col_gen].astype(str).str.lower().isin([f"gen-{i}", f"gen {i}", str(i)])]
                filtros_aplicados.append(f"Gen-{i}")
                break

    if not filtros_aplicados:
        return None

    if resultado.empty:
        return "No he encontrado Pokémon que cumplan esos filtros en el dataset."

    nombres = resultado[columna_nombre].dropna().astype(str).head(25).tolist()

    return (
        "Pokémon encontrados "
        + "(" + ", ".join(filtros_aplicados) + "): "
        + ", ".join(nombres)
        + "."
    )


def mostrar_chunks(pregunta: str) -> str | None:
    pregunta_norm = normalizar_texto(pregunta)

    if "chunk" not in pregunta_norm:
        return None

    contexto = recuperar_chunks(pregunta, k=3)

    if not contexto:
        return "No se han recuperado chunks."

    respuesta = "Chunks recuperados:\n"

    for i, chunk in enumerate(contexto, start=1):
        respuesta += f"\n--- Chunk {i} ---\n{chunk}\n"

    return respuesta.strip()


def generar_respuesta(contexto: list[str], pregunta: str) -> str:
    pregunta_norm = normalizar_texto(pregunta)
    
    id_detectado = detectar_id_en_pregunta(pregunta)

    if id_detectado is not None:
        row = obtener_fila_por_id(id_detectado)

        if row is None:
            return f"No he encontrado ningún Pokémon con el número {id_detectado} en el dataset."

        return formatear_datos_generales(row)

    respuesta_chunks = mostrar_chunks(pregunta)
    if respuesta_chunks is not None:
        return respuesta_chunks

    nombres_detectados = detectar_pokemons_en_pregunta(pregunta)

    if len(nombres_detectados) >= 2 and any(palabra in pregunta_norm for palabra in ["compara", "comparar", "diferencia"]):
        return comparar_pokemons(nombres_detectados)

    respuesta_ranking = obtener_ranking(pregunta)
    if respuesta_ranking is not None:
        return respuesta_ranking

    respuesta_tipo = listar_por_tipo(pregunta)
    if respuesta_tipo is not None and any(palabra in pregunta_norm for palabra in ["tipo", "fire", "water", "grass", "dragon", "electric"]):
        if len(nombres_detectados) == 0:
            return respuesta_tipo

    respuesta_flags = listar_por_generacion_o_flags(pregunta)
    if respuesta_flags is not None and len(nombres_detectados) == 0:
        return respuesta_flags

    respuesta_global = obtener_maximo_o_minimo_global(pregunta)
    if respuesta_global is not None and len(nombres_detectados) == 0:
        return respuesta_global

    if len(nombres_detectados) >= 1:
        nombre = nombres_detectados[0]
        row = obtener_fila_pokemon(nombre)

        if row is None:
            return "He detectado un Pokémon, pero no he podido encontrarlo en el dataset."

        if any(
            frase in pregunta_norm
            for frase in [
                "estadistica mas alta",
                "stat mas alta",
                "stat mayor",
                "mejor estadistica",
                "estadistica mayor",
            ]
        ):
            return obtener_estadistica_mas_alta(row)

        if any(
            frase in pregunta_norm
            for frase in [
                "estadistica mas baja",
                "stat mas baja",
                "stat menor",
                "peor estadistica",
                "estadistica menor",
            ]
        ):
            return obtener_estadistica_mas_baja(row)

        respuesta_campo = responder_campo_pokemon(row, pregunta)
        if respuesta_campo is not None:
            return respuesta_campo

        if any(
            palabra in pregunta_norm
            for palabra in ["datos", "informacion", "info", "que es", "quien es", "hablame", "sabes de"]
        ):
            return formatear_datos_generales(row)

        return (
            "No he podido interpretar exactamente qué campo concreto quieres, "
            "pero estos son los datos disponibles en el dataset:\n\n"
            + formatear_datos_generales(row)
        )

    if len(contexto) > 0:
        return (
            "He recuperado información relacionada, pero no puedo responder con seguridad "
            "sin detectar un Pokémon, filtro o campo concreto."
        )

    return "No tengo información suficiente para responder."


def es_respuesta_valida(respuesta: str, contexto: list[str]) -> bool:
    respuesta_lower = respuesta.lower()

    frases_invalidas = [
        "no tengo información suficiente",
        "no puedo responder con seguridad sin detectar",
        "he recuperado información relacionada, pero no puedo responder",
    ]

    for frase in frases_invalidas:
        if frase in respuesta_lower:
            return False

    if len(respuesta.strip()) < 5:
        return False

    return True


def escalar_a_humano(pregunta: str) -> str:
    with open(LOG_ESCALADOS, "a", encoding="utf-8") as file:
        file.write(f"[{datetime.now().isoformat()}] {pregunta}\n")

    return (
        "No he podido resolver tu consulta con seguridad usando el dataset disponible. "
        "Te paso con un agente humano."
    )


def manejar_pregunta(pregunta: str) -> str:
    input_limpio = preprocesar_input(pregunta)
    contexto = recuperar_chunks(input_limpio, k=10)
    respuesta = generar_respuesta(contexto, input_limpio)

    if not es_respuesta_valida(respuesta, contexto):
        return escalar_a_humano(pregunta)

    return respuesta


def main() -> None:
    print("Pipeline Pokémon avanzado activo. Escribe una pregunta o 'salir'.")

    while True:
        pregunta = input("\nPregunta> ").strip()

        if pregunta.lower() == "salir":
            break

        respuesta = manejar_pregunta(pregunta)

        print("\nRespuesta:")
        print(respuesta)


if __name__ == "__main__":
    main()