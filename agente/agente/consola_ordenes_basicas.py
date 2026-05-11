from __future__ import annotations

from agente.agente.agente_basico import BasicAgent, print_response


HELP = """
Ordenes disponibles:

  funcion     Pide pegar una funcion Python y la envia al agente.
  siguiente   Avanza al siguiente paso usando el estado actual.
  estado      Muestra el estado resumido del agente.
  artefactos  Lista los artefactos generados.
  reset       Reinicia el agente.
  ayuda       Muestra estas ordenes.
  salir       Cierra la consola.
"""


def main() -> None:
    agent = BasicAgent()
    print("Consola de ordenes basicas del agente.")
    print(HELP)

    while True:
        command = input("\nOrden> ").strip().lower()

        if command == "salir":
            break

        if command == "ayuda":
            print(HELP)
            continue

        if command == "reset":
            agent = BasicAgent()
            print("Estado reiniciado.")
            continue

        if command == "funcion":
            source = read_function()
            response = agent.run(source)
            print_response(response)
            continue

        if command == "siguiente":
            response = agent.run("siguiente")
            print_response(response)
            continue

        if command == "estado":
            print_state(agent)
            continue

        if command == "artefactos":
            print_artifacts(agent)
            continue

        print("Orden no reconocida. Escribe 'ayuda' para ver las ordenes disponibles.")


def read_function() -> str:
    print("Pega la funcion Python. Termina con una linea vacia.")
    lines: list[str] = []

    while True:
        line = input()
        if line == "":
            break
        lines.append(line)

    return "\n".join(lines)


def print_state(agent: BasicAgent) -> None:
    state = agent.state
    print("\n--- ESTADO ---")
    print(f"function_name: {state.function_name}")
    print(f"current_step: {state.current_step}")
    print(f"artifacts: {len(state.artifacts)}")


def print_artifacts(agent: BasicAgent) -> None:
    print("\n--- ARTEFACTOS ---")
    if not agent.state.artifacts:
        print("No hay artefactos generados.")
        return

    for index, artifact in enumerate(agent.state.artifacts, start=1):
        print(f"\n{index}. {artifact.kind}")
        print(f"path: {artifact.path}")
        print("content:")
        print(artifact.content)


if __name__ == "__main__":
    main()

