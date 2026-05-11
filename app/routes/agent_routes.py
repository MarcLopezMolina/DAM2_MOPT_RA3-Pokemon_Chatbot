from flask import Blueprint, jsonify, request

from app.services.agent_service import AgentService

agent_bp = Blueprint("agent", __name__)
agent_service = AgentService()


@agent_bp.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok", "message": "Stateful Flask Builder Agent activo"}), 200


@agent_bp.route("/llm/status", methods=["GET"])
def llm_status():
    status = agent_service.llm_status()
    http_status = 200 if status["ok"] else 503
    return jsonify(status), http_status


@agent_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_id = str(data.get("user_id", "default")).strip() or "default"
    message = str(data.get("message", "")).strip()

    if not message:
        return jsonify({"error": "El campo 'message' es obligatorio"}), 400

    result = agent_service.process_message(user_id=user_id, message=message)
    status = 200 if result["ok"] else 422
    return jsonify(result), status
