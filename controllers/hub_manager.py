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
        
    async def harden(
        self,
        spec: PromptSpec,
        current_prompt: str,
        vulnerabilities: list[str],
        patch_recommendations: list[str],
    ) -> tuple[str, IterationLog]:
        """
        Runs one targeted hardening round after Red Teamer finds vulnerabilities.
        Feeds vulnerabilities + patch recommendations directly to the Architect.
        """
        logger.info(f"Hub hardening round | vulnerabilities: {vulnerabilities}")

        patches_text = "\n".join(f"  - {p}" for p in patch_recommendations)
        vulns_text   = ", ".join(vulnerabilities)

        hardening_input = (
            f"The following prompt has been red team tested and found VULNERABLE.\n\n"
            f"=== Original Specification ===\n{spec.to_text()}\n\n"
            f"=== Current Prompt (needs hardening) ===\n{current_prompt}\n\n"
            f"=== Vulnerabilities Found ===\n{vulns_text}\n\n"
            f"=== Required Fixes ===\n{patches_text}\n\n"
            f"Rewrite the prompt to patch ALL vulnerabilities while keeping "
            f"the original functionality intact. Add explicit rules that prevent "
            f"prompt injection, role confusion, and the other attack vectors found."
        )

        async with MsgHub(participants=[self.architect, self.critic]):
            architect_msg = await self.architect.reply(
                Msg(name="pipeline", role="user", content=hardening_input)
            )
            hardened_prompt = architect_msg.content

            critic_msg = await self.critic.reply(
                Msg(name="pipeline", role="user", content=hardened_prompt)
            )
            score   = critic_msg.metadata.get("score", 0.0)
            feedback = critic_msg.content

        log = IterationLog(
            iteration       = 999,  # sentinel value — marks hardening round
            draft           = hardened_prompt,
            critic_feedback = f"[HARDENING ROUND]\n{feedback}",
            score           = score,
        )

        logger.info(f"Hardening round complete | score: {score}")
        return hardened_prompt, log

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