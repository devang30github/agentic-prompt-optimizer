# [APO] Agentic Prompt Optimizer

> A multi-agent system that transforms raw developer intent into production-grade LLM prompts — powered by AgentScope, Groq, and a Committee of Expert Agents.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi&logoColor=white)
![AgentScope](https://img.shields.io/badge/AgentScope-latest-7C3AED?style=flat-square)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.3_70B-F55036?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)

---

## What is APO?

Most developers write LLM system prompts by hand — iterating slowly, guessing at edge cases, and never knowing how "good" the prompt actually is.

**APO automates this entire process.** You describe what you need in plain English. A pipeline of specialized AI agents parses your intent, drafts a prompt, critiques it, refines it across multiple rounds, tests it against real input, and scores it on a detailed rubric — all without you writing a single line of prompt engineering.

**Input:** `"need a customer support bot for electronics store, polite, never make up specs, escalate if angry, use {product_name} and {order_id}"`

**Output:** A production-ready system prompt, scored 9.2/10 across 5 dimensions, with a full iteration log showing how it improved round by round.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        APO Pipeline                             │
│                                                                 │
│  Raw Input                                                      │
│     │                                                           │
│     ▼                                                           │
│  ┌──────────────┐                                               │
│  │   Analyst    │  Parses messy input → structured PromptSpec   │
│  │   Agent      │  (objective, variables, constraints, examples)│
│  └──────┬───────┘                                               │
│         │  PromptSpec                                           │
│         ▼                                                       │
│  ┌─────────────────────────────────────┐                        │
│  │           MsgHub (AgentScope)       │                        │
│  │                                     │                        │
│  │  ┌─────────────┐   draft   ┌──────────────┐                 │
│  │  │  Architect  │ ────────► │    Critic    │                 │
│  │  │   Agent     │ ◄──────── │    Agent     │                 │
│  │  └─────────────┘  feedback └──────────────┘                 │
│  │                                     │                        │
│  │  Loop exits when score ≥ 8.5        │                        │
│  │  or MAX_ROUNDS (5) reached          │                        │
│  └─────────────────────────────────────┘                        │
│         │  Final Prompt                                         │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │   Executor   │  Runs final prompt against sample input       │
│  │   Agent      │  → real-world output example                  │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  ┌──────────────┐                                               │
│  │    Scorer    │  LLM-as-a-Judge rubric evaluation             │
│  │   Service    │  → per-dimension scorecard (5 criteria)       │
│  └──────┬───────┘                                               │
│         │                                                       │
│         ▼                                                       │
│  OptimizationResult                                             │
│  (final prompt + score history + scorecard + executor output)   │
└─────────────────────────────────────────────────────────────────┘
```

### Agent Roles

| Agent | Role | Key Behaviour |
|---|---|---|
| **Analyst** | Requirement parser | Converts raw text → structured `PromptSpec` via `chat_json()` |
| **Architect** | Prompt drafter | Writes system prompts using CoT / Few-shot / ReAct / CO-STAR techniques |
| **Critic** | Quality reviewer | Scores drafts 0–10, issues `REVISE` or `PASSED` verdict |
| **Executor** | Real-world tester | Runs the final prompt against a sample input |
| **Scorer** | Rubric evaluator | LLM-as-a-Judge across 5 dimensions with weighted overall score |

### MsgHub Loop (AgentScope)

The Architect↔Critic refinement loop runs inside AgentScope's `MsgHub` — a shared broadcast environment where every message is visible to all participants. This allows genuine iterative collaboration rather than a simple linear chain:

```
Round 1: Architect drafts → Critic scores 6.8 → REVISE
Round 2: Architect revises → Critic scores 7.9 → REVISE  
Round 3: Architect refines → Critic scores 8.7 → PASSED ✓
```

---

## Project Structure

```
apo/
│
├── agents/                    # Agent layer (business logic)
│   ├── __init__.py
│   ├── analyst.py             # Parses raw input → PromptSpec
│   ├── architect.py           # Drafts & refines system prompts
│   ├── critic.py              # Reviews drafts, issues scores & verdicts
│   └── executor.py            # Tests final prompt against sample input
│
├── controllers/               # Controller layer (orchestration)
│   ├── __init__.py
│   ├── hub_manager.py         # Owns the MsgHub Architect↔Critic loop
│   └── pipeline.py            # Top-level pipeline: Analyst→Hub→Executor
│
├── models/                    # Model layer (data contracts)
│   ├── __init__.py
│   ├── spec.py                # PromptSpec dataclass
│   └── result.py              # OptimizationResult + IterationLog dataclasses
│
├── services/                  # Service layer (external integrations)
│   ├── __init__.py
│   ├── llm_client.py          # OpenAI-compatible LLM wrapper (Groq endpoint)
│   └── scorer.py              # LLM-as-a-Judge rubric evaluator
│
├── frontend/                  # View layer (vanilla HTML/CSS/JS)
│   ├── index.html             # Single-page UI
│   ├── style.css              # Dark theme, DM Mono + Syne fonts
│   └── app.js                 # SSE client, chart rendering, stage tracker
│
├── main.py                    # FastAPI server + SSE streaming endpoint
├── config.py                  # Settings loaded from .env
├── requirements.txt
└── .env                       # API keys (not committed)
```

### MVC Mapping

```
models/      →  Data shapes (PromptSpec, OptimizationResult, IterationLog)
agents/      →  Business logic — each agent is a self-contained expert
controllers/ →  Orchestration — pipeline flow and MsgHub loop management
services/    →  External integrations — LLM client, scorer utility
frontend/    →  View layer — the UI that consumes the FastAPI endpoints
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Agent Framework | **AgentScope** | MsgHub for broadcast messaging, async AgentBase |
| LLM Provider | **Groq** (free tier) | Fast inference, LLaMA 3.3 70B, OpenAI-compatible |
| LLM Client | **openai** Python SDK | Provider-agnostic via `base_url` override |
| Backend | **FastAPI** + **uvicorn** | Async, SSE streaming, auto Swagger docs |
| Frontend | **Vanilla HTML/CSS/JS** | Zero build step, Chart.js for score graph |
| Config | **python-dotenv** | Environment-based configuration |

---

## Scorecard Dimensions

The Scorer evaluates every final prompt across 5 weighted criteria:

| Dimension | Weight | What it measures |
|---|---|---|
| **Clarity** | 25% | Unambiguous instructions with no vague language |
| **Completeness** | 25% | All spec requirements covered |
| **Hallucination Risk** | 20% | Specific guardrails against making things up |
| **Edge Case Handling** | 15% | Handles angry users, missing vars, off-topic inputs |
| **Token Efficiency** | 15% | Concise without losing meaning |

---

## Getting Started

### Prerequisites

- Python 3.11+
- A free [Groq API key](https://console.groq.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/apo.git
cd apo

# Install dependencies
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Configuration

```env
GROQ_API_KEY=your_groq_api_key_here
LLM_MODEL=openai/gpt-oss-20b
MAX_ROUNDS=5
SCORE_THRESHOLD=8.5
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO
```

### Run

```bash
uvicorn main:app --reload
```

Open **`http://localhost:8000/static/index.html`** in your browser.

API docs available at **`http://localhost:8000/docs`**

---

## API Reference

### `POST /optimize/stream`
Runs the full pipeline with real-time SSE stage updates.

```json
{
  "raw_input": "need a prompt for a customer support bot...",
  "sample_input": "Hi, my order hasn't arrived and I'm frustrated!"
}
```

Emits SSE events:
```
data: {"stage": "analyst",  "status": "start"}
data: {"stage": "analyst",  "status": "done"}
data: {"stage": "hub",      "status": "start"}
data: {"stage": "hub",      "status": "round", "round": 1, "score": 6.8}
data: {"stage": "hub",      "status": "round", "round": 2, "score": 8.7}
data: {"stage": "hub",      "status": "done"}
data: {"stage": "executor", "status": "start"}
data: {"stage": "executor", "status": "done"}
data: {"stage": "scorer",   "status": "start"}
data: {"stage": "scorer",   "status": "done"}
data: {"stage": "complete", "result": { ... }}
```

### `POST /optimize`
Same as above but returns a single JSON response (no streaming).

### `POST /score`
Standalone rubric scorer for any existing prompt.

```json
{
  "prompt_text": "You are a customer support assistant...",
  "spec_text":   "Objective: handle electronics support queries..."
}
```

### `GET /health`
```json
{ "status": "ok", "model": "llama-3.3-70b-versatile" }
```

---

## Sample Test Cases

```json
// 1. Customer Support Bot
{
  "raw_input": "customer support chatbot for electronics store, polite, never make up product specs, escalate if angry, use {product_name} and {order_id}",
  "sample_input": "My laptop screen is broken and I want a refund immediately!"
}

// 2. Code Review Assistant  
{
  "raw_input": "code reviewer for python, identify bugs, suggest improvements, follow PEP8, be strict but constructive, use {language} and {code_snippet}",
  "sample_input": "def calculate(x,y): return x/y"
}

// 3. SQL Query Generator
{
  "raw_input": "converts natural language to SQL, only output valid SQL, never guess table names, ask for schema if not provided, postgres syntax, use {schema} and {user_question}",
  "sample_input": "show me all users who signed up last month and made more than 3 purchases"
}

// 4. Content Moderation
{
  "raw_input": "classifies user content as safe/warning/remove, explain why flagged, handle sarcasm, use {content} and {platform_guidelines}",
  "sample_input": "This product is absolutely terrible, I want to kill whoever designed it"
}

// 5. Medical Symptom Triage
{
  "raw_input": "symptom checker, always recommend seeing doctor, never diagnose, flag emergencies immediately, calm tone, use {symptoms} and {patient_age}",
  "sample_input": "I have chest pain and my left arm feels numb for the past 20 minutes"
}
```

---

## How It Works — Step by Step

**1. You provide a raw requirement** in plain English. No structure needed.

**2. The Analyst Agent** calls `chat_json()` to parse your input into a structured `PromptSpec` — extracting objective, context, target model, variables, constraints, and examples.

**3. The HubManager** opens an AgentScope `MsgHub` and starts the refinement loop:
   - **Architect** receives the spec (round 1) or spec + previous draft + feedback (round N) and produces a system prompt using appropriate techniques (CoT, Few-shot, ReAct, CO-STAR)
   - **Critic** scores the draft across 5 criteria and issues `REVISE` or `PASSED`
   - Loop continues until score ≥ 8.5 or max rounds (6) reached

**4. The Executor Agent** runs the approved prompt against your sample input to produce a real-world output example.

**5. The Scorer** runs an independent LLM-as-a-Judge evaluation with weighted scoring across all 5 dimensions.

**6. The frontend** displays everything — score progression chart, per-dimension scorecard, full iteration log, final prompt with copy button, and executor output.

---

## Future Roadmap

- [ ] **Red Teamer Agent** — adversarial testing with prompt injection attempts
- [ ] **Prompt History** — save and compare optimization runs
- [ ] **Model Selection** — switch between LLaMA, Mixtral, Gemma from the UI
- [ ] **Export** — download final prompt as `.txt` or `.json`
- [ ] **Few-shot Generator** — auto-generate examples from spec

---

## License

MIT — free to use, modify, and distribute.

---

<div align="center">
  <sub>Built with AgentScope · Groq · FastAPI · Vanilla JS</sub>
</div>
