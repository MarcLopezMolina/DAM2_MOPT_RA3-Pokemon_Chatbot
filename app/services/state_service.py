from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.extensions import cache


class StateService:
    STATE_VERSION = 2

    @staticmethod
    def _default_state() -> dict[str, Any]:
        return {
            "version": StateService.STATE_VERSION,
            "project": {
                "name": "flask_builder_project",
                "structure_created": False,
                "blueprints_registered": [],
            },
            "functions": {},
            "function_order": [],
            "current_function": None,
            "global_step": "collecting",
            "learning": {
                "explained": [],
                "pending_concepts": [],
            },
        }

    @staticmethod
    def default_function_state(
        name: str,
        source: str = "",
        parameters: list[dict[str, Any]] | None = None,
        docstring: str | None = None,
        return_annotation: str | None = None,
        signals: list[str] | None = None,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "source": source,
            "parameters": parameters or [],
            "docstring": docstring,
            "return_annotation": return_annotation,
            "signals": signals or [],
            "return_type": "unknown",
            "description": "",
            "interface": "form",
            "features": [],
            "steps": {
                "analysis": "done",
                "service": "pending",
                "route": "pending",
                "template": "pending",
                "registration": "pending",
                "tests": "pending",
            },
        }

    @staticmethod
    def get_state(user_id: str) -> dict[str, Any]:
        state = cache.get(f"state:{user_id}")
        if state is None:
            state = StateService._default_state()
        else:
            state = StateService.normalize_state(state)

        cache.set(f"state:{user_id}", state)
        return state

    @staticmethod
    def save_state(user_id: str, state: dict[str, Any]) -> None:
        cache.set(f"state:{user_id}", StateService.normalize_state(state))

    @staticmethod
    def reset_state(user_id: str) -> dict[str, Any]:
        state = StateService._default_state()
        cache.set(f"state:{user_id}", state)
        return state

    @staticmethod
    def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
        normalized = StateService._default_state()

        normalized["project"].update(deepcopy(state.get("project", {})))
        normalized["current_function"] = state.get("current_function")
        normalized["global_step"] = state.get("global_step", normalized["global_step"])
        normalized["learning"].update(deepcopy(state.get("learning", {})))

        raw_functions = state.get("functions", {})
        raw_steps = state.get("steps", {})

        if isinstance(raw_functions, list):
            function_order = list(raw_functions)
            functions = {}
            for name in function_order:
                old_steps = raw_steps.get(name, [])
                functions[name] = StateService.default_function_state(name=name)
                StateService._apply_legacy_steps(functions[name], old_steps)
        elif isinstance(raw_functions, dict):
            functions = {}
            function_order = list(state.get("function_order") or raw_functions.keys())
            for name in function_order:
                raw_function = raw_functions.get(name, {})
                if not isinstance(raw_function, dict):
                    raw_function = {}

                function_state = StateService.default_function_state(
                    name=raw_function.get("name", name),
                    source=raw_function.get("source", ""),
                    parameters=deepcopy(raw_function.get("parameters", [])),
                    docstring=raw_function.get("docstring"),
                    return_annotation=raw_function.get("return_annotation"),
                    signals=deepcopy(raw_function.get("signals", [])),
                )
                function_state.update(
                    {
                        "return_type": raw_function.get("return_type", function_state["return_type"]),
                        "description": raw_function.get("description", function_state["description"]),
                        "interface": raw_function.get("interface", function_state["interface"]),
                        "features": deepcopy(raw_function.get("features", function_state["features"])),
                    }
                )

                raw_function_steps = raw_function.get("steps", {})
                if isinstance(raw_function_steps, dict):
                    function_state["steps"].update(raw_function_steps)
                else:
                    StateService._apply_legacy_steps(function_state, raw_function_steps)

                functions[name] = function_state
        else:
            functions = {}
            function_order = []

        normalized["functions"] = functions
        normalized["function_order"] = [name for name in function_order if name in functions]

        if normalized["current_function"] not in normalized["functions"]:
            normalized["current_function"] = normalized["function_order"][0] if normalized["function_order"] else None

        normalized["version"] = StateService.STATE_VERSION
        return normalized

    @staticmethod
    def _apply_legacy_steps(function_state: dict[str, Any], old_steps: list[str]) -> None:
        if not isinstance(old_steps, list):
            return

        for step in old_steps:
            if step in function_state["steps"]:
                function_state["steps"][step] = "done"
