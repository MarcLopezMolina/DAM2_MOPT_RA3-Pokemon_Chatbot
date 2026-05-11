from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParameterInfo:
    name: str
    annotation: str | None = None
    default: str | None = None
    kind: str = "positional"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "annotation": self.annotation,
            "default": self.default,
            "kind": self.kind,
        }


@dataclass
class FunctionAnalysis:
    name: str
    source: str
    parameters: list[ParameterInfo] = field(default_factory=list)
    docstring: str | None = None
    return_annotation: str | None = None
    signals: list[str] = field(default_factory=list)

    def to_state_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source": self.source,
            "parameters": [parameter.to_dict() for parameter in self.parameters],
            "docstring": self.docstring,
            "return_annotation": self.return_annotation,
            "signals": list(self.signals),
        }


class FunctionAnalyzer:
    def analyze(self, source: str) -> list[FunctionAnalysis]:
        try:
            tree = ast.parse(source)
        except SyntaxError:
            return self._fallback_analyze(source)

        analyses = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef):
                continue

            analyses.append(
                FunctionAnalysis(
                    name=node.name,
                    source=ast.get_source_segment(source, node) or "",
                    parameters=self._parameters(node),
                    docstring=ast.get_docstring(node),
                    return_annotation=ast.unparse(node.returns) if node.returns else None,
                    signals=self._signals(node),
                )
            )

        return analyses

    def _fallback_analyze(self, source: str) -> list[FunctionAnalysis]:
        return [
            FunctionAnalysis(name=name, source=source)
            for name in re.findall(r"def\s+([A-Za-z_]\w*)\s*\(", source)
        ]

    def _parameters(self, node: ast.FunctionDef) -> list[ParameterInfo]:
        parameters = []

        positional_args = list(node.args.posonlyargs) + list(node.args.args)
        positional_defaults = [None] * (len(positional_args) - len(node.args.defaults)) + list(node.args.defaults)
        for arg, default in zip(positional_args, positional_defaults):
            parameters.append(self._parameter(arg, default, "positional"))

        if node.args.vararg:
            parameters.append(self._parameter(node.args.vararg, None, "vararg"))

        for arg, default in zip(node.args.kwonlyargs, node.args.kw_defaults):
            parameters.append(self._parameter(arg, default, "keyword_only"))

        if node.args.kwarg:
            parameters.append(self._parameter(node.args.kwarg, None, "kwarg"))

        return parameters

    def _parameter(self, arg: ast.arg, default: ast.expr | None, kind: str) -> ParameterInfo:
        return ParameterInfo(
            name=arg.arg,
            annotation=ast.unparse(arg.annotation) if arg.annotation else None,
            default=ast.unparse(default) if default is not None else None,
            kind=kind,
        )

    def _signals(self, node: ast.FunctionDef) -> list[str]:
        signals = set()

        for child in ast.walk(node):
            if isinstance(child, ast.BinOp) and isinstance(child.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                signals.add("may_divide")

            if isinstance(child, ast.Call):
                call_name = self._call_name(child.func)
                if call_name == "open" or call_name.endswith(".open"):
                    signals.add("uses_file_io")

            if isinstance(child, ast.Return) and child.value is not None:
                signals.add(f"returns_{self._return_signal(child.value)}")

        return sorted(signals)

    def _call_name(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id

        if isinstance(node, ast.Attribute):
            parent = self._call_name(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr

        return ""

    def _return_signal(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            if isinstance(node.value, bool):
                return "bool"
            if isinstance(node.value, (int, float, complex)):
                return "number"
            if isinstance(node.value, str):
                return "string"
            if node.value is None:
                return "none"

        if isinstance(node, ast.List):
            return "list"
        if isinstance(node, ast.Dict):
            return "dict"
        if isinstance(node, ast.Set):
            return "set"
        if isinstance(node, ast.Tuple):
            return "tuple"
        if isinstance(node, ast.Compare):
            return "bool"
        if isinstance(node, ast.JoinedStr):
            return "string"
        if isinstance(node, ast.BinOp):
            return "expression"

        return "unknown"
