"""
config.py

Central configuration. Loads from .env and exposes a single
settings object imported everywhere — never use os.getenv() directly
in agent or controller code.
"""

import os
import logging
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Settings:
    # LLM
    api_key    : str   = os.getenv("GROQ_API_KEY", "")
    model      : str   = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

    # Pipeline
    max_rounds : int   = int(os.getenv("MAX_ROUNDS", "5"))
    score_threshold: float = float(os.getenv("SCORE_THRESHOLD", "8.5"))

    # Server
    host       : str   = os.getenv("HOST", "0.0.0.0")
    port       : int   = int(os.getenv("PORT", "8000"))
    debug      : bool  = os.getenv("DEBUG", "true").lower() == "true"

    # Logging
    log_level  : str   = os.getenv("LOG_LEVEL", "INFO")

    def validate(self):
        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set. Add it to your .env file.")


settings = Settings()


def setup_logging():
    logging.basicConfig(
        level  = getattr(logging, settings.log_level, logging.INFO),
        format = "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )