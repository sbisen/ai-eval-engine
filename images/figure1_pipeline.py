"""Render images/figure1.png — the AI Eval Engine pipeline (simple version).

    python images/figure1_pipeline.py

Green = built & tested today. Grey/dashed = planned.
"""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch  # noqa: E402

INK = "#1b2733"
MUTED = "#5b6b7b"
DONE = "#1f9d63"
DONE_BG = "#e9f7ef"
PLAN = "#9aa7b4"
PLAN_BG = "#f1f3f5"
SAB = "#2f6db0"
SAB_BG = "#eaf1f9"
FB = "#b0632f"
FB_BG = "#f9f0ea"

plt.rcParams["font.family"] = "DejaVu Sans"

fig, ax = plt.subplots(figsize=(9, 11.5), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")


def box(x, y, w, h, fc, ec, dashed=False, lw=1.8):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle="round,pad=0.02,rounding_size=2",
        fc=fc, ec=ec, lw=lw, linestyle="--" if dashed else "-", zorder=2,
    ))


def text(x, y, s, size=12, color=INK, weight="normal"):
    ax.text(x, y, s, fontsize=size, color=color, weight=weight,
            ha="center", va="center", zorder=4)


def step(y, h, tag, title, sub, done):
    fc, ec = (DONE_BG, DONE) if done else (PLAN_BG, PLAN)
    box(15, y, 70, h, fc, ec, dashed=not done)
    text(50, y + h - 2.4, f"{tag}  {title}", size=12, weight="bold",
         color=DONE if done else INK)
    text(50, y + 1.9, sub, size=9.2, color=MUTED)


def arrow(x1, y1, x2, y2, color=MUTED, dashed=False):
    ax.add_patch(FancyArrowPatch(
        (x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=18,
        color=color, lw=1.9, linestyle="--" if dashed else "-", zorder=1,
    ))


text(50, 97, "AI Eval Engine", size=20, weight="bold")

# datasets
box(9, 85, 38, 8.5, SAB_BG, SAB)
text(28, 90.7, "ScienceAgentBench", size=12, weight="bold", color=SAB)
text(28, 87.4, "scored by running code", size=9.2, color=MUTED)

box(53, 85, 38, 8.5, FB_BG, FB)
text(72, 90.7, "FinanceBench", size=12, weight="bold", color=FB)
text(72, 87.4, "scored by grounding", size=9.2, color=MUTED)

arrow(28, 85, 44, 79.5, color=SAB)
arrow(72, 85, 56, 79.5, color=FB)

# interface
box(15, 71, 70, 8, "#ffffff", INK, lw=1.6)
text(50, 76.4, "Your data: CSV + config", size=12.5, weight="bold")
text(50, 73.2, "same interface for any dataset", size=9.2, color=MUTED)
arrow(50, 71, 50, 65.5, color=INK)

# the five steps
steps = [
    (57.5, 7.5, "Step 1", "Domain Context Ingestion",
     "extract a typed DomainContext from a sample", True),
    (47.5, 7.5, "Step 2", "Golden Set Generation",
     "build versioned, domain-grounded test cases", True),
    (37.5, 7.5, "Step 3", "Eval Script + Scoring",
     "run & score: execute code / check grounding", True),
    (27.5, 7.5, "Step 4", "Safety Runbook",
     "cluster failures into reusable safety rules", True),
    (17.5, 7.5, "Step 5", "Monitoring",
     "self-contained index.html dashboard", True),
]
for i, (y, h, tag, title, sub, done) in enumerate(steps):
    step(y, h, tag, title, sub, done)
    if i < len(steps) - 1:
        nxt_done = steps[i + 1][5]
        arrow(50, y, 50, y - 2.5, color=PLAN if not nxt_done else DONE,
              dashed=not nxt_done)

# legend
ax.add_patch(FancyBboxPatch((28, 7), 3, 2.2, boxstyle="round,pad=0.02",
             fc=DONE_BG, ec=DONE, lw=1.4))
text(52, 8.1, "all steps built & tested · runs offline", size=9.2, color=INK)

plt.tight_layout(pad=0.4)
fig.savefig("images/figure1.png", bbox_inches="tight", facecolor="white")
print("wrote images/figure1.png")
