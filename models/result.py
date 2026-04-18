"""
models/result.py

OptimizationResult — the full output contract returned at the end of the pipeline.
Carries the final prompt, every iteration's score, and critic feedback history.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class IterationLog:
    """
    Snapshot of a single Architect↔Critic round.
    Stored so the frontend can show the score progression chart.
    """

    iteration:      int
    draft:          str
    critic_feedback: str
    score:          float


@dataclass
class OptimizationResult:
    """
    Everything produced by a full pipeline run.

    Fields:
        final_prompt:    The approved, production-ready prompt.
        final_score:     Last score issued by the Critic (0–10).
        iterations:      Full log of every draft/feedback/score round.
        total_rounds:    How many Architect↔Critic loops ran.
        passed:          True if score threshold was met, False if max rounds hit.
        spec:            The PromptSpec this result was built from.
        executor_output: Raw output from running the final prompt (optional).
        created_at:      UTC timestamp of completion.
    """

    final_prompt:    str
    final_score:     float
    iterations:      list[IterationLog]      = field(default_factory=list)
    total_rounds:    int                     = 0
    passed:          bool                    = False
    spec:            Optional[object]        = None   # PromptSpec — avoid circular import
    executor_output: Optional[str]           = None
    red_team_reports : list[dict]              = field(default_factory=list)
    created_at:      str                     = field(
                         default_factory=lambda: datetime.utcnow().isoformat()
                     )

    def summary(self) -> str:
        """
        Human-readable summary — used in API responses and logs.
        """
        status = "PASSED" if self.passed else "MAX ROUNDS REACHED"
        lines = [
            f"Status:       {status}",
            f"Final score:  {self.final_score}/10",
            f"Rounds taken: {self.total_rounds}",
            f"Completed at: {self.created_at}",
            "",
            "--- Final Prompt ---",
            self.final_prompt,
        ]
        return "\n".join(lines)

    def score_history(self) -> list[float]:
        """
        Returns just the scores across iterations — useful for the frontend chart.
        """
        return [it.score for it in self.iterations]