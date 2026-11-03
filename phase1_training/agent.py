"""
Well Log Analyst Agent (Volve field, Hugin Fm.)

Evaluates the Hugin reservoir in Volve wells from raw logs with Equinor's own equations
and parameters, then compares the result with Equinor's interpretation.

Run (from the well_log_agent_standalone folder):
    uv run python phase1_training/agent.py            # chat
    uv run python phase1_training/agent.py --check    # test the tools, no LLM
"""

import sys
from functools import cache

from deepagents import FilesystemPermission, create_deep_agent
from deepagents.backends import CompositeBackend, FilesystemBackend, StateBackend
from langgraph.checkpoint.memory import MemorySaver

from config import MEMORY_DIR, REPORTS_DIR, SKILLS_DIR
from prompts import SYSTEM_PROMPT, WELL_ANALYST_PROMPT
from tools import TOOLS, analyze_well, compare_with_equinor, list_wells

REPORTS_DIR.mkdir(exist_ok=True)

# Reports, memory and skills live on disk; anything else is scratch space in the chat (Lesson 2.2)
backend = CompositeBackend(
    default=StateBackend(),
    routes={
        "/reports/": FilesystemBackend(root_dir=str(REPORTS_DIR), virtual_mode=True),
        "/memories/": FilesystemBackend(root_dir=str(MEMORY_DIR), virtual_mode=True),
        "/skills/": FilesystemBackend(root_dir=str(SKILLS_DIR), virtual_mode=True),
    },
)


@cache
def build_agent():
    """Build the agent (and its models) the first time it is needed, so --check needs no API key."""
    from models import model

    try:  # a lighter model for the subagent; set `light_model` in models.py to change it
        from models import light_model
    except ImportError:
        light_model = "groq:openai/gpt-oss-20b"

    # Subagent: reviews many wells in its own context and returns one table (Lessons 4.1, 4.2)
    well_analyst = {
        "name": "well-analyst",
        "description": "Reviews several Volve wells and returns ONE compact table, one row per well. "
                       "Use it for field reviews or for comparing many wells.",
        "system_prompt": WELL_ANALYST_PROMPT,
        "tools": [list_wells, analyze_well, compare_with_equinor],
        "model": light_model,
    }

    return create_deep_agent(
        model=model,
        system_prompt=SYSTEM_PROMPT,
        tools=TOOLS,
        subagents=[well_analyst],
        backend=backend,
        memory=["/memories/AGENTS.md"],                     # Lesson 3.3
        skills=["/skills/"],                                # Lesson 3.2
        permissions=[FilesystemPermission(operations=["write"], paths=["/skills/**"], mode="deny")],
        interrupt_on={                                      # Lesson 1.8
            "write_file": {"allowed_decisions": ["approve", "edit", "reject"]},
            "edit_file": {"allowed_decisions": ["approve", "edit", "reject"]},
        },
        checkpointer=MemorySaver(),                         # Lesson 1.7
        name="Well_Log_Agent",
    )


def __getattr__(name):
    """`from agent import agent` still works: the agent is built here, on first use (PEP 562)."""
    if name == "agent":
        return build_agent()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if __name__ == "__main__":
    from chat import chat, check
    check() if "--check" in sys.argv else chat(build_agent())
