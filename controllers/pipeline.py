"""
controllers/pipeline.py

Pipeline — top-level orchestrator for the full APO run.
Order: Analyst → HubManager → RedTeamer → (optional hardening) → Executor → Scorer
"""

import logging
from agentscope.message import Msg

from agents import AnalystAgent, ExecutorAgent, RedTeamerAgent
from controllers.hub_manager import HubManager
from models import OptimizationResult

logger = logging.getLogger(__name__)

MAX_REDTEAM_CYCLES = 2


class Pipeline:
    def __init__(
        self,
        analyst     : AnalystAgent,
        hub_manager : HubManager,
        executor    : ExecutorAgent,
        red_teamer  : RedTeamerAgent,
    ):
        self.analyst     = analyst
        self.hub_manager = hub_manager
        self.executor    = executor
        self.red_teamer  = red_teamer

    async def run(
        self,
        raw_input   : str,
        sample_input: str = "Hello, can you help me?",
    ) -> OptimizationResult:
        logger.info("=== APO Pipeline starting ===")

        # Stage 1: Analyst
        logger.info("Stage 1: Analyst Agent")
        analyst_msg = await self.analyst.reply(
            Msg(name="user", role="user", content=raw_input)
        )
        spec = analyst_msg.metadata.get("spec")
        if not spec:
            raise RuntimeError("Analyst Agent failed to produce a PromptSpec.")

        # Stage 2: Hub (Architect <-> Critic loop)
        logger.info("Stage 2: HubManager (Architect <-> Critic loop)")
        final_prompt, iterations = await self.hub_manager.run(spec)

        # Stage 3: Red Teamer (up to MAX_REDTEAM_CYCLES)
        logger.info("Stage 3: Red Teamer")
        red_team_reports = []

        for cycle in range(1, MAX_REDTEAM_CYCLES + 1):
            logger.info(f"Red Team cycle {cycle}/{MAX_REDTEAM_CYCLES}")

            rt_msg = await self.red_teamer.reply(
                Msg(
                    name     = "pipeline",
                    role     = "user",
                    content  = "Attack the prompt.",
                    metadata = {
                        "final_prompt": final_prompt,
                        "spec_text"   : spec.to_text(),
                    },
                )
            )

            report           = rt_msg.metadata.get("report", {})
            hardening_needed = rt_msg.metadata.get("hardening_needed", False)
            vulnerabilities  = rt_msg.metadata.get("vulnerabilities", [])
            patches          = rt_msg.metadata.get("patch_recommendations", [])
            red_team_reports.append(report)

            if hardening_needed and cycle < MAX_REDTEAM_CYCLES:
                logger.info(f"Hardening needed — vulnerabilities: {vulnerabilities}")
                final_prompt, hardening_log = await self.hub_manager.harden(
                    spec                  = spec,
                    current_prompt        = final_prompt,
                    vulnerabilities       = vulnerabilities,
                    patch_recommendations = patches,
                )
                iterations.append(hardening_log)
            else:
                logger.info("Red Teamer passed — prompt is robust.")
                break

        # Stage 4: Executor
        logger.info("Stage 4: Executor Agent")
        executor_msg = await self.executor.reply(
            Msg(
                name     = "pipeline",
                role     = "user",
                content  = "Execute the final prompt.",
                metadata = {
                    "final_prompt": final_prompt,
                    "sample_input": sample_input,
                },
            )
        )
        executor_output = executor_msg.metadata.get("executor_output")

        # Assemble result
        final_score  = next(
            (it.score for it in reversed(iterations) if it.iteration != 999),
            0.0
        )
        passed       = any(it.score >= 8.5 for it in iterations if it.iteration != 999)
        total_rounds = len([it for it in iterations if it.iteration != 999])

        result = OptimizationResult(
            final_prompt     = final_prompt,
            final_score      = final_score,
            iterations       = iterations,
            total_rounds     = total_rounds,
            passed           = passed,
            spec             = spec,
            executor_output  = executor_output,
            red_team_reports = red_team_reports,
        )

        logger.info(f"=== APO Pipeline complete | score={final_score} | passed={passed} ===")
        return result