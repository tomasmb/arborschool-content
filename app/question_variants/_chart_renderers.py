"""Matplotlib chart renderers for variant image generation.

Each renderer takes a ``data`` dict (extracted by the LLM classifier)
and returns PNG bytes. Shared rendering boilerplate is centralised
in ``_render_to_png``.
"""

from __future__ import annotations

import io
from collections import Counter
from collections.abc import Callable
from typing import Any

_FONT_LABEL = {"fontsize": 13, "fontweight": "bold"}
_TICK_SIZE = 11


def _render_to_png(
    draw_fn: Callable[..., None],
    data: dict[str, Any],
    *,
    figsize: tuple[float, float] = (8, 5),
    dpi: int = 150,
) -> bytes:
    """Create a figure, call *draw_fn(fig, ax, data)*, return PNG."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
    draw_fn(fig, ax, data)
    plt.tight_layout()

    buf = io.BytesIO()
    fig.savefig(
        buf, format="png", bbox_inches="tight", facecolor="white",
    )
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def _clean_spines(ax: Any) -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(labelsize=_TICK_SIZE)


# ── Individual chart drawers ──────────────────────────────────────


def _draw_pie(fig: Any, ax: Any, data: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt

    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = plt.cm.Set3.colors[:len(labels)]
    _, _, autotexts = ax.pie(
        values, labels=labels, autopct="%1.0f%%",
        colors=colors, startangle=90,
        textprops={"fontsize": 14, "fontweight": "bold"},
    )
    for at in autotexts:
        at.set_fontsize(12)
        at.set_color("white")
        at.set_fontweight("bold")
    ax.set_aspect("equal")


def _draw_bar(fig: Any, ax: Any, data: dict[str, Any]) -> None:
    import matplotlib.pyplot as plt

    labels = data.get("labels", [])
    values = data.get("values", [])
    colors = plt.cm.Set2.colors[:len(labels)]
    bars = ax.bar(
        labels, values, color=colors,
        edgecolor="black", linewidth=1.2,
    )
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height() + 0.5, str(val),
            ha="center", va="bottom", fontsize=12, fontweight="bold",
        )
    ax.set_xlabel(data.get("xlabel", ""), **_FONT_LABEL)
    ax.set_ylabel(data.get("ylabel", ""), **_FONT_LABEL)
    _clean_spines(ax)


def _draw_line(fig: Any, ax: Any, data: dict[str, Any]) -> None:
    ax.plot(
        data.get("x", []), data.get("y", []),
        color="#2196F3", linewidth=2.5, marker="o", markersize=6,
    )
    ax.set_xlabel(data.get("xlabel", ""), **_FONT_LABEL)
    ax.set_ylabel(data.get("ylabel", ""), **_FONT_LABEL)
    ax.grid(True, alpha=0.3)
    _clean_spines(ax)


def _draw_boxplot(fig: Any, ax: Any, data: dict[str, Any]) -> None:
    import matplotlib.patches as mpatches

    mn = data.get("min", 0)
    q1, med, q3 = data.get("q1", 0), data.get("median", 0), data.get("q3", 0)
    mx = data.get("max", 0)
    bh, yc = 0.4, 0.5

    ax.plot([mn, q1], [yc, yc], color="black", linewidth=2)
    ax.plot([q3, mx], [yc, yc], color="black", linewidth=2)
    for xv in (mn, mx):
        ax.plot(
            [xv, xv], [yc - bh / 3, yc + bh / 3],
            color="black", linewidth=2,
        )
    ax.add_patch(mpatches.FancyBboxPatch(
        (q1, yc - bh / 2), q3 - q1, bh,
        boxstyle="square,pad=0",
        facecolor="#90CAF9", edgecolor="black", linewidth=2,
    ))
    ax.plot(
        [med, med], [yc - bh / 2, yc + bh / 2],
        color="red", linewidth=2.5,
    )
    ax.set_xlim(mn - 0.5, mx + 0.5)
    ax.set_ylim(-0.2, 1.2)
    ax.set_xlabel(data.get("xlabel", ""), **_FONT_LABEL)
    ax.set_yticks([])
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(labelsize=_TICK_SIZE)


def _draw_dot_plot(fig: Any, ax: Any, data: dict[str, Any]) -> None:
    values = data.get("values", [])
    counts = Counter(values)
    for val, count in sorted(counts.items()):
        for i in range(count):
            ax.plot(val, i + 1, "o", color="#1976D2", markersize=12)
    ax.set_xlabel(data.get("xlabel", ""), **_FONT_LABEL)
    ax.set_ylabel("Frecuencia", **_FONT_LABEL)
    all_vals = sorted(counts.keys())
    ax.set_xticks(range(int(min(all_vals)), int(max(all_vals)) + 1))
    ax.set_yticks(range(1, max(counts.values()) + 1))
    ax.grid(True, axis="y", alpha=0.3)
    _clean_spines(ax)


# ── Public API ────────────────────────────────────────────────────


def render_pie_chart(data: dict[str, Any]) -> bytes:
    return _render_to_png(_draw_pie, data, figsize=(6, 6))


def render_bar_chart(data: dict[str, Any]) -> bytes:
    return _render_to_png(_draw_bar, data)


def render_line_chart(data: dict[str, Any]) -> bytes:
    return _render_to_png(_draw_line, data)


def render_boxplot(data: dict[str, Any]) -> bytes:
    return _render_to_png(_draw_boxplot, data, figsize=(8, 3))


def render_dot_plot(data: dict[str, Any]) -> bytes:
    return _render_to_png(_draw_dot_plot, data, figsize=(8, 4))


MATPLOTLIB_RENDERERS: dict[str, Callable[[dict[str, Any]], bytes]] = {
    "pie_chart": render_pie_chart,
    "bar_chart": render_bar_chart,
    "line_chart": render_line_chart,
    "boxplot": render_boxplot,
    "dot_plot": render_dot_plot,
}
