from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

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

        names = df[name_column].dropna().astype(str).str.lower().tolist()
        names = sorted(names, key=len, reverse=True)

        return names

    def run(self, user_message: str) -> AgentResponse:
        intent = self.analyze_intent(user_message)

        self.state.last_question = user_message
        self.state.last_intent = intent

        if intent == "exit":
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

        return AgentResponse(
            intent=intent,
            message="No he entendido la pregunta. Pregúntame algo sobre Pokémon.",
            state=self.state,
        )

    def analyze_intent(self, user_message: str) -> str:
        text = user_message.strip()
        lowered = text.lower()

        if lowered in ["salir", "exit", "quit"]:
            return "exit"

        if lowered == "estado":
            return "show_state"
        
        if re.search(r"\b(pokemon|pokémon|id|numero|número)\s*\d+\b", lowered):
            return "rag_question"

        for pokemon_name in self.pokemon_names:
            if pokemon_name in lowered:
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
            "estadística",
            "estadísticas",
            "generacion",
            "generación",
            "legendario",
            "legendaria",
            "peso",
            "pesa",
            "altura",
            "mide",
            "color",
            "forma",
            "total",
            "datos",
            "dato",
            "información",
            "informacion",
            "info",
            "compara",
            "comparar",
            "cuál tiene",
            "cual tiene",
            "más fuerte",
            "mas fuerte",
            "más rápido",
            "mas rapido",
            "de que tipo",
            "de qué tipo",
            "cuánto pesa",
            "cuanto pesa",
        ]

        for keyword in rag_keywords:
            if keyword in lowered:
                return "rag_question"

        return "general_question"

    def handle_general_question(self, question: str) -> AgentResponse:
        self.state.current_step = "general_answer"
        self.state.used_rag = False

        answer = self.answer_general_question(question)

        return AgentResponse(
            intent="general_question",
            message=answer,
            state=self.state,
        )

    def handle_rag_question(self, question: str) -> AgentResponse:
        self.state.current_step = "rag_answer"
        self.state.used_rag = True

        answer = self.call_rag(question)

        return AgentResponse(
            intent="rag_question",
            message=answer,
            state=self.state,
        )

    def answer_general_question(self, question: str) -> str:
        lowered = question.lower()

        if "qué es un pokémon" in lowered or "que es un pokemon" in lowered:
            return (
                "Un Pokémon es una criatura ficticia del universo Pokémon. "
                "Cada Pokémon puede tener tipos, habilidades y estadísticas diferentes."
            )

        if "legendario" in lowered:
            return (
                "Un Pokémon legendario suele ser un Pokémon especial, raro y con gran importancia "
                "dentro del mundo Pokémon. Normalmente tiene estadísticas más altas que muchos Pokémon comunes."
            )

        if "habilidad" in lowered:
            return (
                "Una habilidad es una característica especial que puede afectar al combate. "
                "Por ejemplo, puede aumentar una estadística, evitar ciertos ataques o activar efectos concretos."
            )

        if "tipo" in lowered:
            return (
                "Los tipos indican la naturaleza de un Pokémon, como Fire, Water, Grass, Electric o Dragon. "
                "Los tipos influyen en las fortalezas y debilidades durante los combates."
            )

        return (
            "Puedo responder preguntas generales sobre Pokémon. "
            "Si me preguntas por datos concretos de un Pokémon, usaré el RAG con el dataset."
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