#!/usr/bin/env python3
"""Generate the ablation figure for the SciPy 2026 paper.

Reads the committed result reports and renders a two-panel grouped bar chart:
  (a) evaluation safety dimension added by Step-1 domain context (both datasets);
  (b) pass / solve rate, baseline vs domain-aware (FinanceBench: this work;
      ScienceAgentBench: the benchmark's published expert-knowledge ablation).

Run from the repo root:  python3 results/make_ablation_figure.py
Writes: results/ablation.png  (and a copy into the paper dir if it exists).
"""
import json
import os
import shutil

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(__file__)


def load(path):
    with open(os.path.join(HERE, path)) as f:
        return json.load(f)


def n_safety(report):
    """Count safety-boundary cases in a stripped/full eval_report."""
    return sum(1 for r in report.get("results", []) if r.get("kind") == "safety_boundary")


fb_with = load("financebench_aggregate.json")
fb_without = load("financebench_nocontext_aggregate.json")
sab_with = load("sab/eval_report.json")
sab_without = load("sab_nocontext/eval_report.json")

# --- data ---------------------------------------------------------------
# Panel (a): safety-boundary tests in the generated evaluation
safety_without = [n_safety(fb_without), n_safety(sab_without)]
safety_with = [n_safety(fb_with), n_safety(sab_with)]

# Panel (b): pass / solve rate, baseline vs domain-aware.
# FinanceBench = this work's ablation; ScienceAgentBench = published 32%->42%
# expert-knowledge gap (Chen et al. 2024), which our DomainContext automates.
rate_baseline = [fb_without["pass_rate"], 0.32]
rate_domain = [fb_with["pass_rate"], 0.42]

GREY = "#9aa0a6"   # baseline / without context
BLUE = "#1a73e8"   # with domain context

fig, (axA, axB) = plt.subplots(1, 2, figsize=(9.2, 3.7))
x = np.arange(2)
w = 0.36

# Panel (a) ---------------------------------------------------------------
axA.bar(x - w / 2, safety_without, w, label="Without domain context", color=GREY)
axA.bar(x + w / 2, safety_with, w, label="With domain context", color=BLUE)
axA.set_xticks(x)
axA.set_xticklabels(["FinanceBench", "ScienceAgentBench"])
axA.set_ylabel("Safety-boundary tests")
axA.set_title("(a) Evaluation safety dimension\nadded by Step-1 domain context")
axA.set_ylim(0, 6.6)
for i in range(2):
    axA.text(i - w / 2, safety_without[i] + 0.12, str(safety_without[i]), ha="center", va="bottom", fontsize=9)
    axA.text(i + w / 2, safety_with[i] + 0.12, str(safety_with[i]), ha="center", va="bottom", fontsize=9)
axA.legend(frameon=False, fontsize=8, loc="upper center")

# Panel (b) ---------------------------------------------------------------
axB.bar(x - w / 2, rate_baseline, w, label="Baseline", color=GREY)
axB.bar(x + w / 2, rate_domain, w, label="Domain-aware", color=BLUE)
axB.set_xticks(x)
axB.set_xticklabels(["FinanceBench\n(this work)", "ScienceAgentBench\n(published)"])
axB.set_ylabel("Pass / solve rate")
axB.set_title("(b) Pass / solve rate:\nbaseline vs domain-aware")
axB.set_ylim(0, 0.75)
for i in range(2):
    axB.text(i - w / 2, rate_baseline[i] + 0.01, f"{rate_baseline[i]:.0%}", ha="center", va="bottom", fontsize=9)
    axB.text(i + w / 2, rate_domain[i] + 0.01, f"{rate_domain[i]:.0%}", ha="center", va="bottom", fontsize=9)
axB.legend(frameon=False, fontsize=8, loc="upper left")

for ax in (axA, axB):
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

fig.tight_layout()
out = os.path.join(HERE, "ablation.png")
fig.savefig(out, dpi=200, bbox_inches="tight")
print("wrote", out)

# copy into the paper dir so MyST can include it
paper = os.path.expanduser(
    "~/Desktop/scipy_proceedings/papers/shivika_bisen/ablation.png"
)
if os.path.isdir(os.path.dirname(paper)):
    shutil.copy(out, paper)
    print("copied to", paper)
