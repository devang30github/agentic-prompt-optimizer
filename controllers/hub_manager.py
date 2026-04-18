"""
controllers/hub_manager.py

HubManager — owns the Architect <-> Critic MsgHub loop.
Runs iterative refinement until score >= threshold or max rounds hit.
This is the core of the APO system.
"""

import asyncio
import logging
from agentscope.pipeline import MsgHub
from agentscope.message import Msg

from agents import ArchitectAgent, CriticAgent
from models import IterationLog, PromptSpec

logger = logging.getLogger(__name__)

MAX_ROUNDS = 5


class HubManager:
    def __init__(self, architect: ArchitectAgent, critic: CriticAgent):
        self.architect = architect
        self.critic    = critic

    async def run(self, spec: PromptSpec) -> tuple[str, list[IterationLog]]:
        iterations   : list[IterationLog] = []
        current_draft: str                = ""
        feedback     : str                = ""

        async with MsgHub(participants=[self.architect, self.critic]):
            for round_num in range(1, MAX_ROUNDS + 1):
                logger.info(f"--- Hub round {round_num}/{MAX_ROUNDS} ---")

                architect_input = self._build_architect_input(
                    spec, current_draft, feedback, round_num
                )

                architect_msg = await self.architect.reply(
                    Msg(name="pipeline", role="user", content=architect_input)
                )
                current_draft = architect_msg.content

                critic_msg = await self.critic.reply(
                    Msg(name="pipeline", role="user", content=current_draft)
                )
                critic_response = critic_msg.content
                score           = critic_msg.metadata.get("score", 0.0)
                verdict         = critic_msg.metadata.get("verdict", "REVISE")
                feedback        = critic_response

                iterations.append(IterationLog(
                    iteration       = round_num,
                    draft           = current_draft,
                    critic_feedback = critic_response,
                    score           = score,
                ))

                logger.info(f"Round {round_num} complete | score={score} | verdict={verdict}")

                if verdict == "PASSED":
                    logger.info("Critic issued PASSED — exiting hub loop.")
                    break

                if round_num == MAX_ROUNDS:
                    logger.warning("Max rounds reached without PASSED verdict.")

        return current_draft, iterations

    @staticmethod
    def _build_architect_input(
        spec      : PromptSpec,
        prev_draft: str,
        feedback  : str,
        round_num : int,
    ) -> str:
        if round_num == 1:
            return (
                f"Create a production-grade prompt for the following specification:\n\n"
                f"{spec.to_text()}"
            )
        return (
            f"Revise your prompt draft based on the critic's feedback.\n\n"
            f"=== Original Specification ===\n{spec.to_text()}\n\n"
            f"=== Your Previous Draft ===\n{prev_draft}\n\n"
            f"=== Critic Feedback ===\n{feedback}\n\n"
            f"Produce an improved prompt that addresses all feedback points."
        )