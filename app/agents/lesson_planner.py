from __future__ import annotations

from typing import Any


class LessonPlanner:
    def lesson_for(self, step: str, concepts: list[str], state: dict[str, Any]) -> str:
        new_concepts = self.mark_explained(state, concepts)
        if not new_concepts:
            return self._short_step_intro(step)

        explanations = [self._explain(concept) for concept in new_concepts]
        return "\n".join(explanation for explanation in explanations if explanation)

    def mark_explained(self, state: dict[str, Any], concepts: list[str]) -> list[str]:
        learning = state.setdefault("learning", {})
        explained = learning.setdefault("explained", [])
        new_concepts = []

        for concept in concepts:
            if concept not in explained:
                explained.append(concept)
                new_concepts.append(concept)

        return new_concepts

    def _short_step_intro(self, step: str) -> str:
        intros = {
            "service": "Seguimos con la capa de service.",
            "route": "Seguimos conectando la funcion con Flask.",
            "template": "Seguimos con la parte visual.",
            "app_factory": "Ahora integramos las rutas en la aplicacion.",
            "tests": "Ahora agregamos una prueba basica.",
        }
        return intros.get(step, "")

    def _explain(self, concept: str) -> str:
        explanations = {
            "function_analysis": (
                "Primero analizo la funcion Python: nombre, parametros, valores por defecto y senales utiles. "
                "Ese analisis permite generar codigo Flask adaptado en vez de usar una plantilla fija."
            ),
            "service": (
                "Un service contiene la logica Python pura. "
                "Lo separamos de Flask para que la funcion siga siendo facil de probar y reutilizar."
            ),
            "route": (
                "Una route conecta una URL con una funcion Python de Flask. "
                "Aqui decidimos que ocurre cuando el navegador o una API llama a esa URL."
            ),
            "blueprint": (
                "Un blueprint agrupa rutas relacionadas. "
                "Esto evita poner toda la aplicacion en un unico archivo a medida que crece."
            ),
            "request.form": (
                "request.form contiene los datos enviados por un formulario HTML con metodo POST. "
                "Lo usamos cuando el alumno quiere una pagina web con campos de entrada."
            ),
            "request.get_json": (
                "request.get_json lee el cuerpo JSON de una peticion. "
                "Lo usamos cuando la funcionalidad se expone como API."
            ),
            "jsonify": (
                "jsonify convierte un diccionario Python en una respuesta JSON valida para una API Flask."
            ),
            "template": (
                "Un template es un archivo HTML que Flask renderiza. "
                "Sirve para separar la presentacion de la logica Python."
            ),
            "render_template": (
                "render_template carga un template HTML y le pasa datos como result=result."
            ),
            "app_factory": (
                "La app factory crea y configura la aplicacion Flask. "
                "Es una estructura limpia para registrar blueprints y preparar configuracion."
            ),
            "blueprint_registration": (
                "Registrar un blueprint significa decirle a Flask que esas rutas forman parte de la aplicacion."
            ),
            "interface_choice": (
                "La interfaz define como se usara la funcion: formulario HTML, API JSON o ambas. "
                "Guardar esa decision permite generar rutas y templates coherentes."
            ),
            "api_info": (
                "Como esta funcionalidad se expone como API JSON, no hace falta un formulario HTML. "
                "Genero una pagina informativa para recordar la URL que debe consumir el cliente."
            ),
            "flash": "flash permite mostrar mensajes temporales al usuario despues de una accion.",
            "redirect": "redirect envia al usuario a otra URL despues de completar una accion.",
            "sessions": "session permite guardar datos sencillos entre peticiones del mismo usuario.",
            "static_files": "static files permite servir CSS, JavaScript o imagenes desde la carpeta static.",
            "base_template": "un template base permite compartir estructura HTML entre varias paginas.",
            "error_handlers": "los error handlers personalizan respuestas para errores como 404 o 500.",
            "tests": "una prueba automatica comprueba que la funcionalidad responde sin romperse.",
        }
        return explanations.get(concept, "")
