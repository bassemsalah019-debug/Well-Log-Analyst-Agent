"""Chat with the agent in the terminal, approve/edit/reject file writes, and the no-LLM tool check."""

import os
import subprocess
import tempfile
from pathlib import Path

from langgraph.types import Command

from las_io import available_wells
from memory import memory_settings
from tools import analyze_well, compare_with_equinor, describe_well


def edit_in_editor(text: str) -> str:
    """Open the text in Notepad (Windows) or $EDITOR, wait until it is closed, return the new text."""
    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8") as tmp:
        tmp.write(text)
        path = tmp.name
    editor = "notepad" if os.name == "nt" else os.environ.get("EDITOR", "nano")
    print(f" Opening the draft in {editor}. Edit it, save, and close the window to continue.")
    subprocess.run([editor, path])
    new_text = Path(path).read_text(encoding="utf-8")
    os.remove(path)
    return new_text


def ask_approval(requests) -> list[dict]:
    """Show each pending file write and let the user approve, edit or reject it."""
    decisions = []
    for req in requests:
        args = dict(req["args"])
        key = "content" if "content" in args else "new_string"
        print(f"\n The agent wants to {req['name']}: {args.get('file_path') or args.get('path')}")
        print("─" * 50)
        print((args.get(key) or "")[:4000])
        print("─" * 50)

        choice = input("approve / edit / reject? ").strip().lower()
        if choice.startswith("e"):
            args[key] = edit_in_editor(args.get(key) or "")
            decisions.append({"type": "edit", "edited_action": {"name": req["name"], "args": args}})
        elif "approve" in choice or choice in ("y", "yes"):
            decisions.append({"type": "approve"})
        else:
            decisions.append({"type": "reject", "message": "The user rejected this file. Ask what to change."})
    return decisions


def show_tool_calls(messages) -> None:
    """Print every tool the model called in this turn."""
    for msg in messages:
        if msg.type == "ai" and msg.tool_calls:
            for call in msg.tool_calls:
                shown = {k: (str(v)[:80] + "..." if len(str(v)) > 80 else v)
                         for k, v in call["args"].items() if k != "content"}
                print(f"  🔧 {call['name']} {shown}")


def chat(agent) -> None:
    session, seen = 1, 0
    config = {"configurable": {"thread_id": f"well-session-{session}"}}
    print("🛢️ Well Log Agent (Volve, Hugin Fm.) ready. Type 'new' for a fresh conversation, 'exit' to quit.")

    while True:
        user_input = input("\nYou: ").strip()
        if user_input.lower() in ("exit", "quit"):
            break
        if not user_input:
            continue
        if user_input.lower() == "new":
            session, seen = session + 1, 0
            config = {"configurable": {"thread_id": f"well-session-{session}"}}
            print(" New conversation started (memory is kept).")
            continue

        try:
            result = agent.invoke({"messages": [{"role": "user", "content": user_input}]},
                                  config=config, version="v2")
            while result.interrupts:          # the agent paused before writing a file
                decisions = ask_approval(result.interrupts[0].value["action_requests"])
                result = agent.invoke(Command(resume={"decisions": decisions}), config=config, version="v2")
        except Exception as e:
            text = str(e)
            if "413" in text or "rate_limit" in text:
                print(" The model's limit was reached. Type 'new' for a fresh conversation, or wait a minute.")
                print(f" Details: {text[:300]}")
            else:
                print(f" Error: {e}")
            continue

        messages = result.value["messages"]
        show_tool_calls(messages[seen:])
        seen = len(messages)
        print(f"\nAgent: {messages[-1].text}")


def check() -> None:
    """Run the tools on every well without any LLM."""
    print("Field settings from memory:", memory_settings()["field"])
    print()
    for well in available_wells():
        print("=" * 70)
        print(describe_well.invoke({"well_name": well}))
        print("-" * 70)
        print(analyze_well.invoke({"well_name": well}))
        print("-" * 70)
        print(compare_with_equinor.invoke({"well_name": well}))
    print("=" * 70)
