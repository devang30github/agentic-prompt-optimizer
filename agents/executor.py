"""
agents/executor.py

Executor Agent — runs after the MsgHub loop exits with a passing prompt.
Tests the final prompt against a real sample input and returns the output.
Results are fed back into OptimizationResult for audit and display.
"""

import logging
from agentscope.agent import AgentBase
from agentscope.message import Msg

from services import LLMClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a prompt execution tester.
You will be given a finalized system prompt and a sample user input.
Your job is to simulate exactly how an LLM would respond when using
that system prompt — faithfully and without meta-commentary.

Do NOT say things like "as an AI" or explain what you are doing.
Just produce the output the prompt would generate.
"""


class ExecutorAgent(AgentBase):
    """
    Runs the final approved prompt against a sample input.
    Produces a real-world output example for the OptimizationResult.
    """

    def __init__(self, llm: LLMClient):
        super().__init__()
        self.name = "Executor"
        self.llm = llm

    async def reply(self, msg: Msg) -> Msg:
        final_prompt = msg.metadata.get("final_prompt", "")
        sample_input = msg.metadata.get("sample_input", "Hello, can you help me?")

        if not final_prompt:
            logger.warning("Executor received empty prompt — skipping execution.")
            return Msg(
                name     = self.name,
                role     = "assistant",
                content  = "No prompt provided for execution.",
                metadata = {"executor_output": None},
            )

        logger.info("Executor running final prompt against sample input...")

        output = self.llm.chat(
            system_prompt = final_prompt,
            user_message  = sample_input,
            temperature   = 0.7,
        )

        logger.info(f"Executor output ({len(output)} chars): {output[:100]}...")

        return Msg(
            name     = self.name,
            role     = "assistant",
            content  = output,
            metadata = {"executor_output": output},
        )