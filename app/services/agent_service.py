from __future__ import annotations

from flask import current_app

from app.agents.stateful_agent import StatefulFlaskAgent
from app.llm.llm_service import LLMConfig, LLMService


class AgentService:
    def _build_agent(self) -> StatefulFlaskAgent:
        llm_service = None
        if current_app.config.get("LLM_ENABLED"):
            llm_service = LLMService(self._llm_config())
        return StatefulFlaskAgent(llm_service=llm_service)

    def process_message(self, user_id: str, message: str) -> dict:
        agent = self._build_agent()
        result = agent.run(user_id=user_id, message=message)
        return {
            "ok": result.ok,
            "intent": result.intent or result.tool,
            "tool": result.tool,
            "step": result.step,
            "reply": result.content,
            "artifacts": result.artifacts,
            "concepts": result.concepts,
            "next_action": result.next_action,
            "data": result.data,
            "error": result.error,
        }

    def llm_status(self) -> dict:
        if not current_app.config.get("LLM_ENABLED"):
            return {
                "ok": False,
                "enabled": False,
                "error": "LLM_ENABLED esta desactivado.",
            }

        llm_service = LLMService(self._llm_config())
        status = llm_service.status()
        status["enabled"] = True
        return status

    def _llm_config(self) -> LLMConfig:
        return LLMConfig(
            provider=current_app.config["LLM_PROVIDER"],
            api_key=current_app.config["LLM_API_KEY"],
            model=current_app.config["LLM_MODEL"],
            base_url=current_app.config["LLM_BASE_URL"],
            timeout=current_app.config["LLM_TIMEOUT"],
            max_tokens=current_app.config["LLM_MAX_TOKENS"],
        )
