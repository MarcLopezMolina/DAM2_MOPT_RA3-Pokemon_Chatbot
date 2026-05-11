from __future__ import annotations

from dataclasses import dataclass
from textwrap import dedent
from typing import Any


@dataclass
class CodeArtifact:
    path: str
    language: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {
            "path": self.path,
            "language": self.language,
            "content": self.content,
        }


class CodeGenerator:
    def build_service(self, function_state: dict[str, Any]) -> CodeArtifact:
        name = function_state["name"]
        source = (function_state.get("source") or "").strip()
        if not source:
            source = self._fallback_function_source(function_state)

        return CodeArtifact(
            path=f"app/services/{name}_service.py",
            language="python",
            content=f"# app/services/{name}_service.py\n\n{source}\n",
        )

    def build_route(self, function_state: dict[str, Any]) -> CodeArtifact:
        interface = function_state.get("interface", "form")
        if interface == "json_api":
            return self._build_json_route(function_state)
        if interface == "both":
            return self._build_combined_route(function_state)
        return self._build_form_route(function_state)

    def build_template(self, function_state: dict[str, Any]) -> CodeArtifact:
        interface = function_state.get("interface", "form")
        name = function_state["name"]
        if interface == "json_api":
            content = dedent(
                f"""
                <!-- templates/{name}_api_info.html -->
                <h1>{name.capitalize()} API</h1>
                <p>Esta funcionalidad se consume enviando JSON a <code>/{name}/api</code>.</p>
                """
            ).strip()
            return CodeArtifact(path=f"templates/{name}_api_info.html", language="html", content=f"{content}\n")

        form_template = self._form_template(function_state)
        result_template = self._result_template(function_state)
        return CodeArtifact(
            path=f"templates/{name}_form.html + templates/{name}_result.html",
            language="html",
            content=f"{form_template}\n\n{result_template}\n{self._supporting_template_artifacts(function_state)}",
        )

    def build_app_factory(self, state: dict[str, Any]) -> CodeArtifact:
        function_names = state["function_order"]
        project_features = set(state.get("project", {}).get("features", []))
        function_features = {
            feature
            for name in function_names
            for feature in state.get("functions", {}).get(name, {}).get("features", [])
        }
        needs_secret = bool(function_features.intersection({"flash", "sessions"}))
        imports = "\n".join([f"    from app.routes.{fn}_routes import bp as {fn}_bp" for fn in function_names])
        registers = "\n".join([f"    app.register_blueprint({fn}_bp)" for fn in function_names])
        secret_config = '    app.config.setdefault("SECRET_KEY", "dev")\n' if needs_secret else ""
        error_handlers = self._error_handlers() if "error_handlers" in project_features else ""
        content = f"""# app/__init__.py
from flask import Flask, jsonify

def create_app():
    app = Flask(__name__)
{secret_config}

{imports}

{registers}
{error_handlers}

    return app
"""
        return CodeArtifact(path="app/__init__.py", language="python", content=content)

    def build_tests(self, function_state: dict[str, Any]) -> CodeArtifact:
        name = function_state["name"]
        interface = function_state.get("interface", "form")
        params = self._callable_parameters(function_state)
        sample_payload = self._sample_payload(params)
        tests = [self._service_test(function_state)]
        if interface in {"json_api", "both"}:
            tests.append(self._api_test(name, sample_payload))
        if interface in {"form", "both"}:
            tests.append(self._form_test(name, sample_payload))
        content = "\n\n".join(tests)
        return CodeArtifact(path=f"tests/test_{name}.py", language="python", content=f"{content}\n")

    def _build_form_route(self, function_state: dict[str, Any]) -> CodeArtifact:
        name = function_state["name"]
        features = set(function_state.get("features", []))
        params = self._callable_parameters(function_state)
        assignments = self._form_assignments(function_state)
        call_args = ", ".join(param["name"] for param in params)
        required_fields = self._required_fields(params)
        imports = self._route_imports("form", features)
        success_lines = self._form_success_lines(name, features)

        if assignments:
            post_body = (
                f"missing = _missing_form_fields(request.form, REQUIRED_FIELDS)\n"
                f"        if missing:\n"
                f"            return render_template(\"{name}_form.html\", error=f\"Faltan campos: {{', '.join(missing)}}\")\n"
                f"        {assignments}\n"
                f"        result = {name}({call_args})\n"
                f"        {success_lines}"
            )
        else:
            post_body = f"result = {name}()\n        {success_lines}"

        content = f"""# app/routes/{name}_routes.py

from flask import {imports}
from app.services.{name}_service import {name}

bp = Blueprint("{name}", __name__, url_prefix="/{name}")
REQUIRED_FIELDS = {required_fields!r}

@bp.route("/", methods=["GET", "POST"])
def {name}_view():
    if request.method == "POST":
        {post_body}

    return render_template("{name}_form.html")
{self._result_route(name, features)}

def _missing_form_fields(form, required_fields):
    return [field for field in required_fields if not form.get(field)]
"""
        return CodeArtifact(path=f"app/routes/{name}_routes.py", language="python", content=content)

    def _build_json_route(self, function_state: dict[str, Any]) -> CodeArtifact:
        name = function_state["name"]
        features = set(function_state.get("features", []))
        params = self._callable_parameters(function_state)
        assignments = self._json_assignments(function_state)
        call_args = ", ".join(param["name"] for param in params)
        required_fields = self._required_fields(params)

        if assignments:
            post_body = (
                f"data = request.get_json(silent=True) or {{}}\n"
                f"    missing = _missing_json_fields(data, REQUIRED_FIELDS)\n"
                f"    if missing:\n"
                f"        return jsonify({{\"error\": \"missing_fields\", \"fields\": missing}}), 400\n"
                f"    {assignments}\n"
                f"    result = {name}({call_args})"
            )
        else:
            post_body = f"result = {name}()"

        content = f"""# app/routes/{name}_routes.py

from flask import Blueprint, jsonify, request
from app.services.{name}_service import {name}

bp = Blueprint("{name}", __name__, url_prefix="/{name}")
REQUIRED_FIELDS = {required_fields!r}

@bp.route("/api", methods=["POST"])
def {name}_api():
    {post_body}
    return jsonify({{"result": result}})

def _missing_json_fields(data, required_fields):
    return [field for field in required_fields if data.get(field) is None]
"""
        return CodeArtifact(path=f"app/routes/{name}_routes.py", language="python", content=content)

    def _build_combined_route(self, function_state: dict[str, Any]) -> CodeArtifact:
        name = function_state["name"]
        features = set(function_state.get("features", []))
        params = self._callable_parameters(function_state)
        form_assignments = self._form_assignments(function_state)
        json_assignments = self._json_assignments(function_state)
        call_args = ", ".join(param["name"] for param in params)
        required_fields = self._required_fields(params)
        imports = self._route_imports("both", features)
        success_lines = self._form_success_lines(name, features)

        form_body = (
            f"missing = _missing_form_fields(request.form, REQUIRED_FIELDS)\n"
            f"        if missing:\n"
            f"            return render_template(\"{name}_form.html\", error=f\"Faltan campos: {{', '.join(missing)}}\")\n"
            f"        {form_assignments}\n"
            f"        result = {name}({call_args})\n"
            f"        {success_lines}"
            if form_assignments
            else f"result = {name}()\n        {success_lines}"
        )
        json_body = (
            f"data = request.get_json(silent=True) or {{}}\n"
            f"    missing = _missing_json_fields(data, REQUIRED_FIELDS)\n"
            f"    if missing:\n"
            f"        return jsonify({{\"error\": \"missing_fields\", \"fields\": missing}}), 400\n"
            f"    {json_assignments}\n"
            f"    result = {name}({call_args})"
            if json_assignments
            else f"result = {name}()"
        )

        content = f"""# app/routes/{name}_routes.py

from flask import {imports}
from app.services.{name}_service import {name}

bp = Blueprint("{name}", __name__, url_prefix="/{name}")
REQUIRED_FIELDS = {required_fields!r}

@bp.route("/", methods=["GET", "POST"])
def {name}_view():
    if request.method == "POST":
        {form_body}

    return render_template("{name}_form.html")
{self._result_route(name, features)}

@bp.route("/api", methods=["POST"])
def {name}_api():
    {json_body}
    return jsonify({{"result": result}})

def _missing_form_fields(form, required_fields):
    return [field for field in required_fields if not form.get(field)]

def _missing_json_fields(data, required_fields):
    return [field for field in required_fields if data.get(field) is None]
"""
        return CodeArtifact(path=f"app/routes/{name}_routes.py", language="python", content=content)

    def _form_assignments(self, function_state: dict[str, Any]) -> str:
        lines = []
        for param in self._callable_parameters(function_state):
            name = param["name"]
            raw = self._form_raw_value(param)
            lines.append(f"{name} = {self._conversion_expr(raw, param, function_state)}")
        return "\n        ".join(lines)

    def _json_assignments(self, function_state: dict[str, Any]) -> str:
        lines = []
        for param in self._callable_parameters(function_state):
            name = param["name"]
            raw = self._json_raw_value(param)
            lines.append(f"{name} = {self._conversion_expr(raw, param, function_state)}")
        return "\n    ".join(lines)

    def _form_raw_value(self, param: dict[str, Any]) -> str:
        name = param["name"]
        default = param.get("default")
        if default is not None:
            return f'request.form.get("{name}", {default})'
        return f'request.form["{name}"]'

    def _json_raw_value(self, param: dict[str, Any]) -> str:
        name = param["name"]
        default = param.get("default")
        if default is not None:
            return f'data.get("{name}", {default})'
        return f'data.get("{name}")'

    def _conversion_expr(self, raw: str, param: dict[str, Any], function_state: dict[str, Any]) -> str:
        annotation = (param.get("annotation") or "").lower()
        default = param.get("default")

        if annotation in {"int", "builtins.int"}:
            return f"int({raw})"
        if annotation in {"float", "builtins.float"}:
            return f"float({raw})"
        if annotation in {"bool", "builtins.bool"}:
            return f"{raw} in ('1', 'true', 'True', 'on', True)"

        if default is not None:
            if default.replace(".", "", 1).isdigit():
                return f"float({raw})" if "." in default else f"int({raw})"
            if default in {"True", "False"}:
                return f"{raw} in ('1', 'true', 'True', 'on', True)"

        signals = set(function_state.get("signals", []))
        if "may_divide" in signals or "returns_expression" in signals:
            return f"float({raw})"

        return raw

    def _required_fields(self, params: list[dict[str, Any]]) -> list[str]:
        return [param["name"] for param in params if param.get("default") is None]

    def _callable_parameters(self, function_state: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            param
            for param in function_state.get("parameters", [])
            if param.get("kind") in {None, "positional", "keyword_only"}
        ]

    def _form_template(self, function_state: dict[str, Any]) -> str:
        name = function_state["name"]
        features = set(function_state.get("features", []))
        params = self._callable_parameters(function_state)
        inputs = "\n".join(self._input_for_param(param, function_state) for param in params)
        if not inputs:
            inputs = "    <p>Esta funcion no necesita datos de entrada.</p>"

        body = f"""<!-- templates/{name}_form.html -->
<h1>{name.capitalize()}</h1>
{self._flash_block(features)}
{{% if error %}}<p>{{{{ error }}}}</p>{{% endif %}}
<form method="post">
{inputs}
    <button type="submit">Calcular</button>
</form>"""
        return self._wrap_with_base(function_state, body)

    def _result_template(self, function_state: dict[str, Any]) -> str:
        name = function_state["name"]
        features = set(function_state.get("features", []))
        body = f"""<!-- templates/{name}_result.html -->
<h1>Resultado</h1>
{self._flash_block(features)}
<p>{{{{ result }}}}</p>
<a href="/{name}/">Volver</a>"""
        return self._wrap_with_base(function_state, body)

    def _input_for_param(self, param: dict[str, Any], function_state: dict[str, Any]) -> str:
        name = param["name"]
        annotation = (param.get("annotation") or "").lower()
        input_type = "text"
        step = ""

        if annotation in {"int", "builtins.int"}:
            input_type = "number"
        elif annotation in {"float", "builtins.float"}:
            input_type = "number"
            step = ' step="any"'
        elif "may_divide" in function_state.get("signals", []) or "returns_expression" in function_state.get("signals", []):
            input_type = "number"
            step = ' step="any"'

        value = ""
        if param.get("default") is not None:
            value = f' value="{param["default"].strip(chr(39)).strip(chr(34))}"'

        return f'    <input type="{input_type}"{step} name="{name}" placeholder="{name}"{value}>'

    def _route_imports(self, interface: str, features: set[str]) -> str:
        imports = ["Blueprint", "request"]
        if interface in {"json_api", "both"}:
            imports.append("jsonify")
        if interface in {"form", "both"}:
            imports.append("render_template")
        if features.intersection({"redirect", "sessions"}):
            imports.extend(["redirect", "url_for"])
        if "flash" in features:
            imports.append("flash")
        if "sessions" in features:
            imports.append("session")
        return ", ".join(dict.fromkeys(imports))

    def _form_success_lines(self, name: str, features: set[str]) -> str:
        lines = []
        if "sessions" in features:
            lines.append('session["last_result"] = result')
        if "flash" in features:
            lines.append('flash("Operacion completada.")')
        if "redirect" in features or "sessions" in features:
            if "sessions" in features:
                lines.append(f'return redirect(url_for(".{name}_result"))')
            else:
                lines.append(f'return redirect(url_for(".{name}_result", result=result))')
        else:
            lines.append(f'return render_template("{name}_result.html", result=result)')
        return "\n        ".join(lines)

    def _result_route(self, name: str, features: set[str]) -> str:
        if not features.intersection({"redirect", "sessions"}):
            return ""
        result_source = 'session.get("last_result")' if "sessions" in features else 'request.args.get("result")'
        return f"""

@bp.route("/result", methods=["GET"])
def {name}_result():
    result = {result_source}
    return render_template("{name}_result.html", result=result)
"""

    def _flash_block(self, features: set[str]) -> str:
        if "flash" not in features:
            return ""
        return """{% with messages = get_flashed_messages() %}
{% if messages %}
{% for message in messages %}<p>{{ message }}</p>{% endfor %}
{% endif %}
{% endwith %}"""

    def _wrap_with_base(self, function_state: dict[str, Any], body: str) -> str:
        features = set(function_state.get("features", []))
        if "base_template" not in features:
            if "static_files" in features:
                return f'<link rel="stylesheet" href="{{{{ url_for(\'static\', filename=\'style.css\') }}}}">\n{body}'
            return body
        return f"""{{% extends "base.html" %}}
{{% block content %}}
{body}
{{% endblock %}}"""

    def _supporting_template_artifacts(self, function_state: dict[str, Any]) -> str:
        features = set(function_state.get("features", []))
        sections = []
        if "base_template" in features:
            css_link = ""
            if "static_files" in features:
                css_link = '    <link rel="stylesheet" href="{{ url_for(\'static\', filename=\'style.css\') }}">\n'
            sections.append(
                f"""

<!-- templates/base.html -->
<!doctype html>
<html>
<head>
    <title>Flask Builder</title>
{css_link}</head>
<body>
{{% block content %}}{{% endblock %}}
</body>
</html>
""".rstrip()
            )
        if "static_files" in features:
            sections.append(
                """

/* static/style.css */
body {
    font-family: Arial, sans-serif;
    margin: 2rem;
}
input, button {
    margin: 0.25rem 0;
    display: block;
}
""".rstrip()
            )
        return "\n".join(sections) + ("\n" if sections else "")

    def _error_handlers(self) -> str:
        return """

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "not_found"}), 404

    @app.errorhandler(500)
    def server_error(error):
        return jsonify({"error": "server_error"}), 500
"""

    def _sample_payload(self, params: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {}
        for param in params:
            name = param["name"]
            annotation = (param.get("annotation") or "").lower()
            default = param.get("default")
            if default is not None:
                try:
                    payload[name] = int(default)
                except ValueError:
                    try:
                        payload[name] = float(default)
                    except ValueError:
                        payload[name] = default.strip("'\"")
            elif annotation in {"int", "builtins.int"}:
                payload[name] = 1
            elif annotation in {"float", "builtins.float"}:
                payload[name] = 1.0
            elif annotation in {"bool", "builtins.bool"}:
                payload[name] = True
            else:
                payload[name] = "test"
        return payload

    def _service_test(self, function_state: dict[str, Any]) -> str:
        name = function_state["name"]
        params = self._callable_parameters(function_state)
        args = ", ".join(repr(value) for value in self._sample_payload(params).values())
        return f"""from app.services.{name}_service import {name}

def test_{name}_service_runs():
    result = {name}({args})
    assert result is not None
"""

    def _api_test(self, name: str, sample_payload: dict[str, Any]) -> str:
        return f"""def test_{name}_api(client):
    response = client.post("/{name}/api", json={sample_payload!r})
    assert response.status_code == 200
    assert "result" in response.get_json()
"""

    def _form_test(self, name: str, sample_payload: dict[str, Any]) -> str:
        return f"""def test_{name}_form(client):
    response = client.post("/{name}/", data={sample_payload!r})
    assert response.status_code in {{200, 302}}
"""

    def _fallback_function_source(self, function_state: dict[str, Any]) -> str:
        name = function_state["name"]
        params = ", ".join(param["name"] for param in self._callable_parameters(function_state))
        return f"def {name}({params}):\n    pass"
