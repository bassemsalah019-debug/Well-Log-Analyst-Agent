"""
Evaluate the Well Log Agent (Volve, Hugin Fm.) in two parts:
  A) Tools, no LLM (free): run analyze_well and compare_with_equinor on every well and check the
     results against Equinor's report averages and Equinor's curves.
  B) Behavior (uses the LLM): does the agent call the right tools, refuse what it should refuse,
     keep to the tool numbers, and pause before saving a report?

Run (from the well_log_agent_standalone folder):
    uv run python phase1_training/eval_agent.py --tools             # Part A only
    uv run python phase1_training/eval_agent.py --behavior          # Part B only
    uv run python phase1_training/eval_agent.py --behavior 1,2,7    # some cases only
"""

import re
import sys
import time

from las_io import available_wells, find_well
from tools import analyze_well, compare_with_equinor

# ── Equinor's report averages: Hugin Fm., net sand ───────────────
# Copied from the "Averages" tables in each well's PETROPHYSICAL_REPORT PDF.
# They live ONLY here, never in the agent's memory, so the agent cannot see the answers.
REPORT_AVERAGES = {
    "F-1_A":   {"NG": 0.692, "PHIF": 0.168, "SW": 0.899},
    "F-1_B":   {"NG": 0.906, "PHIF": 0.202, "SW": 0.363},
    "F-1_C":   {"NG": 0.809, "PHIF": 0.209, "SW": 0.365},
    "F-11_A":  {"NG": 0.862, "PHIF": 0.209, "SW": 0.323},
    "F-11_B":  {"NG": 0.888, "PHIF": 0.207, "SW": 0.232},
    "F-11_T2": {"NG": 0.808, "PHIF": 0.168, "SW": 0.934},
    "F-12":    {"NG": 0.813, "PHIF": 0.230, "SW": 0.154},
    "F-15_D":  {"NG": 0.786, "PHIF": 0.208, "SW": 0.265},
}

# Tolerances: typical uncertainty of log-derived averages, fixed before this check.
# They are NOT tuned to make wells pass; every difference is printed anyway.
TOLERANCE = {"NG": 0.05, "PHIF": 0.02, "SW": 0.05}


# ── Part A: tools against Equinor (no LLM) ───────────────────────
def number(pattern: str, text: str) -> float | None:
    found = re.search(pattern, text)
    return float(found.group(1)) if found else None


def eval_tools() -> None:
    print("=" * 78)
    print("PART A1: agent results vs Equinor's report averages (Hugin Fm., net sand)")
    print("=" * 78)
    print(f"{'Well':8} {'N/G ours/report':>18} {'PHIF ours/report':>19} {'SW ours/report':>17}   Result")
    passed = 0
    for well, ref in REPORT_AVERAGES.items():
        out = analyze_well.invoke({"well_name": well})
        ours = {
            "NG": number(r"N/G = ([\d.]+)", out),
            "PHIF": number(r"Net sand averages: PHIF = ([\d.]+)", out),
            "SW": number(r"SW \(pore-volume weighted\) = ([\d.]+)", out),
        }
        if None in ours.values():
            print(f"{well:8} could not read the tool output:\n{out}")
            continue
        fails = [k for k in ref if abs(ours[k] - ref[k]) > TOLERANCE[k]]
        passed += not fails
        cells = [f"{ours[k]:.3f} / {ref[k]:.3f}" for k in ("NG", "PHIF", "SW")]
        result = "PASS ✅" if not fails else "FAIL ❌ (" + ", ".join(f"{k} off by {abs(ours[k] - ref[k]):.3f}" for k in fails) + ")"
        print(f"{well:8} {cells[0]:>18} {cells[1]:>19} {cells[2]:>17}   {result}")
    print(f"\n  -> {passed}/{len(REPORT_AVERAGES)} wells within tolerance "
          f"(N/G ±{TOLERANCE['NG']}, PHIF ±{TOLERANCE['PHIF']}, SW ±{TOLERANCE['SW']})")

    print("\n" + "=" * 78)
    print("PART A2: depth-by-depth difference from Equinor's curves (mean absolute difference)")
    print("=" * 78)
    print(f"{'Well':8} {'VSH':>7} {'PHIF':>7} {'SW':>7} {'Net sand agreement':>20} {'N/G diff from curves':>21} {'from hand edits':>16}")
    for well in available_wells():
        out = compare_with_equinor.invoke({"well_name": well})
        if "has no Hugin" in out:
            print(f"{well:8} no Hugin Fm. (correctly skipped)")
            continue
        mae = {c: number(rf"{c}: \d+ depths, mean absolute difference = ([\d.]+)", out) for c in ("VSH", "PHIF", "SW")}
        agree = re.search(r"SAND_FLAG at (\d+%)", out)
        split = re.search(r"([+-][\d.]+) comes from our curves.*?([+-][\d.]+) comes from Equinor's SAND_FLAG", out)
        row = " ".join(f"{(f'{v:.3f}' if v is not None else '-'):>7}" for v in mae.values())
        print(f"{well:8} {row} {(agree.group(1) if agree else 'no flag'):>20} "
              f"{(split.group(1) if split else '-'):>21} {(split.group(2) if split else '-'):>16}")
    print()


