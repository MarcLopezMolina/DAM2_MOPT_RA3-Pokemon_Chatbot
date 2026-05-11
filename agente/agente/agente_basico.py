from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Artifact:
    kind: str
    path: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "kind": self.kind,
            "path": self.path,
            "content": self.content,
        }


@dataclass
class AgentState:
    function_name: str | None = None
    function_source: str | None = None
    current_step: str = "waiting_for_function"
    artifacts: list[Artifact] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "function_name": self.function_name,
            "function_source": self.function_source,
            "current_step": self.current_step,
            "artifacts": [artifact.to_dict() for artifact in self.artifacts],
        }


@dataclass
class AgentResponse:
    intent: str
    message: str
    state: AgentState
    artifact: Artifact | None = None

    def to_dict(self) -> dict:
        return {
            "intent": self.intent,
            "message": self.message,
            "state": self.state.to_dict(),
            "artifact": self.artifact.to_dict() if self.artifact else None,
        }


class BasicAgent:
    def __init__(self) -> None:
        self.state = AgentState()

    def run(self, user_message: str) -> AgentResponse:
        intent = self.analyze_intent(user_message)

        if intent == "python_function":
            return self.handle_python_function(user_message)

        if intent == "next_step":
            return self.handle_next_step()

        if intent == "show_state":
            return AgentResponse(
                intent=intent,
                message="Este es el estado actual del agente.",
                state=self.state,
            )

        return AgentResponse(
            intent=intent,
            message="No he entendido la accion. Pega una funcion Python o escribe 'siguiente'.",
            state=self.state,
        )

    def analyze_intent(self, user_message: str) -> str:
        text = user_message.strip()
        lowered = text.lower()

        if lowered == "siguiente":
            return "next_step"

        if lowered == "estado":
            return "show_state"

        if text.startswith("def ") and "(" in text and "):" in text:
            return "python_function"

        return "unknown"

    def handle_python_function(self, source: str) -> AgentResponse:
        name = self.extract_function_name(source)
        self.state.function_name = name
        self.state.function_source = source
        self.state.current_step = "analysis_done"

        artifact = Artifact(
            kind="analysis",
            path="memory/function_analysis.txt",
            content=f"Funcion detectada: {name}",
        )
        self.state.artifacts.append(artifact)

        return AgentResponse(
            intent="python_function",
            message=f"He analizado la funcion '{name}'. Escribe 'siguiente' para generar el service.",
            state=self.state,
            artifact=artifact,
        )

    def handle_next_step(self) -> AgentResponse:
        if self.state.function_name is None:
            return AgentResponse(
                intent="next_step",
                message="Antes necesito una funcion Python.",
                state=self.state,
            )

        if self.state.current_step == "analysis_done":
            return self.build_service()

        return AgentResponse(
            intent="next_step",
            message="No hay mas pasos en esta demo.",
            state=self.state,
        )

    def build_service(self) -> AgentResponse:
        name = self.state.function_name
        self.state.current_step = "service_done"

        artifact = Artifact(
            kind="service",
            path=f"app/services/{name}_service.py",
            content=(
                f"def run_{name}(*args, **kwargs):\n"
                f"    # Aqui iria la llamada controlada a {name}\n"
                f"    return {name}(*args, **kwargs)\n"
            ),
        )
        self.state.artifacts.append(artifact)

        return AgentResponse(
            intent="next_step",
            message=f"He generado un artefacto service para '{name}'.",
            state=self.state,
            artifact=artifact,
        )

    def extract_function_name(self, source: str) -> str:
        header = source.strip().splitlines()[0]
        return header.removeprefix("def ").split("(", 1)[0].strip()


def print_response(response: AgentResponse) -> None:
    print("\n--- RESPUESTA DEL AGENTE ---")
    print(f"Intencion: {response.intent}")
    print(f"Mensaje: {response.message}")
    print(
        "Estado: "
        f"function_name={response.state.function_name!r}, "
        f"current_step={response.state.current_step!r}, "
        f"artifacts={len(response.state.artifacts)}"
    )

    if response.artifact:
        print("\nArtefacto:")
        print(f"- kind: {response.artifact.kind}")
        print(f"- path: {response.artifact.path}")
        print("- content:")
        print(response.artifact.content)


def main() -> None:
    agent = BasicAgent()
    print("Agente basico. Pega una funcion Python, escribe 'siguiente', 'estado' o 'salir'.")

    while True:
        user_message = input("\nAlumno> ").strip()
        if user_message.lower() == "salir":
            break

        response = agent.run(user_message)
        print_response(response)


if __name__ == "__main__":
    main()
