import os
import re
import tempfile
import unicodedata
from pathlib import Path

import gradio as gr
from smolagents.memory import ActionStep

from agent import agent, brief_tool

def build_task(company: str, market: str, offering: str) -> str:
    task = f"Research the company {company.strip()}."
    if market.strip():
        task += (
            f" Our market is {market.strip()}: if several companies share that name, "
            "prefer the one operating there."
        )
    if offering.strip():
        task += f" We sell {offering.strip()}."
    return task


def describe_step(step: ActionStep) -> str:
    """One readable block per agent step: code it ran, time, and errors."""
    status = "❌ error" if step.error else "✅"
    duration = getattr(step.timing, "duration", None)
    header = f"**Step {step.step_number}** · {status}" + (f" · {duration:.1f}s" if duration else "")
    code = (step.code_action or "").strip()
    block = f"{header}\n```python\n{code}\n```" if code else header
    if step.error:
        first_line = str(step.error).splitlines()[0][:200]
        block += f"\n> {first_line}"
    return block


def save_brief(company: str, brief: str) -> str:
    plain = unicodedata.normalize("NFKD", company).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", plain.lower()).strip("-") or "company"
    path = Path(tempfile.gettempdir()) / f"discovery-brief-{slug}.md"
    path.write_text(brief.replace("\\$", "$"), encoding="utf-8")
    return str(path)


def run_agent(company: str, market: str, offering: str):
    if not company.strip():
        raise gr.Error("Enter a company name.")

    brief_tool.last_brief = None
    steps = []
    hidden = gr.update(visible=False)
    yield "⏳ Researching... this usually takes 1-2 minutes.", "", hidden

    try:
        for event in agent.run(build_task(company, market, offering), stream=True):
            if isinstance(event, ActionStep):
                steps.append(describe_step(event))
                yield f"⏳ Researching... step {event.step_number} done.", "\n\n".join(steps), hidden
    except Exception as error:
        # Usually the model provider is down or rate-limited, not a bug in the agent
        print(f"Agent run failed: {error}")
        yield (
            "⚠️ The model provider didn't respond (it may be overloaded). "
            "Wait a minute and try again.",
            "\n\n".join(steps),
            hidden,
        )
        return

    brief = brief_tool.last_brief
    if not brief:
        yield "⚠️ The agent finished without building a brief. Please try again.", "\n\n".join(steps), hidden
        return

    yield brief, "\n\n".join(steps), gr.update(value=save_brief(company, brief), visible=True)


CSS = """
.gradio-container {max-width: 860px !important; margin: 0 auto !important;}
#run-btn {background: #18181b; color: #fff; border: none; font-weight: 500;}
#run-btn:hover {background: #3f3f46;}
#brief {padding-top: 8px;}
footer {display: none !important;}
#author, #author * {text-align: center; color: #a1a1aa !important; font-size: 13px !important;}
#author {margin-top: 24px;}
"""

THEME = gr.themes.Base(
    primary_hue="zinc",
    neutral_hue="zinc",
    font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
    radius_size="sm",
)

with gr.Blocks(title="Account Research Agent") as demo:
    gr.Markdown(
        "## Account Research Agent\n"
        "Public-source brief for a first discovery call: snapshot, recent signals, "
        "likely priorities and questions."
    )

    with gr.Row():
        company = gr.Textbox(
            label="Company",
            info="e.g. Ualá, Jumbo, Despegar",
            scale=2,
        )
        market = gr.Textbox(
            label="Market",
            value=os.getenv("DEFAULT_MARKET", ""),  # set your default in .env
            info="For ambiguous names",
            scale=1,
        )
        offering = gr.Textbox(
            label="What do you sell? (optional)",
            info="e.g. payment reconciliation software for finance teams",
            scale=3,
        )
    with gr.Row():
        run_btn = gr.Button("Generate brief", elem_id="run-btn", size="md", scale=0, min_width=160)

    brief_md = gr.Markdown(latex_delimiters=[], elem_id="brief")  # "$" = money, not math
    download = gr.DownloadButton("Download brief (.md)", visible=False, size="sm", variant="secondary")

    with gr.Accordion("How the agent worked", open=False):
        steps_md = gr.Markdown(latex_delimiters=[])

    gr.Markdown("Author: Pablo Retes, Buenos Aires", elem_id="author")

    for trigger in (run_btn.click, company.submit, market.submit, offering.submit):
        trigger(run_agent, inputs=[company, market, offering], outputs=[brief_md, steps_md, download])

if __name__ == "__main__":
    demo.launch(share=False, theme=THEME, css=CSS)