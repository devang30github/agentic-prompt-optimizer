"""
controllers/pipeline.py

Pipeline — top-level orchestrator for the full APO run.
Calls agents in order: Analyst → HubManager → Executor.
Returns a complete OptimizationResult.
"""

import logging
from agentscope.message import Msg

from agents import AnalystAgent, ExecutorAgent
from controllers.hub_manager import HubManager
from models import OptimizationResult

logger = logging.getLogger(__name__)


class Pipeline:
    def __init__(
        self,
        analyst    : AnalystAgent,
        hub_manager: HubManager,
        executor   : ExecutorAgent,
    ):
        self.analyst     = analyst
        self.hub_manager = hub_manager
        self.executor    = executor

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

        # Stage 2: HubManager
        logger.info("Stage 2: HubManager (Architect <-> Critic loop)")
        final_prompt, iterations = await self.hub_manager.run(spec)

        final_score  = iterations[-1].score if iterations else 0.0
        passed       = any(it.score >= 8.5 for it in iterations)
        total_rounds = len(iterations)

        # Stage 3: Executor
        logger.info("Stage 3: Executor Agent")
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

        result = OptimizationResult(
            final_prompt    = final_prompt,
            final_score     = final_score,
            iterations      = iterations,
            total_rounds    = total_rounds,
            passed          = passed,
            spec            = spec,
            executor_output = executor_output,
        )

        logger.info(f"=== APO Pipeline complete | score={final_score} | passed={passed} ===")
        return result