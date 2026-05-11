from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.agents.function_analyzer import FunctionAnalyzer


@dataclass
class Intent:
    type: str
    confidence: float = 1.0
    data: dict[str, Any] = field(default_factory=dict)


class IntentClassifier:
    def __init__(self, function_analyzer: FunctionAnalyzer | None = None):
        self.function_analyzer = function_analyzer or FunctionAnalyzer()

    def classify(self, message: str) -> Intent:
        message = (message or "").strip()
        lowered = message.lower()

        if lowered in {"reset", "reiniciar"}:
            return Intent("reset")

        if lowered == "estado":
            return Intent("show_state")

        if lowered == "siguiente":
            return Intent("next_step")

        functions = self.function_analyzer.analyze(message)
        if functions:
            return Intent("python_function", data={"functions": functions})

        interface = self._interface_choice(lowered)
        if interface is not None:
            return Intent("interface_choice", data={"interface": interface})

        feature = self._flask_feature(lowered)
        if feature is not None:
            return Intent("flask_feature_request", data={"feature": feature})

        if self._is_question(message):
            return Intent("concept_question")

        return Intent("unknown", confidence=0.5)

    def _interface_choice(self, lowered: str) -> str | None:
        if any(term in lowered for term in ["ambas", "ambos", "formulario y api", "api y formulario"]):
            return "both"

        if any(term in lowered for term in ["api json", "como api", "hazlo api", "json", "request.get_json"]):
            return "json_api"

        if any(term in lowered for term in ["formulario", "form", "request.form", "html"]):
            return "form"

        return None

    def _flask_feature(self, lowered: str) -> str | None:
        features = {
            "flash": ["flash", "mensaje temporal", "mensajes temporales"],
            "redirect": ["redirect", "redireccion", "redirigir"],
            "sessions": ["session", "sesion", "sesiones"],
            "static_files": ["static", "archivo estatico", "css", "javascript"],
            "base_template": ["base template", "template base", "layout"],
            "error_handlers": ["error handler", "manejador de errores", "404", "500"],
            "tests": ["test", "pytest", "prueba automatica"],
        }

        for feature, terms in features.items():
            if any(term in lowered for term in terms):
                return feature

        return None

    def _is_question(self, message: str) -> bool:
        lowered = message.lower()
        keywords = [
            "que ",
            "por que",
            "porque",
            "como ",
            "explica",
            "duda",
            "ayuda",
            "ejemplo",
            "blueprint",
            "request.form",
            "request.get_json",
            "template",
            "flask",
        ]
        return message.endswith("?") or any(keyword in lowered for keyword in keywords)
