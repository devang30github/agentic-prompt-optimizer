"""
services/scorer.py

Scorer — standalone utility that provides a detailed rubric-based
evaluation of a prompt using LLM-as-a-Judge pattern.
Called optionally after the hub loop for a richer final scorecard
beyond the Critic's in-loop score.
"""

import logging
from services.llm_client import LLMClient

logger = logging.getLogger(__name__)

JUDGE_SYSTEM_PROMPT = """You are an impartial LLM prompt quality judge.
Evaluate the given prompt across 5 criteria and return ONLY valid JSON.
No explanation outside the JSON object.

JSON schema:
{
  "clarity":             <0-10 float>,
  "completeness":        <0-10 float>,
  "hallucination_risk":  <0-10 float, 10 = very low risk>,
  "edge_case_handling":  <0-10 float>,
  "token_efficiency":    <0-10 float>,
  "overall":             <weighted average, 0-10 float>,
  "summary":             "<2-3 sentence overall assessment>"
}
"""


class Scorer:
    """
    LLM-as-a-Judge evaluator for final prompt quality.

    Produces a detailed rubric scorecard with per-dimension scores
    and an overall weighted average. Used after the hub loop exits
    to give the user a richer breakdown than just one number.
    """

    WEIGHTS = {
        "clarity":            0.25,
        "completeness":       0.25,
        "hallucination_risk": 0.20,
        "edge_case_handling": 0.15,
        "token_efficiency":   0.15,
    }

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def evaluate(self, prompt_text: str, spec_text: str) -> dict:
        """
        Run full rubric evaluation on a prompt against its spec.

        Args:
            prompt_text: The final prompt to evaluate.
            spec_text:   The original PromptSpec as text for context.

        Returns:
            Dict with per-dimension scores, overall score, and summary.
        """
        logger.info("Scorer running LLM-as-a-Judge evaluation...")

        user_message = (
            f"=== Original Specification ===\n{spec_text}\n\n"
            f"=== Prompt to Evaluate ===\n{prompt_text}"
        )

        try:
            result = self.llm.chat_json(
                system_prompt = JUDGE_SYSTEM_PROMPT,
                user_message  = user_message,
            )
            result["overall"] = self._compute_weighted(result)
            logger.info(f"Scorer overall: {result['overall']}/10")
            return result

        except (ValueError, RuntimeError) as e:
            logger.error(f"Scorer evaluation failed: {e}")
            return self._fallback_scorecard()

    def _compute_weighted(self, scores: dict) -> float:
        """
        Recompute weighted overall from individual dimension scores.
        Overrides whatever the model computed to ensure consistency.
        """
        total = sum(
            scores.get(dim, 0.0) * weight
            for dim, weight in self.WEIGHTS.items()
        )
        return round(total, 2)

    @staticmethod
    def _fallback_scorecard() -> dict:
        """
        Returns a safe zero scorecard if evaluation fails,
        so the pipeline never crashes on scoring errors.
        """
        return {
            "clarity":            0.0,
            "completeness":       0.0,
            "hallucination_risk": 0.0,
            "edge_case_handling": 0.0,
            "token_efficiency":   0.0,
            "overall":            0.0,
            "summary":            "Evaluation failed. Please retry.",
        }