# ── Part B: behavior test cases (uses the LLM) ───────────────────
CASES = [
    {
        "name": "Checks the curves first",
        "prompt": "What curves does well F-15 D have?",
        "must_call": ["describe_well"],
        "must_contain_any": ["gr", "rhob"],
    },
    {
        "name": "Uses the tool numbers and writes no report",
        "prompt": "Analyze well F-15 D.",
        "must_call": ["analyze_well"],
        "must_not_call": ["write_file"],
        "answer_uses_tool_number": r"N/G = ([\d.]+)",
        "must_not_contain": ["laterally continuous"],
    },
    {
        "name": "Explains the Equinor comparison without inventing causes",
        "prompt": "Analyze well F-15 D and tell me how close it is to Equinor.",
        "must_call": ["analyze_well", "compare_with_equinor"],
        "must_not_contain": ["without the extra neutron correction", "without any extra neutron correction",
                             "without the neutron correction", "phif is slightly higher because of rt"],
    },
    {
        "name": "Says when a well has no Hugin Fm.",
        "prompt": "Analyze well F-1.",
        "must_contain_any": ["no hugin", "does not have hugin", "doesn't have hugin", "not have a hugin", "outside"],
    },
    {
        "name": "Handles a well with no data",
        "prompt": "Analyze well F-99.",
        "must_contain_any": ["no data", "not available", "available wells", "does not exist", "not found", "no well"],
    },
    {
        "name": "Refuses out-of-scope questions",
        "prompt": "How do I bake a chocolate cake?",
        "must_not_call": ["list_wells", "describe_well", "analyze_well", "compare_with_equinor"],
        "must_contain_any": ["well", "petrophysic", "only help"],
    },
    {
        "name": "Pauses for approval before saving a report",
        "prompt": "Write a report for well F-1 B.",
        "expect_approval_under": "/reports/",
    },
    {
        "name": "Delegates a field review to the subagent",
        "prompt": "Review all wells in the field.",
        "must_call": ["task"],
    },
    {
        "name": "Subagent table matches the tools' numbers",
        "prompt": "Review all wells in the field.",   # same prompt as case 8: its run is reused, no extra tokens
        "must_call": ["task"],
        "subagent_matches_tools": True,
    },
]


def clean(text: str) -> str:
    """Lower case, and turn the model's special hyphens into normal ones."""
    return re.sub(r"[\u2010-\u2015\u2212]", "-", text).lower()


def tool_numbers(well: str) -> dict:
    """N/G, PHIF and SW of one well, straight from analyze_well (no LLM)."""
    out = analyze_well.invoke({"well_name": well})
    return {"NG": number(r"N/G = ([\d.]+)", out),
            "PHIF": number(r"Net sand averages: PHIF = ([\d.]+)", out),
            "SW": number(r"SW \(pore-volume weighted\) = ([\d.]+)", out)}


def same_number(written: str, exact: float) -> bool:
    """True if `written` is the tool's number, at most rounded to fewer decimals (0.823 -> 0.82 is fine)."""
    decimals = len(written.split(".")[1]) if "." in written else 0
    return abs(float(written) - exact) <= 0.5 * 10 ** -decimals + 1e-9


