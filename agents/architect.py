"""
agents/architect.py

Architect Agent — lives inside the MsgHub loop.
Receives either the initial PromptSpec or Critic feedback,
and produces/refines a prompt draft each round.
"""

import logging
from agentscope.agent import AgentBase
from agentscope.message import Msg

from services import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an expert prompt architect specialising in
production-grade LLM prompt engineering.

Your job is to write or refine a SYSTEM PROMPT based on either:
  - An initial specification (first round), or
  - A specification + previous draft + critic feedback (subsequent rounds)

CRITICAL RULES:
  - Output must be a SYSTEM PROMPT — written in second person ("You are...", "Your role is...", "Your job is...")
  - It instructs the LLM how to behave, what rules to follow, and how to handle edge cases
  - NEVER write a greeting, a user message, or a first-person response ("I am here to help...")
  - NEVER include meta-commentary like "Here is the prompt:" or "This prompt does..."
  - The output IS the system prompt. It must be copy-pasteable directly into an LLM system field.
  - Always include explicit rules against prompt injection, role confusion, and off-topic inputs.

Apply the best prompting technique for the task:
  - Chain-of-Thought (CoT) for reasoning tasks
  - Few-shot examples for pattern tasks
  - ReAct format for tool-use / agent tasks
  - CO-STAR structure for role-based tasks

Structure the system prompt with these sections where relevant:
  - Role definition ("You are a...")
  - Core responsibilities
  - Hard rules and constraints
  - Edge case handling
  - Output format instructions
"""

class ArchitectAgent(AgentBase):
    """
    Drafts and refines prompts inside the MsgHub loop.
    On round 1: generates a fresh draft from the spec.
    On round N: revises the previous draft using Critic feedback.
    """

    def __init__(self, llm: LLMClient):
        super().__init__()
        self.name = "Architect"
        self.llm = llm
    
    async def reply(self, msg: Msg) -> Msg:
        logger.info("Architect drafting prompt...")

        draft = self.llm.chat(
            system_prompt = SYSTEM_PROMPT,
            user_message  = msg.content,
            temperature   = 0.8,
        )

        logger.info(f"Architect produced draft ({len(draft)} chars)")

        return Msg(
            name    = self.name,
            role    = "assistant",
            content = draft,
        )
'''
    def reply(self, msg: Msg) -> Msg:
        """
        Receives a Msg with spec text (round 1) or spec + feedback (round N+).
        Returns a Msg containing the new prompt draft.
        """
        logger.info("Architect drafting prompt...")

        draft = self.llm.chat(
            system_prompt = SYSTEM_PROMPT,
            user_message  = msg.content,
            temperature   = 0.8,   # slightly creative for drafting
        )

        logger.info(f"Architect produced draft ({len(draft)} chars)")

        return Msg(
            name    = self.name,
            role    = "assistant",
            content = draft,
        )
'''