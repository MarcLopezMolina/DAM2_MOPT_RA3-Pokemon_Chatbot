from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import re
import unicodedata

import pandas as pd


@dataclass
class AgentState:
    current_step: str = "waiting_for_question"
    last_question: str | None = None
    last_intent: str | None = None
    used_rag: bool = False

    def to_dict(self) -> dict:
        return {
            "current_step": self.current_step,
            "last_question": self.last_question,
            "last_intent": self.last_intent,
            "used_rag": self.used_rag,
        }


@dataclass
class AgentResponse:
    intent: str
    message: str
    state: AgentState

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "message": self.message,
            "state": self.state.to_dict(),
        }


class PokemonAgent:
    def __init__(self) -> None:
        self.state = AgentState()
        self.pokemon_names = self.load_pokemon_names()
        print(f"Nombres de Pokémon cargados: {len(self.pokemon_names)}")

    def normalize_text(self, text: str) -> str:
        text = str(text).lower().strip()
        text = unicodedata.normalize("NFD", text)
        text = "".join(char for char in text if unicodedata.category(char) != "Mn")
        text = " ".join(text.split())
        return text

    def load_pokemon_names(self) -> list[str]:
        base_dir = Path(__file__).resolve().parent
        excel_path = base_dir / "data" / "dataSetFinal.xlsx"

        if not excel_path.exists():
            print(f"No se encontró el Excel en: {excel_path}")
            return []

        df = pd.read_excel(excel_path)
        df.columns = [str(column).strip() for column in df.columns]

        possible_name_columns = ["Name", "Nombre", "name", "nombre"]

        name_column = None

        for column in possible_name_columns:
            if column in df.columns:
                name_column = column
                break

        if name_column is None:
            print("No se encontró columna de nombre.")
            print("Columnas encontradas:")
            print(df.columns.tolist())
            return []

        names = df[name_column].dropna().astype(str).tolist()
        names = [self.normalize_text(name) for name in names]
        names = sorted(names, key=len, reverse=True)

        return names

    def run(self, user_message: str) -> AgentResponse:
        intent = self.analyze_intent(user_message)

        self.state.last_question = user_message
        self.state.last_intent = intent

        if intent == "exit":
            self.state.current_step = "exit"
            self.state.used_rag = False

            return AgentResponse(
                intent=intent,
                message="Cerrando agente Pokémon.",
                state=self.state,
            )

        if intent == "show_state":
            return AgentResponse(
                intent=intent,
                message="Este es el estado actual del agente Pokémon.",
                state=self.state,
            )

        if intent == "general_question":
            return self.handle_general_question(user_message)

        if intent == "rag_question":
            return self.handle_rag_question(user_message)

        return self.escalar_a_humano()

    def analyze_intent(self, user_message: str) -> str:
        text = user_message.strip()
        lowered = self.normalize_text(text)

        if lowered in ["salir", "exit", "quit"]:
            return "exit"

        if lowered == "estado":
            return "show_state"

        general_direct_keywords = [
            "ash",
            "ash ketchum",
            "profesor oak",
            "profesor pokemon",
            "enfermera joy",
            "team rocket",
            "equipo rocket",
            "misty",
            "brock",
            "may",
            "dawn",
            "serena",
            "goh",
            "quien es ash",
            "quien es el profesor oak",
            "quien es misty",
            "quien es brock",
            "quien es serena",
            "quienes son el team rocket",
        ]

        for keyword in general_direct_keywords:
            if keyword in lowered:
                return "general_question"

        if re.search(r"\b(pokemon|id|numero|num|#)\s*#?\s*\d+\b", lowered):
            return "rag_question"

        rag_keywords = [
            "habilidad",
            "habilidades",
            "tipo",
            "tipos",
            "hp",
            "ataque",
            "defensa",
            "velocidad",
            "estadistica",
            "estadisticas",
            "generacion",
            "peso",
            "pesa",
            "altura",
            "mide",
            "total",
            "compara",
            "comparar",
            "diferencia",
            "quien gana",
            "ganaria",
            "batalla",
            "combate",
            "vs",
            "versus",
            "dime los datos",
            "datos",
            "dato",
            "informacion",
            "info",
            "de que tipo",
            "top",
            "ranking",
            "mas fuerte",
            "mas rapido",
            "mas pesado",
            "mas alto",
            "mas bajo",
        ]

        for pokemon_name in self.pokemon_names:
            if pokemon_name and pokemon_name in lowered:
                return "rag_question"

        for keyword in rag_keywords:
            if keyword in lowered:
                return "rag_question"

        general_pokemon_keywords = [
            "pokemon",
            "pokeball",
            "pokebola",
            "pokedex",
            "entrenador",
            "gimnasio",
            "medalla",
            "liga pokemon",
            "evolucion",
            "megaevolucion",
            "mega evolucion",
            "teracristal",
            "teracristalizacion",
            "dinamax",
            "gigamax",
            "inicial",
            "starter",
            "criador",
            "centro pokemon",
            "region",
            "kanto",
            "johto",
            "hoenn",
            "sinnoh",
            "teselia",
            "unova",
            "kalos",
            "alola",
            "galar",
            "paldea",
            "hisui",
            "movimiento",
            "movimientos",
            "ataque fisico",
            "ataque especial",
            "defensa especial",
            "naturaleza",
            "naturalezas",
            "iv",
            "ivs",
            "ev",
            "evs",
            "shiny",
            "variocolor",
            "debilidad",
            "debilidades",
            "resistencia",
            "resistencias",
            "inmunidad",
            "inmunidades",
            "estado alterado",
            "paralisis",
            "quemadura",
            "veneno",
            "sueno",
            "congelado",
            "legendario",
            "legendaria",
            "mitico",
            "mythical",
            "competitivo",
            "faiss",
            "rag",
        ]

        for keyword in general_pokemon_keywords:
            if keyword in lowered:
                return "general_question"

        return "unknown"

    def handle_general_question(self, question: str) -> AgentResponse:
        self.state.current_step = "general_answer"
        self.state.used_rag = False

        answer = self.answer_general_question(question)

        escalated = "te paso con un agente humano" in answer.lower()

        if escalated:
            self.state.current_step = "human_escalation"
            self.registrar_escalado(question)

        return AgentResponse(
            intent="human_escalation" if escalated else "general_question",
            message=answer,
            state=self.state,
        )

    def handle_rag_question(self, question: str) -> AgentResponse:
        self.state.current_step = "rag_answer"
        self.state.used_rag = True

        answer = self.call_rag(question)

        escalated = "te paso con un agente humano" in answer.lower()

        if escalated:
            self.state.current_step = "human_escalation"
            self.registrar_escalado(question)

        return AgentResponse(
            intent="human_escalation" if escalated else "rag_question",
            message=answer,
            state=self.state,
        )

    def registrar_escalado(self, pregunta: str) -> None:
        base_dir = Path(__file__).resolve().parent
        log_path = base_dir / "logs_escalado.txt"

        timestamp = datetime.now().isoformat(timespec="seconds")

        with open(log_path, "a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {pregunta}\n")

    def escalar_a_humano(self) -> AgentResponse:
        self.state.current_step = "human_escalation"
        self.state.used_rag = False

        pregunta = self.state.last_question or "Pregunta no disponible"
        self.registrar_escalado(pregunta)

        return AgentResponse(
            intent="human_escalation",
            message=(
                "No he podido resolver tu consulta con seguridad. "
                "Te paso con un agente humano."
            ),
            state=self.state,
        )

    def answer_general_question(self, question: str) -> str:
        lowered = self.normalize_text(question)

        if "ash" in lowered or "ash ketchum" in lowered:
            return (
                "Ash Ketchum es uno de los personajes principales del anime de Pokémon. "
                "Es un entrenador de Pueblo Paleta cuyo objetivo es convertirse en Maestro Pokémon. "
                "Su compañero más conocido es Pikachu."
            )

        if "profesor oak" in lowered:
            return (
                "El Profesor Oak es uno de los profesores Pokémon más conocidos. "
                "Aparece principalmente relacionado con la región de Kanto y ayuda a los entrenadores al inicio de su aventura."
            )

        if "team rocket" in lowered or "equipo rocket" in lowered:
            return (
                "El Team Rocket es una organización del universo Pokémon. "
                "En el anime, Jessie, James y Meowth intentan capturar Pokémon raros, especialmente el Pikachu de Ash."
            )

        if "misty" in lowered:
            return (
                "Misty es una entrenadora Pokémon especializada en Pokémon de tipo Agua. "
                "Es una de las compañeras más conocidas de Ash en el anime."
            )

        if "brock" in lowered:
            return (
                "Brock es un entrenador Pokémon especializado en tipo Roca. "
                "También es conocido por acompañar a Ash durante varias temporadas del anime."
            )

        if "serena" in lowered:
            return (
                "Serena es una entrenadora Pokémon de la región de Kalos. "
                "Aparece en el anime y participa en exhibiciones Pokémon."
            )

        if (
            "que puedes hacer" in lowered
            or "ayuda" in lowered
            or "help" in lowered
        ):
            return (
                "Soy un agente Pokémon. Puedo responder preguntas generales sobre el mundo Pokémon "
                "y consultar el dataset para datos concretos. Puedo hablar de tipos, habilidades, estadísticas, "
                "evolución, legendarios, regiones, combates, fortalezas y debilidades. También puedo buscar Pokémon "
                "por nombre o número, comparar Pokémon y estimar quién ganaría en una batalla simple."
            )

        if (
            "que es un pokemon" in lowered
            or "que son los pokemon" in lowered
            or lowered.strip() in ["pokemon", "pokémon"]
        ):
            return (
                "Un Pokémon es una criatura ficticia del universo Pokémon. "
                "Los entrenadores pueden capturarlos, entrenarlos y combatir con ellos. "
                "Cada Pokémon puede tener tipos, habilidades, estadísticas, movimientos y formas de evolución diferentes."
            )

        if "pokeball" in lowered or "pokebola" in lowered:
            return (
                "Una Poké Ball es un objeto usado por los entrenadores para capturar y guardar Pokémon. "
                "Existen diferentes tipos, como Poké Ball, Super Ball, Ultra Ball o Master Ball."
            )

        if "pokedex" in lowered:
            return (
                "La Pokédex es una enciclopedia digital que registra información sobre los Pokémon, "
                "como su número, nombre, tipo, descripción, hábitat o datos físicos."
            )

        if "entrenador" in lowered:
            return (
                "Un entrenador Pokémon es una persona que captura, entrena y combate con Pokémon. "
                "En los juegos, el objetivo suele ser mejorar el equipo, ganar medallas y completar la Pokédex."
            )

        if "gimnasio" in lowered or "medalla" in lowered:
            return (
                "Los gimnasios Pokémon son lugares donde los entrenadores desafían a líderes especializados. "
                "Al ganar, normalmente reciben una medalla."
            )

        if "liga pokemon" in lowered:
            return (
                "La Liga Pokémon es una competición donde los entrenadores más fuertes se enfrentan. "
                "Normalmente, para llegar a ella hay que vencer a líderes de gimnasio."
            )

        if "centro pokemon" in lowered:
            return (
                "Un Centro Pokémon es un lugar donde los entrenadores pueden curar a sus Pokémon. "
                "También suele funcionar como punto de apoyo durante la aventura."
            )

        if "tipo" in lowered or "tipos" in lowered:
            return (
                "Los tipos representan la naturaleza elemental de un Pokémon o movimiento, como Fire, Water, Grass, Electric o Dragon. "
                "Son importantes porque determinan fortalezas, debilidades, resistencias e inmunidades en combate."
            )

        if "debilidad" in lowered or "debilidades" in lowered:
            return (
                "Una debilidad significa que un Pokémon recibe más daño de ciertos tipos de movimientos. "
                "Por ejemplo, un Pokémon de tipo Fire suele ser débil frente a Water, Ground y Rock."
            )

        if "resistencia" in lowered or "resistencias" in lowered:
            return (
                "Una resistencia significa que un Pokémon recibe menos daño de ciertos tipos de movimientos. "
                "Las resistencias dependen del tipo o combinación de tipos del Pokémon."
            )

        if "inmunidad" in lowered or "inmunidades" in lowered:
            return (
                "Una inmunidad significa que un Pokémon no recibe daño de un tipo concreto de movimiento. "
                "Por ejemplo, los Pokémon de tipo Ghost son inmunes a movimientos de tipo Normal y Fighting."
            )

        if "habilidad" in lowered or "habilidades" in lowered:
            return (
                "Una habilidad es un efecto especial propio de un Pokémon. "
                "Puede influir en combate, modificar estadísticas, bloquear efectos o activar ventajas concretas."
            )

        if "movimiento" in lowered or "movimientos" in lowered:
            return (
                "Los movimientos son las acciones que usa un Pokémon en combate. "
                "Pueden causar daño, alterar estados, modificar estadísticas o aplicar efectos especiales."
            )

        if "estadistica" in lowered or "stats" in lowered:
            return (
                "Las estadísticas principales de un Pokémon son HP, Attack, Defense, Sp.Atk, Sp.Def y Speed. "
                "Sirven para medir su resistencia, daño físico, daño especial, defensa y rapidez."
            )

        if "hp" in lowered or "vida" in lowered:
            return (
                "HP son los puntos de salud de un Pokémon. "
                "Cuanto mayor sea el HP, más daño puede recibir antes de debilitarse."
            )

        if "ataque fisico" in lowered:
            return (
                "El ataque físico usa la estadística Attack del Pokémon atacante y la Defense del Pokémon defensor. "
                "Se aplica a movimientos físicos."
            )

        if "ataque especial" in lowered or "sp.atk" in lowered:
            return (
                "El ataque especial usa la estadística Sp.Atk del Pokémon atacante y la Sp.Def del defensor. "
                "Se aplica a movimientos especiales."
            )

        if "defensa especial" in lowered or "sp.def" in lowered:
            return (
                "La defensa especial mide cuánto resiste un Pokémon los movimientos especiales. "
                "Es diferente de la defensa física."
            )

        if "velocidad" in lowered or "speed" in lowered:
            return (
                "La velocidad determina normalmente qué Pokémon ataca primero en combate. "
                "Un Pokémon más rápido suele actuar antes que uno más lento."
            )

        if "evolucion" in lowered or "evoluciona" in lowered:
            return (
                "La evolución es el proceso por el que algunos Pokémon cambian a una forma más fuerte o distinta. "
                "Puede ocurrir por nivel, piedra evolutiva, intercambio, amistad u otras condiciones especiales."
            )

        if "megaevolucion" in lowered or "mega evolucion" in lowered:
            return (
                "La megaevolución es una transformación temporal que algunos Pokémon pueden usar en combate. "
                "Normalmente aumenta sus estadísticas y puede cambiar su tipo o habilidad."
            )

        if "dinamax" in lowered or "gigamax" in lowered:
            return (
                "Dinamax hace que un Pokémon aumente mucho de tamaño durante unos turnos. "
                "Gigamax es una variante especial que cambia la apariencia y permite movimientos exclusivos."
            )

        if "teracristal" in lowered or "teracristalizacion" in lowered:
            return (
                "La teracristalización permite a un Pokémon cambiar o potenciar su tipo durante el combate. "
                "Puede usarse de forma ofensiva o defensiva."
            )

        if "legendario" in lowered or "legendaria" in lowered:
            return (
                "Un Pokémon legendario suele ser raro, poderoso y relevante dentro de la historia del mundo Pokémon. "
                "Muchos tienen estadísticas altas y aparecen asociados a mitos, regiones o eventos importantes."
            )

        if "mitico" in lowered or "mythical" in lowered:
            return (
                "Un Pokémon mítico es una categoría especial de Pokémon extremadamente raros. "
                "Tradicionalmente suelen obtenerse mediante eventos especiales."
            )

        if "inicial" in lowered or "starter" in lowered:
            return (
                "Un Pokémon inicial es el primer compañero que el jugador suele elegir al comenzar la aventura. "
                "Normalmente hay tres opciones basadas en Grass, Fire y Water."
            )

        if "shiny" in lowered or "variocolor" in lowered:
            return (
                "Un Pokémon shiny o variocolor es una versión con colores diferentes a los normales. "
                "Son raros y muy buscados por coleccionistas."
            )

        if "naturaleza" in lowered or "naturalezas" in lowered:
            return (
                "La naturaleza de un Pokémon modifica sus estadísticas. "
                "Normalmente aumenta una estadística y reduce otra."
            )

        if "iv" in lowered or "ivs" in lowered:
            return (
                "Los IVs son valores individuales que influyen en el potencial máximo de las estadísticas de un Pokémon."
            )

        if "ev" in lowered or "evs" in lowered:
            return (
                "Los EVs son puntos de esfuerzo que permiten especializar las estadísticas de un Pokémon."
            )

        if (
            "estado alterado" in lowered
            or "paralisis" in lowered
            or "quemadura" in lowered
            or "veneno" in lowered
            or "sueno" in lowered
            or "congelado" in lowered
        ):
            return (
                "Los estados alterados son condiciones que afectan a un Pokémon en combate, "
                "como parálisis, quemadura, veneno, sueño o congelación."
            )

        if "kanto" in lowered:
            return "Kanto es la primera región principal de Pokémon."

        if "johto" in lowered:
            return "Johto es la región introducida en la segunda generación."

        if "hoenn" in lowered:
            return "Hoenn es la región de la tercera generación."

        if "sinnoh" in lowered:
            return "Sinnoh es la región de la cuarta generación."

        if "teselia" in lowered or "unova" in lowered:
            return "Teselia, también llamada Unova, es la región de la quinta generación."

        if "kalos" in lowered:
            return "Kalos es la región de la sexta generación."

        if "alola" in lowered:
            return "Alola es la región de la séptima generación."

        if "galar" in lowered:
            return "Galar es la región de la octava generación."

        if "paldea" in lowered:
            return "Paldea es la región de la novena generación, inspirada en la península ibérica."

        if "hisui" in lowered:
            return "Hisui es una versión antigua de la región de Sinnoh."

        if "competitivo" in lowered:
            return (
                "El competitivo Pokémon consiste en formar equipos optimizados para combatir contra otros jugadores. "
                "Se tienen en cuenta tipos, habilidades, movimientos, estadísticas, naturalezas, IVs, EVs y roles de equipo."
            )

        if "rag" in lowered or "faiss" in lowered:
            return (
                "En este proyecto, el RAG usa FAISS para recuperar información relevante del dataset de Pokémon. "
                "El agente decide cuándo consultar el dataset y cuándo responder una pregunta general."
            )

        if "como funciona" in lowered:
            return (
                "El sistema funciona en varias fases: primero el agente analiza la intención, luego preprocesa la pregunta, "
                "consulta el dataset o FAISS si hacen falta datos concretos, valida la respuesta y, si no puede responder con seguridad, "
                "escala la consulta a humano."
            )

        return (
            "No he podido resolver tu consulta con seguridad. "
            "Te paso con un agente humano."
        )

    def call_rag(self, question: str) -> str:
        from pipeline_pokemon import manejar_pregunta

        return manejar_pregunta(question)


def print_response(response: AgentResponse) -> None:
    print("\n--- RESPUESTA DEL AGENTE POKÉMON ---")
    print(f"Intención: {response.intent}")
    print(f"Mensaje: {response.message}")
    print(
        "Estado: "
        f"current_step={response.state.current_step!r}, "
        f"last_intent={response.state.last_intent!r}, "
        f"used_rag={response.state.used_rag!r}"
    )


def main() -> None:
    agent = PokemonAgent()
    print("Agente Pokémon. Escribe una pregunta, 'estado' o 'salir'.")

    while True:
        user_message = input("\nAlumno> ").strip()

        response = agent.run(user_message)
        print_response(response)

        if response.intent == "exit":
            break


if __name__ == "__main__":
    main()