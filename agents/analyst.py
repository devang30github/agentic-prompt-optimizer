"""
agents/analyst.py

Analyst Agent — first agent in the pipeline.
Takes raw user input and converts it into a structured PromptSpec.
Uses chat_json() since we need a reliable structured output, not prose.
"""

import logging
from agentscope.agent import AgentBase
from agentscope.message import Msg

from models import PromptSpec
from services import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior prompt engineering analyst.
Your job is to parse a developer's raw, messy requirement into a clean
structured specification for a prompt optimization pipeline.

You MUST respond with only a valid JSON object — no explanation, no markdown.

JSON schema:
{
  "objective":    "clear one-sentence goal of what the prompt must do",
  "context":      "domain or app context e.g. e-commerce chatbot, devops tool",
  "target_model": "which LLM this prompt targets, default llama-3.3-70b-versatile",
  "variables":    ["list", "of", "placeholders", "like", "{product}"],
  "constraints":  ["hard rules like max token limits, tone, format"],
  "examples": [
    {"input": "example user input", "output": "expected LLM output"}
  ]
}

If the user doesn't mention a field, use a sensible default or empty list.
"""


class AnalystAgent(AgentBase):
    """
    Parses raw user requirement → PromptSpec dataclass.
    First agent called in the pipeline, runs once.
    """

    def __init__(self, llm: LLMClient):
        super().__init__()
        self.name="Analyst"
        self.llm = llm
        
    async def reply(self, msg: Msg) -> Msg:
        logger.info("Analyst parsing raw requirement...")
        raw_input = msg.content

        parsed = self.llm.chat_json(
            system_prompt = SYSTEM_PROMPT,
            user_message  = f"Parse this requirement:\n\n{raw_input}",
        )

        spec = PromptSpec(
            objective    = parsed.get("objective", ""),
            context      = parsed.get("context", ""),
            target_model = parsed.get("target_model", "llama-3.3-70b-versatile"),
            variables    = parsed.get("variables", []),
            constraints  = parsed.get("constraints", []),
            examples     = parsed.get("examples", []),
            raw_input    = raw_input,
        )

        logger.info(f"Analyst produced spec | objective: {spec.objective}")

        return Msg(
            name     = self.name,
            role     = "assistant",
            content  = spec.to_text(),
            metadata = {"spec": spec},
        )
'''
    def reply(self, msg: Msg) -> Msg:
        """
        Receives a Msg with raw user requirement as content.
        Returns a Msg whose content is the serialized PromptSpec as text.
        Also attaches the PromptSpec object in metadata for the controller.
        """
        logger.info("Analyst parsing raw requirement...")
        raw_input = msg.content

        parsed = self.llm.chat_json(
            system_prompt = SYSTEM_PROMPT,
            user_message  = f"Parse this requirement:\n\n{raw_input}",
        )

        spec = PromptSpec(
            objective    = parsed.get("objective", ""),
            context      = parsed.get("context", ""),
            target_model = parsed.get("target_model", "llama-3.3-70b-versatile"),
            variables    = parsed.get("variables", []),
            constraints  = parsed.get("constraints", []),
            examples     = parsed.get("examples", []),
            raw_input    = raw_input,
        )

        logger.info(f"Analyst produced spec | objective: {spec.objective}")

        return Msg(
            name     = self.name,
            role     = "assistant",
            content  = spec.to_text(),
            metadata = {"spec": spec},
        )
'''