from __future__ import annotations

from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = BASE_DIR / "data" / "dataSetFinal.xlsx"


class PokemonRAG:
    def __init__(self, excel_path: Path = EXCEL_PATH) -> None:
        self.excel_path = excel_path
        self.df = pd.read_excel(self.excel_path)
        self.df.columns = [str(column).strip() for column in self.df.columns]

    def answer(self, question: str) -> str:
        question_lower = question.lower()

        pokemon = self.find_pokemon_in_question(question_lower)

        if pokemon is not None:
            return self.answer_about_pokemon(question_lower, pokemon)

        return (
            "He consultado el dataset, pero no he encontrado un Pokémon concreto en la pregunta. "
            "Prueba con algo como: '¿Qué habilidades tiene Pecharunt?' o 'Dime los datos de Pikachu'."
        )

    def find_pokemon_in_question(self, question_lower: str):
        for _, row in self.df.iterrows():
            name = str(row.get("Name", "")).strip()

            if name and name.lower() in question_lower:
                return row

        return None

    def answer_about_pokemon(self, question_lower: str, pokemon) -> str:
        name = pokemon.get("Name", "Desconocido")

        if "habilidad" in question_lower or "habilidades" in question_lower:
            return (
                f"Las habilidades de {name} son: "
                f"{pokemon.get('Abilities', 'No disponible')}."
            )

        if "tipo" in question_lower or "tipos" in question_lower:
            type_1 = pokemon.get("Type 1", "No disponible")
            type_2 = pokemon.get("Type 2", "")

            if pd.isna(type_2) or str(type_2).strip() == "":
                return f"{name} es de tipo {type_1}."

            return f"{name} es de tipo {type_1} y {type_2}."

        if (
            "estadistica" in question_lower
            or "estadisticas" in question_lower
            or "estadística" in question_lower
            or "estadísticas" in question_lower
        ):
            return self.format_stats(pokemon)

        if "ataque" in question_lower:
            return f"El ataque de {name} es {pokemon.get('Attack', 'No disponible')}."

        if "defensa" in question_lower:
            return f"La defensa de {name} es {pokemon.get('Defense', 'No disponible')}."

        if "velocidad" in question_lower:
            return f"La velocidad de {name} es {pokemon.get('Speed', 'No disponible')}."

        if "hp" in question_lower or "vida" in question_lower:
            return f"El HP de {name} es {pokemon.get('HP', 'No disponible')}."

        if "generacion" in question_lower or "generación" in question_lower:
            return f"{name} pertenece a la generación {pokemon.get('Generation', 'No disponible')}."

        if "legendario" in question_lower or "legendaria" in question_lower:
            return f"Valor de Legendary para {name}: {pokemon.get('Legendary', 'No disponible')}."

        return self.format_full_pokemon(pokemon)

    def format_stats(self, pokemon) -> str:
        name = pokemon.get("Name", "Desconocido")

        return (
            f"Estadísticas de {name}:\n"
            f"- HP: {pokemon.get('HP', 'No disponible')}\n"
            f"- Attack: {pokemon.get('Attack', 'No disponible')}\n"
            f"- Defense: {pokemon.get('Defense', 'No disponible')}\n"
            f"- Sp. Atk: {pokemon.get('Sp. Atk', 'No disponible')}\n"
            f"- Sp. Def: {pokemon.get('Sp. Def', 'No disponible')}\n"
            f"- Speed: {pokemon.get('Speed', 'No disponible')}\n"
            f"- Total: {pokemon.get('Total', 'No disponible')}"
        )

    def format_full_pokemon(self, pokemon) -> str:
        name = pokemon.get("Name", "Desconocido")

        return (
            f"Datos de {name}:\n"
            f"- Número: {pokemon.get('#', 'No disponible')}\n"
            f"- Type 1: {pokemon.get('Type 1', 'No disponible')}\n"
            f"- Type 2: {pokemon.get('Type 2', 'No disponible')}\n"
            f"- Total: {pokemon.get('Total', 'No disponible')}\n"
            f"- HP: {pokemon.get('HP', 'No disponible')}\n"
            f"- Attack: {pokemon.get('Attack', 'No disponible')}\n"
            f"- Defense: {pokemon.get('Defense', 'No disponible')}\n"
            f"- Sp. Atk: {pokemon.get('Sp. Atk', 'No disponible')}\n"
            f"- Sp. Def: {pokemon.get('Sp. Def', 'No disponible')}\n"
            f"- Speed: {pokemon.get('Speed', 'No disponible')}\n"
            f"- Generation: {pokemon.get('Generation', 'No disponible')}\n"
            f"- Legendary: {pokemon.get('Legendary', 'No disponible')}\n"
            f"- Abilities: {pokemon.get('Abilities', 'No disponible')}"
        )


def consultar_rag_pokemon(question: str) -> str:
    rag = PokemonRAG()
    return rag.answer(question)


def main() -> None:
    rag = PokemonRAG()
    print("RAG Pokémon activo. Escribe una pregunta o 'salir'.")

    while True:
        question = input("\nPregunta> ").strip()

        if question.lower() == "salir":
            break

        answer = rag.answer(question)
        print("\nRespuesta:")
        print(answer)


if __name__ == "__main__":
    main()