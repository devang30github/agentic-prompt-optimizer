"""
models/spec.py

PromptSpec — the structured input contract created by the Analyst Agent.
Every other agent receives this, never the raw user string.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PromptSpec:
    """
    Structured representation of what the user wants optimized.

    Fields:
        objective:   What the prompt should make the LLM do.
        context:     Background info or domain (e.g. "e-commerce chatbot").
        target_model: Which model the prompt will run on.
        variables:   Placeholders the prompt should support e.g. {product}.
        constraints: Hard rules e.g. "max 200 tokens", "no bullet points".
        examples:    Optional few-shot input/output pairs.
        raw_input:   Original unprocessed user request — kept for audit trail.
    """

    objective:    str
    context:      str
    target_model: str                        = "llama-3.3-70b-versatile"
    variables:    list[str]                  = field(default_factory=list)
    constraints:  list[str]                  = field(default_factory=list)
    examples:     list[dict[str, str]]       = field(default_factory=list)
    raw_input:    Optional[str]              = None

    def to_text(self) -> str:
        """
        Serialize spec to a readable block that agents can consume as context.
        """
        lines = [
            f"Objective:    {self.objective}",
            f"Context:      {self.context}",
            f"Target model: {self.target_model}",
        ]
        if self.variables:
            lines.append(f"Variables:    {', '.join(self.variables)}")
        if self.constraints:
            lines.append("Constraints:")
            for c in self.constraints:
                lines.append(f"  - {c}")
        if self.examples:
            lines.append("Examples:")
            for i, ex in enumerate(self.examples, 1):
                lines.append(f"  [{i}] Input:  {ex.get('input', '')}")
                lines.append(f"       Output: {ex.get('output', '')}")
        return "\n".join(lines)