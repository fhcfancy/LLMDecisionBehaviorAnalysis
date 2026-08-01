"""Shared paper style for the Cross-Family Generalization figures.

Mirrors ``DataAnalysis/Perceive`` so cross-directory figures look like they
belong to the same paper.

Conventions
-----------
- Serif font (Times New Roman) with Type-42 PDFs for vector publishing.
- Spines: top/right hidden; left/bottom width 0.7.
- Grid: dashed, axis="y", linewidth 0.6, alpha 0.22, drawn below data.
- Heatmaps: light-to-theme gradient (offwhite -> base color) instead of the
  saturated YlOrRd previously used here -- this matches the Perceive figure 1A
  / 1B / 3 family.
- Bar charts: edgecolor "white" with thin linewidth.

The palette names follow ``Perceive/theme_colors.md``.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import rcParams  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402


THEME_BLUE = "#4C78A8"
THEME_BLUE_DARK = "#547397"
THEME_BLUE_LIGHT = "#5A83AF"
THEME_BLUE_SOFT = "#81A0C2"
THEME_PURPLE = "#B279A2"
THEME_ORANGE = "#F3973C"
THEME_RED = "#E36466"

THEME_WHITE = "#FFFFFF"
THEME_OFFWHITE = "#FBFBFB"
THEME_LIGHT_GRAY = "#EBEBEB"
THEME_GRAY = "#D4D4D4"
THEME_BLACK = "#000000"

MODE_BASE_COLORS = {
    "Neutral": THEME_BLUE,
    "Neutral-CoT": THEME_PURPLE,
    "EI": THEME_ORANGE,
    "EA": THEME_RED,
}

# Generalization study has 4 models: two GPT (thinking + non-thinking) and two
# Qwen (thinking + non-thinking). We pick mid-range hues from the Perceive
# palette (not the same as the Claude/DeepSeek shades used in Perceive) so a
# reader can quickly tell which family they are looking at while still
# perceiving these figures as part of the same paper.
MODEL_HEATMAP_COLORS = {
    "GPT_5": "#336197",        # GPT non-thinking -> deep blue
    "GPT_o4": "#1E60A8",       # GPT thinking     -> darkest blue
    "QwenN": THEME_BLUE_LIGHT, # Qwen non-thinking -> lighter blue
    "QwenT": THEME_BLUE_SOFT,  # Qwen thinking     -> lightest blue
}


def set_paper_style() -> None:
    rcParams["font.family"] = "serif"
    rcParams["font.serif"] = ["Times New Roman", "Times", "Nimbus Roman", "DejaVu Serif"]
    rcParams["pdf.fonttype"] = 42
    rcParams["ps.fonttype"] = 42
    rcParams["text.color"] = "black"
    rcParams["axes.labelcolor"] = "black"
    rcParams["xtick.color"] = "black"
    rcParams["ytick.color"] = "black"
    rcParams["axes.edgecolor"] = "black"
    rcParams["axes.linewidth"] = 0.7


def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i : i + 2], 16) / 255.0 for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple[float, float, float]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*(max(0, min(255, round(c * 255))) for c in rgb))


def blend(hex_color: str, target: tuple[float, float, float], amount: float) -> str:
    r, g, b = hex_to_rgb(hex_color)
    tr, tg, tb = target
    mixed = (
        r * (1 - amount) + tr * amount,
        g * (1 - amount) + tg * amount,
        b * (1 - amount) + tb * amount,
    )
    return rgb_to_hex(mixed)


def lighten(hex_color: str, amount: float) -> str:
    return blend(hex_color, (1.0, 1.0, 1.0), amount)


def darken(hex_color: str, amount: float) -> str:
    return blend(hex_color, (0.0, 0.0, 0.0), amount)


def model_shade(mode_color: str, model: str) -> str:
    """4-model shade convention used in the Generalization paper.

    GPT family = darker tier; Qwen family = lighter tier. Within each family,
    the thinking variant is darker than its non-thinking counterpart.
    """
    if model == "GPT_o4":
        return darken(mode_color, 0.28)
    if model == "GPT_5":
        return darken(mode_color, 0.14)
    if model == "QwenT":
        return lighten(mode_color, 0.18)
    if model == "QwenN":
        return lighten(mode_color, 0.32)
    return mode_color


def style_axes(ax: plt.Axes, *, grid: bool = True, grid_axis: str = "y") -> None:
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_linewidth(0.7)
    ax.spines["bottom"].set_linewidth(0.7)
    if grid:
        ax.grid(axis=grid_axis, linestyle="--", linewidth=0.6, alpha=0.22)
        ax.set_axisbelow(True)


def light_theme_cmap(base_hex: str, name: str | None = None) -> LinearSegmentedColormap:
    """Light-to-theme gradient (offwhite -> base) for heatmaps."""
    cmap_name = name or f"theme_{base_hex.strip('#').lower()}"
    return LinearSegmentedColormap.from_list(cmap_name, [THEME_OFFWHITE, base_hex], N=256)


def warm_alignment_cmap() -> LinearSegmentedColormap:
    """Multi-stop warm gradient used for topic-drift heatmaps (Perceive fig 7)."""
    return LinearSegmentedColormap.from_list(
        "alignment_orange_red",
        [THEME_OFFWHITE, "#F7D8B5", THEME_ORANGE, "#EB6A57", THEME_RED],
        N=256,
    )


def save_publication(fig, out_dir: Path | str, name: str, *, dpi: int = 600) -> None:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_dir / f"{name}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
    fig.savefig(out_dir / f"{name}.pdf", bbox_inches="tight", facecolor="white")
