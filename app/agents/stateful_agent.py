from __future__ import annotations

from typing import Any

from app.agents.code_generator import CodeGenerator
from app.agents.function_analyzer import FunctionAnalyzer
from app.agents.intent_classifier import IntentClassifier
from app.agents.lesson_planner import LessonPlanner
from app.services.state_service import StateService
from app.tools.base import ToolResult


class StatefulFlaskAgent:
    def __init__(self, llm_service=None):
        self.llm_service = llm_service
        self.function_analyzer = FunctionAnalyzer()
        self.intent_classifier = IntentClassifier(function_analyzer=self.function_analyzer)
        self.code_generator = CodeGenerator()
        self.lesson_planner = LessonPlanner()

    def run(self, user_id: str, message: str) -> ToolResult:
        message = (message or "").strip()
        if not message:
            return ToolResult(
                False,
                "input",
                "Debes enviar un mensaje.",
                error="empty_message",
                intent="unknown",
                next_action="Escribe una funcion Python, un comando como 'estado' o una pregunta.",
            )

        state = StateService.get_state(user_id)
        intent = self.intent_classifier.classify(message)

        if intent.type == "reset":
            StateService.reset_state(user_id)
            return ToolResult(
                ok=True,
                tool="reset_state",
                content="He reiniciado el estado del alumno. Ya puedes pegar nuevas funciones.",
                intent="reset",
                next_action="Pega una funcion Python para empezar.",
            )

        if intent.type == "show_state":
            return ToolResult(
                ok=True,
                tool="show_state",
                content="Estado actual recuperado.",
                data={"state": state},
                intent="show_state",
                next_action="Escribe 'siguiente' para avanzar o pega otra funcion.",
            )

        if intent.type == "next_step":
            return self._next_step(user_id, state)

        if intent.type == "python_function":
            detected = intent.data["functions"]
            new_names = []
            for analysis in detected:
                function_info = analysis.to_state_payload()
                name = function_info["name"]
                if name not in state["functions"]:
                    state["functions"][name] = StateService.default_function_state(
                        name=name,
                        source=function_info["source"],
                        parameters=function_info["parameters"],
                        docstring=function_info["docstring"],
                        return_annotation=function_info["return_annotation"],
                        signals=function_info["signals"],
                    )
                    state["function_order"].append(name)
                    new_names.append(name)

            if state["current_function"] is None and state["function_order"]:
                state["current_function"] = state["function_order"][0]
                state["global_step"] = "building"

            StateService.save_state(user_id, state)
            detected_names = [analysis.name for analysis in detected]
            concepts = ["function_analysis"]
            lesson = self.lesson_planner.lesson_for("analysis", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="detect_functions",
                content=(
                    f"{lesson}\n\n"
                    f"He detectado estas funciones: {', '.join(detected_names)}. "
                    f"Empezamos con '{state['current_function']}'. Escribe 'siguiente' para generar el service."
                ),
                data={"state": state, "new_functions": new_names},
                intent="python_function",
                step="analysis",
                concepts=concepts,
                next_action="Escribe 'siguiente' para generar el service.",
            )

        if intent.type == "interface_choice":
            return self._handle_interface_choice(user_id, state, intent.data["interface"])

        if intent.type == "flask_feature_request":
            return self._handle_flask_feature_request(user_id, state, intent.data["feature"])

        if intent.type == "concept_question":
            if self.llm_service is None:
                return ToolResult(
                    ok=False,
                    tool="llm",
                    content=(
                        "El LLM no esta configurado. Revisa LLM_ENABLED, LLM_PROVIDER, "
                        "LLM_BASE_URL y LLM_MODEL en el archivo .env."
                    ),
                    error="llm_not_configured",
                    data={"state": state},
                    intent="concept_question",
                    next_action="Configura el LLM o pregunta por el estado con 'estado'.",
                )

            prompt = self._build_prompt(message, state)
            answer = self.llm_service.ask(prompt)
            return ToolResult(
                ok=True,
                tool="llm",
                content=answer,
                data={"state": state},
                intent="concept_question",
                concepts=["llm_answer"],
                next_action="Puedes escribir 'siguiente', 'estado' o hacer otra pregunta.",
            )

        return ToolResult(
            ok=True,
            tool="help",
            content=(
                "Pega una o varias funciones Python, escribe 'siguiente' para avanzar, "
                "'estado' para ver el progreso o haz una pregunta como 'que es un blueprint?'."
            ),
            data={"state": state},
            intent="unknown",
            next_action="Pega una funcion Python, escribe 'siguiente' o haz una pregunta de Flask.",
        )

    def _build_prompt(self, message: str, state: dict[str, Any]) -> str:
        function_names = state.get("function_order", [])
        progress = {
            name: state["functions"][name]["steps"]
            for name in function_names
            if name in state.get("functions", {})
        }
        return f"""
Eres un tutor de programacion que ensena a convertir aplicaciones Python en aplicaciones web con Flask.

Contexto del alumno:
- Paso global: {state['global_step']}
- Funciones detectadas: {function_names}
- Funcion actual: {state['current_function']}
- Progreso por funcion: {progress}

Reglas:
- Responde en espanol.
- Se didactico y claro.
- Prioriza explicaciones breves y utiles.
- Limita la respuesta a 6 frases salvo que el alumno pida mas detalle.
- Si das codigo, que sea pequeno y conectado con Flask.
- No rehagas toda la aplicacion de golpe; ayuda por pasos.

Pregunta del alumno:
{message}
""".strip()

    def _handle_interface_choice(self, user_id: str, state: dict[str, Any], interface: str) -> ToolResult:
        current_fn = state.get("current_function")
        if not current_fn or current_fn not in state["functions"]:
            return ToolResult(
                ok=False,
                tool="interface_choice",
                content="Primero pega una funcion Python para poder elegir si la convertimos en formulario o API JSON.",
                error="no_function_detected",
                data={"state": state},
                intent="interface_choice",
                next_action="Pega una funcion Python y despues elige formulario o API JSON.",
            )

        state["functions"][current_fn]["interface"] = interface
        for step in ("route", "template", "registration"):
            state["functions"][current_fn]["steps"][step] = "pending"
        concepts = ["interface_choice"]
        lesson = self.lesson_planner.lesson_for("interface_choice", concepts, state)
        StateService.save_state(user_id, state)
        labels = {
            "form": "formulario HTML",
            "json_api": "API JSON",
            "both": "formulario HTML y API JSON",
        }
        mode_details = {
            "form": "Generare una ruta GET/POST y templates HTML.",
            "json_api": "Generare un endpoint POST que recibe JSON y devuelve JSON.",
            "both": "Generare una pagina con formulario y tambien un endpoint API JSON.",
        }
        return ToolResult(
            ok=True,
            tool="interface_choice",
            content=(
                f"{lesson}\n\n"
                f"He configurado '{current_fn}' para generarse como {labels.get(interface, interface)}. "
                f"{mode_details.get(interface, '')} "
                "Escribe 'siguiente' para generar el codigo con esa interfaz."
            ),
            data={"state": state},
            intent="interface_choice",
            concepts=concepts,
            next_action="Escribe 'siguiente' para generar el codigo con esa interfaz.",
        )

    def _handle_flask_feature_request(self, user_id: str, state: dict[str, Any], feature: str) -> ToolResult:
        current_fn = state.get("current_function")
        app_features = state["project"].setdefault("features", [])
        target = "project"
        if feature == "error_handlers":
            if feature not in app_features:
                app_features.append(feature)
            state["global_step"] = "integration"
        elif current_fn and current_fn in state["functions"]:
            function_state = state["functions"][current_fn]
            features = function_state.setdefault("features", [])
            if feature not in features:
                features.append(feature)
            for step in ("route", "template", "registration"):
                function_state["steps"][step] = "pending"
            target = current_fn
        else:
            return ToolResult(
                ok=False,
                tool="flask_feature_request",
                content="Primero pega una funcion Python para poder incorporar esa capacidad Flask.",
                error="no_function_detected",
                data={"state": state, "feature": feature},
                intent="flask_feature_request",
                concepts=[feature],
                next_action="Pega una funcion Python y vuelve a pedir la capacidad Flask.",
            )

        lesson = self.lesson_planner.lesson_for("flask_feature", [feature], state)
        artifacts = self._feature_preview_artifacts(feature, state, target)
        StateService.save_state(user_id, state)
        target_text = "la app" if target == "project" else f"'{target}'"
        artifact_text = (
            " He actualizado la vista de codigo con las piezas afectadas."
            if artifacts
            else ""
        )
        return ToolResult(
            ok=True,
            tool="flask_feature_request",
            content=(
                f"{lesson}\n\n"
                f"He incorporado la capacidad Flask '{feature}' al plan de {target_text}. "
                "Escribe 'siguiente' para confirmar/regenerar la siguiente pieza afectada."
                f"{artifact_text}"
            ),
            data={"state": state, "feature": feature, "artifacts": artifacts},
            intent="flask_feature_request",
            concepts=[feature],
            artifacts=artifacts,
            next_action="Escribe 'siguiente' para confirmar/regenerar codigo con esta capacidad.",
        )

    def _feature_preview_artifacts(self, feature: str, state: dict[str, Any], target: str) -> list[dict[str, Any]]:
        if target == "project":
            if feature == "error_handlers":
                return [self.code_generator.build_app_factory(state).to_dict()]
            return []

        function_state = state["functions"].get(target)
        if not function_state:
            return []

        artifacts = [self.code_generator.build_route(function_state).to_dict()]
        if feature in {"flash", "redirect", "sessions", "base_template", "static_files"}:
            artifacts.append(self.code_generator.build_template(function_state).to_dict())
        return artifacts

    def _next_step(self, user_id: str, state: dict[str, Any]) -> ToolResult:
        current_fn = state.get("current_function")

        if not current_fn or current_fn not in state["functions"]:
            return ToolResult(
                ok=False,
                tool="next_step",
                content="Todavia no tengo ninguna funcion. Pega primero una funcion Python.",
                error="no_function_detected",
                intent="next_step",
                next_action="Pega primero una funcion Python.",
            )

        function_state = state["functions"][current_fn]
        steps = function_state["steps"]

        if steps["service"] != "done":
            steps["service"] = "done"
            artifact = self.code_generator.build_service(function_state)
            concepts = ["service"]
            lesson = self.lesson_planner.lesson_for("service", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="build_service",
                content=self._with_lesson(lesson, artifact.content),
                data={"state": state, "artifacts": [artifact.to_dict()]},
                intent="next_step",
                step="service",
                artifacts=[artifact.to_dict()],
                concepts=concepts,
                next_action="Escribe 'siguiente' para generar la route.",
            )

        if steps["route"] != "done":
            steps["route"] = "done"
            artifact = self.code_generator.build_route(function_state)
            concepts = self._route_concepts(function_state)
            lesson = self.lesson_planner.lesson_for("route", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="build_route",
                content=self._with_lesson(lesson, artifact.content),
                data={"state": state, "artifacts": [artifact.to_dict()]},
                intent="next_step",
                step="route",
                artifacts=[artifact.to_dict()],
                concepts=concepts,
                next_action="Escribe 'siguiente' para generar el template.",
            )

        if steps["template"] != "done":
            steps["template"] = "done"
            artifact = self.code_generator.build_template(function_state)
            concepts = self._template_concepts(function_state)
            lesson = self.lesson_planner.lesson_for("template", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="build_template",
                content=self._with_lesson(lesson, artifact.content),
                data={"state": state, "artifacts": [artifact.to_dict()]},
                intent="next_step",
                step="template",
                artifacts=[artifact.to_dict()],
                concepts=concepts,
                next_action="Escribe 'siguiente' para continuar con la siguiente funcion o integrar la app.",
            )

        if "tests" in function_state.get("features", []) and steps.get("tests") != "done":
            steps["tests"] = "done"
            artifact = self.code_generator.build_tests(function_state)
            concepts = ["tests"]
            lesson = self.lesson_planner.lesson_for("tests", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="build_tests",
                content=self._with_lesson(lesson, artifact.content),
                data={"state": state, "artifacts": [artifact.to_dict()]},
                intent="next_step",
                step="tests",
                artifacts=[artifact.to_dict()],
                concepts=concepts,
                next_action="Escribe 'siguiente' para continuar con la siguiente funcion o integrar la app.",
            )

        next_fn = self._move_to_next_function(state)
        if next_fn is not None:
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="switch_function",
                content=(
                    f"La funcion '{current_fn}' ya tiene service, route y template. "
                    f"Ahora trabajamos con '{next_fn}'. Escribe 'siguiente'."
                ),
                data={"state": state},
                intent="next_step",
                step="switch_function",
                next_action="Escribe 'siguiente' para generar el service de la nueva funcion.",
            )

        if state["global_step"] != "integration_done":
            state["global_step"] = "integration_done"
            for fn in state["function_order"]:
                state["functions"][fn]["steps"]["registration"] = "done"
            artifact = self.code_generator.build_app_factory(state)
            concepts = ["app_factory", "blueprint_registration"]
            lesson = self.lesson_planner.lesson_for("app_factory", concepts, state)
            StateService.save_state(user_id, state)
            return ToolResult(
                ok=True,
                tool="build_app_factory",
                content=self._with_lesson(lesson, artifact.content),
                data={"state": state, "artifacts": [artifact.to_dict()]},
                intent="next_step",
                step="app_factory",
                artifacts=[artifact.to_dict()],
                concepts=concepts,
                next_action="Puedes hacer preguntas, revisar 'estado' o reiniciar con 'reset'.",
            )

        return ToolResult(
            ok=True,
            tool="done",
            content="Ya has generado todas las piezas basicas. Puedes hacer preguntas o reiniciar el estado con 'reset'.",
            data={"state": state},
            intent="next_step",
            step="done",
            next_action="Haz una pregunta o reinicia con 'reset'.",
        )

    def _move_to_next_function(self, state: dict[str, Any]) -> str | None:
        for fn in state["function_order"]:
            steps = state["functions"][fn]["steps"]
            required_steps = ["service", "route", "template"]
            if "tests" in state["functions"][fn].get("features", []):
                required_steps.append("tests")
            if any(steps[step] != "done" for step in required_steps):
                state["current_function"] = fn
                return fn

        state["current_function"] = None
        state["global_step"] = "integration"
        return None

    def _route_concepts(self, function_state: dict[str, Any]) -> list[str]:
        interface = function_state.get("interface", "form")
        concepts = ["route", "blueprint"]
        if interface in {"form", "both"}:
            concepts.extend(["request.form", "render_template"])
        if interface in {"json_api", "both"}:
            concepts.extend(["request.get_json", "jsonify"])
        for feature in function_state.get("features", []):
            if feature in {"flash", "redirect", "sessions"}:
                concepts.append(feature)
        return concepts

    def _template_concepts(self, function_state: dict[str, Any]) -> list[str]:
        interface = function_state.get("interface", "form")
        if interface == "json_api":
            return ["api_info"]
        concepts = ["template", "render_template"]
        for feature in function_state.get("features", []):
            if feature in {"flash", "base_template", "static_files"}:
                concepts.append(feature)
        return concepts

    def _with_lesson(self, lesson: str, content: str) -> str:
        if not lesson:
            return content
        return f"{lesson}\n\n{content}"
