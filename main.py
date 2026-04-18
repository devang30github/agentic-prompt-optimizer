"""
main.py

FastAPI server — exposes the APO pipeline as a REST API.
Three endpoints consumed by the frontend:
  POST /optimize       → runs the full pipeline
  GET  /health         → sanity check
  POST /score          → standalone scorer for an existing prompt
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import agentscope

from config import settings, setup_logging
from services import LLMClient, Scorer
from agents import AnalystAgent, ArchitectAgent, CriticAgent, ExecutorAgent
from controllers.hub_manager import HubManager
from controllers import Pipeline
from fastapi.responses import FileResponse

setup_logging()

# Initialise AgentScope runtime
agentscope.init(logging_level=settings.log_level)

app = FastAPI(
    title       = "Agentic Prompt Optimizer",
    description = "Multi-agent system that turns raw requirements into production-grade prompts.",
    version     = "1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["*"],
    allow_credentials = False,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# Mount frontend so index.html is served at /
app.mount("/static", StaticFiles(directory="frontend"), name="static")

@app.get("/")
def serve_frontend():
    return FileResponse("frontend/index.html")
  
# ------------------------------------------------------------------
# Dependency: build a fresh pipeline per request (stateless)
# ------------------------------------------------------------------

def build_pipeline() -> tuple[Pipeline, Scorer]:
    settings.validate()
    llm       = LLMClient(api_key=settings.api_key, model=settings.model)
    analyst   = AnalystAgent(llm)
    architect = ArchitectAgent(llm)
    critic    = CriticAgent(llm)
    executor  = ExecutorAgent(llm)
    hub       = HubManager(architect, critic)
    pipeline  = Pipeline(analyst, hub, executor)
    scorer    = Scorer(llm)
    return pipeline, scorer


# ------------------------------------------------------------------
# Request / Response schemas
# ------------------------------------------------------------------

class OptimizeRequest(BaseModel):
    raw_input   : str
    sample_input: Optional[str] = "Hello, can you help me?"

class ScoreRequest(BaseModel):
    prompt_text: str
    spec_text  : str

class IterationOut(BaseModel):
    iteration       : int
    score           : float
    critic_feedback : str
    draft           : str

class OptimizeResponse(BaseModel):
    final_prompt    : str
    final_score     : float
    passed          : bool
    total_rounds    : int
    score_history   : list[float]
    iterations      : list[IterationOut]
    executor_output : Optional[str]
    scorecard       : dict


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@app.get("/health")
def health():
    return {"status": "ok", "model": settings.model}

@app.post("/optimize", response_model=OptimizeResponse)
async def optimize(req: OptimizeRequest):
    try:
        pipeline, scorer = build_pipeline()
        result           = await pipeline.run(req.raw_input, req.sample_input)
        scorecard        = scorer.evaluate(
            prompt_text = result.final_prompt,
            spec_text   = result.spec.to_text() if result.spec else "",
        )

        return OptimizeResponse(
            final_prompt    = result.final_prompt,
            final_score     = result.final_score,
            passed          = result.passed,
            total_rounds    = result.total_rounds,
            score_history   = result.score_history(),
            iterations      = [
                IterationOut(
                    iteration       = it.iteration,
                    score           = it.score,
                    critic_feedback = it.critic_feedback,
                    draft           = it.draft,
                )
                for it in result.iterations
            ],
            executor_output = result.executor_output,
            scorecard       = scorecard,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/score")
async def score_prompt(req: ScoreRequest):
    try:
        _, scorer = build_pipeline()
        scorecard = scorer.evaluate(req.prompt_text, req.spec_text)
        return {"scorecard": scorecard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))