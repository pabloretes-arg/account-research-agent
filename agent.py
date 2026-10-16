import os
from datetime import date, timedelta
from dotenv import load_dotenv
from smolagents import ActionStep, CodeAgent, FinalAnswerTool, LiteLLMModel, LiteLLMRouterModel
from tools import DiscoveryBriefTool, ResilientSearchTool, SafeVisitWebpageTool

load_dotenv()

# ---------- MODEL ----------
# The model is read from MODEL_ID in the .env file (see .env.example).
# To switch providers, change the .env, not the code.
MODEL_ID = os.getenv("MODEL_ID")
if not MODEL_ID:
    raise SystemExit("Missing MODEL_ID in .env. Copy .env.example to .env and fill it in.")

# Optional backups, comma-separated (e.g. FALLBACK_MODEL_IDS=gemini/gemini-flash-lite-latest).
# If the main provider fails or is overloaded, the request goes to the next model automatically.
FALLBACK_MODEL_IDS = [m.strip() for m in os.getenv("FALLBACK_MODEL_IDS", "").split(",") if m.strip()]


def build_model():
    if not FALLBACK_MODEL_IDS:
        return LiteLLMModel(model_id=MODEL_ID, max_tokens=4096)
    backups = [f"backup-{i}" for i in range(len(FALLBACK_MODEL_IDS))]
    model_list = [{"model_name": "main", "litellm_params": {"model": MODEL_ID}}] + [
        {"model_name": name, "litellm_params": {"model": model_id}}
        for name, model_id in zip(backups, FALLBACK_MODEL_IDS)
    ]
    return LiteLLMRouterModel(
        model_id="main",
        model_list=model_list,
        client_kwargs={"fallbacks": [{"main": backups}], "num_retries": 1},
        max_tokens=4096,
    )


model = build_model()

# ---------- TOOLS ----------
brief_tool = DiscoveryBriefTool()  # kept in a variable so app.py can read the brief

tools = [
    ResilientSearchTool(max_results=5),
    SafeVisitWebpageTool(max_output_length=8000),
    brief_tool,
    FinalAnswerTool(),
]

# ---------- INSTRUCTIONS ----------
TODAY = date.today()
CUTOFF = TODAY - timedelta(days=365)

INSTRUCTIONS = f"""
You are an account research assistant that helps B2B sales teams prepare for a first discovery call.
Today's date is {TODAY.isoformat()}.

Given a company name:
0. If several companies share that name, pick the most likely one using any country or industry
   hint, and say in the snapshot which one you chose and which others exist.
1. Search for the company's official website and recent news.
2. Visit the 1-3 most relevant pages to confirm key facts.
3. Build the brief and return it in the same code block:
   brief = build_discovery_brief(...)
   final_answer(brief)

Rules:
- Only state facts you found in your sources. If you can't find something, say "not found".
  Never invent numbers, names or dates.
- Only include news dated on or after {CUTOFF.isoformat()}.
- Copy URLs exactly as they appear in search results or pages. Never edit domains or add accents.
  Link each signal to its own article, not to a general news page.
- Keep facts and inferences separate: likely priorities and questions are your hypotheses.
- Recent signals must be about this company. General market data (e.g. "e-commerce grew 60%
  in the country") is context: mention it in the snapshot as market context, never as the company's own data.
- If a group has several country units (e.g. Cencosud), only use facts about the unit in our market.
  Don't mix in founding dates, store counts or figures from other countries.
- Likely priorities are the company's business priorities, not our sales pitch.
  Never phrase a priority in terms of what we sell. Our angle goes only in where_we_fit.
- Discovery questions must be what a seller would ask the buyer: open-ended questions about
  their operations, current processes, challenges and goals. Never ask for confidential
  figures or targets.
- Order the questions from broad to specific: start with the company's goals and initiatives,
  then explore the area where our offering could help. Never pitch inside a question.
- If the user says what they sell, tailor the likely priorities and discovery questions
  to that offering.
- When searching for news, include the current year in the query.
- Keep searches efficient: don't repeat the same search. If web search fails,
  visit the company's website and newsroom directly.
- You have a budget of about 8 research steps. You can run several searches or visits
  in one code block. Prefer news articles: online store homepages and PDFs are usually unreadable.
"""

# ---------- STEP BUDGET ----------
# Enforced in code: near the step limit, the agent is told to stop researching and write the brief
MAX_STEPS = 12
WRAP_UP_AT = MAX_STEPS - 3


def budget_reminder(step: ActionStep, agent) -> None:
    if step.step_number >= WRAP_UP_AT and brief_tool.last_brief is None:
        left = MAX_STEPS - step.step_number
        step.observations = (step.observations or "") + (
            f"\n\nBUDGET: only {left} step(s) left. Stop researching now. "
            "Call build_discovery_brief with what you already found and pass the result to final_answer."
        )


# ---------- AGENT ----------
agent = CodeAgent(
    model=model,
    tools=tools,
    instructions=INSTRUCTIONS,
    max_steps=MAX_STEPS,
    step_callbacks=[budget_reminder],
    verbosity_level=1,
)

if __name__ == "__main__":
    agent.run("Research the company Ualá (Argentina).")