def check_subagent_table(messages) -> list[str]:
    """Compare every number in the subagent's table with analyze_well, well by well."""
    task_ids = {c["id"] for m in messages if m.type == "ai" for c in (m.tool_calls or []) if c["name"] == "task"}
    replies = [m.text for m in messages if m.type == "tool"
               and (getattr(m, "name", "") == "task" or getattr(m, "tool_call_id", None) in task_ids)]
    if not replies:
        return ["no reply from the subagent"]
    problems, rows_found = [], set()
    for line in replies[-1].splitlines():
        cells = [c.strip().strip("*") for c in line.strip().strip("|").split("|")]
        well = find_well(cells[0]) if len(cells) >= 4 else None
        if not well:
            continue
        expected = tool_numbers(well)
        if expected["NG"] is None:        # e.g. F-1: no Hugin, nothing to check
            continue
        rows_found.add(well)
        for key, cell in zip(("NG", "PHIF", "SW"), cells[1:4]):
            written = re.search(r"-?\d+\.\d+", cell)
            if not written:
                problems.append(f"{well} {key}: no number in '{cell}'")
            elif not same_number(written.group(0), expected[key]):
                problems.append(f"{well} {key}: table says {written.group(0)}, the tool says {expected[key]}")
    hugin_wells = {w for w in available_wells() if tool_numbers(w)["NG"] is not None}
    for well in sorted(hugin_wells - rows_found):
        problems.append(f"{well} is missing from the table")
    return problems


_runs = {}   # prompt -> result, so two cases with the same prompt share one agent run


def run_case(number_: int, case: dict) -> tuple[list[str], list[str]]:
    """Run one case in its own thread and return (problems, tools_called)."""
    if case["prompt"] in _runs:
        result = _runs[case["prompt"]]
    else:
        from agent import agent   # built on first use, so Part A (--tools) needs no API key
        config = {"configurable": {"thread_id": f"eval-{number_}"}}
        result = agent.invoke({"messages": [{"role": "user", "content": case["prompt"]}]},
                              config=config, version="v2")
        _runs[case["prompt"]] = result
    messages = result.value["messages"]
    called = [call["name"] for msg in messages if msg.type == "ai" for call in (msg.tool_calls or [])]
    answer = clean(messages[-1].text)

    problems = []
    for name in case.get("must_call", []):
        if name not in called:
            problems.append(f"did not call {name}")
    for name in case.get("must_not_call", []):
        if name in called:
            problems.append(f"should not call {name}")
    words = case.get("must_contain_any")
    if words and not any(w in answer for w in words):
        problems.append(f"answer has none of {words}")
    for phrase in case.get("must_not_contain", []):
        if phrase in answer:
            problems.append(f"answer says '{phrase}'")
    if "answer_uses_tool_number" in case:
        tool_text = " ".join(m.text for m in messages if m.type == "tool")
        found = re.search(case["answer_uses_tool_number"], tool_text)
        if not found:
            problems.append("the tool returned no number to check")
        elif found.group(1) not in answer:
            problems.append(f"answer does not use the tool's number ({found.group(1)})")
    if case.get("subagent_matches_tools"):
        problems += check_subagent_table(messages)
    if "expect_approval_under" in case:
        requests = result.interrupts[0].value["action_requests"] if result.interrupts else []
        paths = [r["args"].get("file_path") or "" for r in requests]
        if not any(p.startswith(case["expect_approval_under"]) for p in paths):
            problems.append(f"did not pause before writing a file under {case['expect_approval_under']}")
    return problems, called


def eval_behavior(selected: list[int] | None = None) -> None:
    print("=" * 78)
    print("PART B: behavior test cases")
    print("=" * 78)
    chosen = [(i, c) for i, c in enumerate(CASES, start=1) if not selected or i in selected]
    passed = 0
    for number_, case in chosen:
        reused = case["prompt"] in _runs
        try:
            problems, called = run_case(number_, case)
        except Exception as e:
            problems, called = [f"error: {str(e)[:200]}"], []
        passed += not problems
        print(f"\n[{number_}] {case['name']}: {'PASS ✅' if not problems else 'FAIL ❌'}")
        print(f"    tools called: {called or 'none'}")
        for problem in problems:
            print(f"    - {problem}")
        if not reused:
            time.sleep(20)  # stay under the provider's per-minute limit
    print(f"\n  -> {passed}/{len(chosen)} test cases passed\n")


if __name__ == "__main__":
    args = sys.argv[1:]
    run_all = not args
    if run_all or "--tools" in args:
        eval_tools()
    if run_all or "--behavior" in args:
        picked = None
        if "--behavior" in args:
            i = args.index("--behavior")
            if i + 1 < len(args) and re.fullmatch(r"[\d,]+", args[i + 1]):
                picked = [int(x) for x in args[i + 1].split(",")]
        eval_behavior(picked)