"""
agents/critic.py

Critic Agent — lives inside the MsgHub loop alongside Architect.
Reviews each draft and returns structured feedback + a numeric score.
Loop exits when score >= threshold or max rounds reached.
"""

import re
import logging
from agentscope.agent import AgentBase
from agentscope.message import Msg

from services import LLMClient

logger = logging.getLogger(__name__)

SCORE_THRESHOLD = 8.5
SYSTEM_PROMPT = """You are a ruthless but fair prompt engineering critic.
Your job is to review a prompt draft against its original specification and
score it on a scale of 0-10.

Evaluate on these criteria:
  - Clarity       : Is the instruction unambiguous?
  - Completeness  : Does it cover all spec requirements?
  - Hallucination risk: Does it reduce chances of model making things up?
  - Edge case handling: Does it handle unexpected inputs gracefully?
  - Token efficiency: Is it concise without losing meaning?
  - Format correctness: Is it a proper system prompt written in second person?
    A first-person greeting or user message is an automatic score of 3 or below.

You MUST respond in this exact format — nothing else:

SCORE: <number between 0 and 10, one decimal place>
FEEDBACK: <2-4 sentences of specific, actionable critique>
VERDICT: <PASSED if score >= 8.5, else REVISE>
"""


class CriticAgent(AgentBase):
    """
    Reviews Architect drafts and issues scores + feedback.
    The MsgHub controller reads VERDICT to decide whether to exit the loop.
    """

    def __init__(self, llm: LLMClient):
        super().__init__()
        self.name = "Critic"
        self.llm = llm

    async def reply(self, msg: Msg) -> Msg:
        logger.info("Critic reviewing draft...")

        review = self.llm.chat(
            system_prompt = SYSTEM_PROMPT,
            user_message  = f"Review this prompt draft:\n\n{msg.content}",
            temperature   = 0.3,
        )

        score   = self._parse_score(review)
        verdict = "PASSED" if score >= SCORE_THRESHOLD else "REVISE"

        logger.info(f"Critic score: {score}/10 | verdict: {verdict}")

        return Msg(
            name     = self.name,
            role     = "assistant",
            content  = review,
            metadata = {"score": score, "verdict": verdict},
        )

    @staticmethod
    def _parse_score(review_text: str) -> float:
        """
        Extracts the numeric score from the Critic's response.
        Falls back to 0.0 if parsing fails so the loop always continues safely.
        """
        match = re.search(r"SCORE:\s*([0-9]+(?:\.[0-9]+)?)", review_text)
        if match:
            return float(match.group(1))
        logger.warning("Could not parse score from Critic response. Defaulting to 0.0")
        return 0.0