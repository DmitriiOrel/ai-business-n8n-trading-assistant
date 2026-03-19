from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd


def plot_ab_performance(df: pd.DataFrame, output_path: Path, days: int = 30) -> None:
    view = df.tail(days).copy()
    if view.empty:
        raise ValueError("Not enough rows to build A/B chart")

    view = view.reset_index(drop=True)
    x = range(len(view))

    fig, ax = plt.subplots(figsize=(11, 5))

    for i, row in view.iterrows():
        color = "#d2ecff" if row["daily_b"] >= row["daily_a"] else "#ffd8d8"
        ax.axvspan(i - 0.5, i + 0.5, color=color, alpha=0.4, zorder=0)

    # Draw Strategy B first, then Strategy A on top with a dashed style.
    ax.plot(
        x,
        view["cum_b"],
        label="Strategy B (LLM + TA)",
        linewidth=2.4,
        color="#ff7f0e",
        alpha=0.90,
        zorder=2,
    )
    ax.plot(
        x,
        view["cum_a"],
        label="Strategy A (baseline)",
        linewidth=2.0,
        linestyle="--",
        marker="o",
        markersize=3.5,
        color="#1f77b4",
        alpha=0.95,
        zorder=3,
    )

    step = max(1, len(view) // 8)
    ax.set_xticks(list(x)[::step])
    ax.set_xticklabels(view["date"].astype(str).tolist()[::step], rotation=30, ha="right")
    ax.set_ylabel("Cumulative return")
    ax.set_title("A vs B Performance (last 30 days)")
    ax.legend()
    ax.grid(True, alpha=0.2)
    fig.tight_layout()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
