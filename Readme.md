# Account Research Agent

**Prepare a first discovery call in minutes.** Give it a company and what you sell; it researches public sources and returns a one-page brief: company snapshot, recent signals, likely priorities, where your offering could fit, and five discovery questions.

Built with [smolagents](https://github.com/huggingface/smolagents) as part of the [Hugging Face AI Agents Course](https://huggingface.co/learn/agents-course) (Unit 2.1).

## Demo

<!-- Drag the demo video here when editing this file on GitHub -->

## The idea behind it

Good discovery starts with the client's business problem, not with a predetermined solution. So the brief keeps three things apart:

| Section | What it is | Who it's about |
|---|---|---|
| **Recent signals** | Dated news with sources | Facts about the company |
| **Likely priorities** | Hypotheses to validate in the call | The client's business |
| **Where our offering could fit** | Our angle, to test only after the client talks | Us |

Discovery questions go from broad (the client's goals) to specific (the area where we could help), and never pitch.

## How it works

```
Company + Market + What you sell
          │
          ▼
   CodeAgent (smolagents)  ── Thought → Action → Observation loop
     ├─ web_search      → resilient search, falls back across engines
     ├─ visit_webpage   → skips PDFs, paywalls and empty pages
     └─ build_discovery_brief → enforces the brief's structure
          │
          ▼
   Discovery brief (Markdown, downloadable)
```

## Design decisions

**Critical rules live in code, not in the prompt.** Language models follow instructions most of the time, not all of the time. Whatever can be checked, is checked in code:

- **Date filter:** news older than 12 months is dropped and listed, so you can see if a priority relies on old news.
- **Structure:** exactly 5 questions, 3–5 priorities, at most 3 fit hypotheses. If the model breaks it, the tool rejects the brief and the agent fixes it.
- **The brief can't get lost:** the app reads it straight from the tool, even if the model passes the wrong thing to `final_answer`.
- **Step budget:** a `step_callback` tells the agent to stop researching and write the brief when it is close to its step limit.

**Resilient by design.**

- **Model fallback:** if the main model fails or is overloaded, requests go to a backup model automatically (`LiteLLMRouterModel`).
- **Search fallback:** if a search engine throttles the agent, the search tool tries other engines before giving up.

**Model-agnostic.** The model is a line in `.env`, not in the code.

## Run it locally

Requires Python 3.10+.

```bash
git clone https://github.com/pabloretes-arg/account-research-agent.git
cd account-research-agent
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your API keys to .env
python app.py
```

Open http://127.0.0.1:7860.

## Lessons learned

- **The agent pitched before listening.** Asked to tailor the brief to what we sell, it turned our product into the client's "priorities". Forbidding it in the prompt was not enough. Giving it a separate place for our angle (*Where our offering could fit*) worked much better.
- **Ambiguous names.** "Jumbo" can be a supermarket in Argentina, a toy store in Greece or a lottery company in Australia. The agent picked silently. Now a *Market* field resolves it, and the brief says which company it chose.
- **Market data is not company data.** "E-commerce grew 60%" was about the whole country, not the client. Repeating it in a meeting as their growth would be embarrassing. Signals must now be about the company itself.
- **Wasted steps.** The agent spent its budget on PDFs, paywalled sites and pages built with JavaScript. Skipping them in code was cheaper than explaining it in the prompt.
- **Free tiers are fragile.** Model providers return errors and search engines throttle. Fallbacks turn a failed run into a slower one.

## Limitations

- Public sources only. Always verify the brief before using it with a client.
- Free models make mistakes of judgment (e.g. mixing our pitch into the client's priorities). The [multi-agent version](#whats-next) adds a reviewer for that.

## What's next

This is part of a series built while taking the course:

1. **Account Research Agent**, single agent with smolagents (this repo)
2. **Multi-agent version**: a strategist, a researcher and a "sales manager" review, with smolagents (coming soon)
3. **Discovery Playbook RAG**, with LlamaIndex (coming soon)
4. **Meeting Prep Workflow**, with LangGraph (coming soon)

## Why smolagents

- **Code agents:** the agent writes Python to call its tools, so it can run several searches in one step.
- **Minimal abstractions:** easy to see and control every step, which made the code-enforced rules above simple to add.
- **Model-agnostic:** works with any provider through LiteLLM.

## Author

**Pablo Retes**, Buenos Aires. Built while taking the [Hugging Face AI Agents Course](https://huggingface.co/learn/agents-course).