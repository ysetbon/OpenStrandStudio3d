"""
Generate a polished PDF document explaining the OpenStrandStudio3D
VBO + numpy rendering pipeline (V3) with matplotlib diagrams and
detailed explanatory text.

Usage:
    python docs/generate_pipeline_doc_v3.py

Output:
    docs/rendering_pipeline_v3.pdf
"""

import os
import argparse
import textwrap
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, ArrowStyle
import matplotlib.patheffects as pe

# ── Colour palette ──────────────────────────────────────────────
C_BG      = "#1e1e2e"
C_TEXT    = "#cdd6f4"
C_ACCENT  = "#89b4fa"
C_GREEN   = "#a6e3a1"
C_RED     = "#f38ba8"
C_YELLOW  = "#f9e2af"
C_PEACH   = "#fab387"
C_MAUVE   = "#cba6f7"
C_TEAL    = "#94e2d5"
C_SURFACE = "#313244"
C_OVERLAY = "#45475a"
C_DIM     = "#6c7086"

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUT_PDF = os.path.join(OUT_DIR, "rendering_pipeline_v3.pdf")


def configure_theme(printable=False):
    """Configure color palette for screen or printer output."""
    global C_BG, C_TEXT, C_ACCENT, C_GREEN, C_RED
    global C_YELLOW, C_PEACH, C_MAUVE, C_TEAL, C_SURFACE, C_OVERLAY, C_DIM

    if printable:
        # White background + high contrast text, no ink-heavy dark fills.
        C_BG      = "#ffffff"
        C_TEXT    = "#000000"
        C_ACCENT  = "#000000"
        C_GREEN   = "#000000"
        C_RED     = "#000000"
        C_YELLOW  = "#000000"
        C_PEACH   = "#000000"
        C_MAUVE   = "#000000"
        C_TEAL    = "#000000"
        C_SURFACE = "#ffffff"
        C_OVERLAY = "#efefef"
        C_DIM     = "#000000"
    else:
        C_BG      = "#1e1e2e"
        C_TEXT    = "#cdd6f4"
        C_ACCENT  = "#89b4fa"
        C_GREEN   = "#a6e3a1"
        C_RED     = "#f38ba8"
        C_YELLOW  = "#f9e2af"
        C_PEACH   = "#fab387"
        C_MAUVE   = "#cba6f7"
        C_TEAL    = "#94e2d5"
        C_SURFACE = "#313244"
        C_OVERLAY = "#45475a"
        C_DIM     = "#6c7086"


def resolve_unlocked_output_path(path):
    """Return a writable output path; if locked, append numeric suffix."""
    base, ext = os.path.splitext(path)
    candidate = path
    idx = 1
    while True:
        if not os.path.exists(candidate):
            return candidate
        try:
            with open(candidate, "rb+"):
                return candidate
        except PermissionError:
            candidate = f"{base}_{idx}{ext}"
            idx += 1


# ── Helpers ─────────────────────────────────────────────────────

def new_page(fig_width=11.69, fig_height=8.27):
    """Create a dark-themed figure sized for landscape A4."""
    fig = plt.figure(figsize=(fig_width, fig_height), facecolor=C_BG)
    return fig


def add_title(fig, title, subtitle=None, y=0.95, fontsize=22):
    fig.text(0.5, y, title, ha="center", va="top",
             fontsize=fontsize, fontweight="bold", color=C_ACCENT,
             family="monospace")
    if subtitle:
        fig.text(0.5, y - 0.045, subtitle, ha="center", va="top",
                 fontsize=12, color=C_TEXT, family="monospace")


def add_body_text(fig, text, x=0.06, y=0.82, width=80, fontsize=9.5,
                  color=None, line_spacing=1.55):
    """Render a block of wrapped text onto the figure."""
    if color is None:
        color = C_TEXT
    lines = []
    for raw_line in text.strip().split("\n"):
        if raw_line.strip() == "":
            lines.append("")
        else:
            wrapped = textwrap.wrap(raw_line, width=width)
            lines.extend(wrapped if wrapped else [""])
    joined = "\n".join(lines)
    fig.text(x, y, joined, va="top", fontsize=fontsize, color=color,
             family="monospace", linespacing=line_spacing)


def rounded_box(ax, xy, width, height, text, color=None,
                text_color=None, fontsize=10, lw=1.5, edge_color=None,
                alpha=1.0):
    if color is None:
        color = C_SURFACE
    if text_color is None:
        text_color = C_TEXT
    ec = edge_color or color
    box = FancyBboxPatch(xy, width, height,
                         boxstyle="round,pad=0.02",
                         facecolor=color, edgecolor=ec,
                         linewidth=lw, alpha=alpha)
    ax.add_patch(box)
    cx = xy[0] + width / 2
    cy = xy[1] + height / 2
    ax.text(cx, cy, text, ha="center", va="center",
            fontsize=fontsize, color=text_color, family="monospace")
    return box


def arrow(ax, start, end, color=None, lw=2, style="-|>", mutation=15):
    if color is None:
        color = C_ACCENT
    a = FancyArrowPatch(start, end,
                        arrowstyle=ArrowStyle(style, head_length=0.3,
                                              head_width=0.2),
                        color=color, lw=lw, mutation_scale=mutation)
    ax.add_patch(a)
    return a


# ════════════════════════════════════════════════════════════════
#  Page 1 – Title Page
# ════════════════════════════════════════════════════════════════
def page_title():
    fig = new_page()
    fig.text(0.5, 0.68, "OpenStrandStudio3D", ha="center", va="center",
             fontsize=38, fontweight="bold", color=C_ACCENT, family="monospace")
    fig.text(0.5, 0.56, "Rendering Pipeline V3", ha="center", va="center",
             fontsize=32, fontweight="bold", color=C_MAUVE, family="monospace")
    fig.text(0.5, 0.45, "VBO Cache  +  Numpy Vectorisation", ha="center",
             va="center", fontsize=18, color=C_TEXT, family="monospace")

    overview = (
        "This document explains how OpenStrandStudio3D renders strand tubes\n"
        "to the screen. It covers the scene structure, how a single strand\n"
        "becomes a 3D tube mesh, the three-layer caching system that avoids\n"
        "redundant work, and the numpy broadcasting tricks that replaced\n"
        "slow Python loops with fast C-level array operations.\n"
        "\n"
        "The result: drag interactions went from ~0.3 FPS to ~25 FPS."
    )
    fig.text(0.5, 0.32, overview, ha="center", va="top", fontsize=11,
             color=C_DIM, family="monospace", linespacing=1.6)
    return fig


# ════════════════════════════════════════════════════════════════
#  NEW (V3) Page – Old vs New Approaches
# ════════════════════════════════════════════════════════════════
def page_old_vs_new():
    fig = new_page()
    add_title(fig, "Old vs New Approaches (V1 \u2192 V2 \u2192 V3)",
              "Explicit evolution of rendering strategy")

    ax = fig.add_axes([0.04, 0.40, 0.92, 0.44])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 6)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    rounded_box(ax, (0.4, 2.8), 3.2, 2.0,
                "V1 (Original)\n\n"
                "Python nested loops\n"
                "Immediate mode GL\n"
                "(glBegin/glVertex3f)",
                color=C_SURFACE, edge_color=C_RED, lw=2.2, text_color=C_TEXT, fontsize=9.5)

    rounded_box(ax, (4.4, 2.8), 3.2, 2.0,
                "V2 (3d4bc3d)\n\n"
                "Vectorized tube mesh\n"
                "glDrawArrays path\n"
                "Display-list cache removed",
                color=C_SURFACE, edge_color=C_PEACH, lw=2.2, text_color=C_TEXT, fontsize=9.5)

    rounded_box(ax, (8.4, 2.8), 3.2, 2.0,
                "V3 (5abbd6a)\n\n"
                "Vectorized Bezier + frames\n"
                "float32-throughout mesh\n"
                "Drag-time VBO reuse",
                color=C_SURFACE, edge_color=C_GREEN, lw=2.2, text_color=C_TEXT, fontsize=9.5)

    arrow(ax, (3.7, 3.8), (4.3, 3.8), color=C_YELLOW, lw=2.8)
    arrow(ax, (7.7, 3.8), (8.3, 3.8), color=C_YELLOW, lw=2.8)

    ax.text(2.0, 2.35, "~0.3 FPS drag", color=C_RED, fontsize=10,
            family="monospace", ha="center", fontweight="bold")
    ax.text(6.0, 2.35, "~6 FPS drag", color=C_PEACH, fontsize=10,
            family="monospace", ha="center", fontweight="bold")
    ax.text(10.0, 2.35, "~25 FPS drag", color=C_GREEN, fontsize=10,
            family="monospace", ha="center", fontweight="bold")

    ax.text(2.0, 1.35, "Bottleneck:\nPython + per-vertex GL",
            color=C_DIM, fontsize=8.5, family="monospace", ha="center")
    ax.text(6.0, 1.35, "Main gain:\nBatch arrays + vectorized mesh",
            color=C_DIM, fontsize=8.5, family="monospace", ha="center")
    ax.text(10.0, 1.35, "Main gain:\nVersioned cache + drag VBO hits",
            color=C_DIM, fontsize=8.5, family="monospace", ha="center")

    txt = (
        "This page separates OLD vs NEW approaches clearly:\n"
        "\n"
        "V1 used Python loops and immediate-mode GL calls for lots of tiny operations. V2 moved\n"
        "to vectorized mesh construction and batched draw-arrays rendering, and removed display-list\n"
        "replay that caused stale-geometry edge cases. V3 adds drag-time VBO reuse for non-affected\n"
        "chains, vectorized Bezier generation, optimized sequential frame transport, and float32\n"
        "data flow end-to-end. The result is much better interactive drag performance."
    )
    add_body_text(fig, txt, x=0.06, y=0.30, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 2 – Scene Structure (diagram)
# ════════════════════════════════════════════════════════════════
def page_scene_structure():
    fig = new_page()
    add_title(fig, "Scene Structure")

    # ── Diagram in upper portion ──
    ax = fig.add_axes([0.05, 0.38, 0.9, 0.50])
    ax.set_xlim(0, 11.5)
    ax.set_ylim(0, 6)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    chain_colors = [C_ACCENT, C_GREEN, C_PEACH, C_MAUVE]
    chain_labels = ["Chain 1  (12 strands)", "Chain 2  (11 strands)",
                    "Chain 3  (10 strands)", "Chain 4  (10 strands)"]
    strand_counts = [5, 4, 4, 4]
    box_w = 1.2
    box_h = 0.5
    x_start = 2.0
    gap = 0.4

    for ci in range(4):
        y = 5.0 - ci * 1.35
        ax.text(0.1, y + 0.18, chain_labels[ci], fontsize=9,
                color=chain_colors[ci], fontweight="bold", family="monospace")
        for si in range(strand_counts[ci]):
            x = x_start + si * (box_w + gap)
            ec = C_YELLOW if si == 0 else chain_colors[ci]
            fc = C_SURFACE if si > 0 else chain_colors[ci] + "30"
            lbl = f"{ci+1}_1" if si == 0 else f"{ci+1}_{si+1}"
            rounded_box(ax, (x, y - 0.25), box_w, box_h, lbl, color=fc,
                        edge_color=ec, text_color=C_TEXT, fontsize=9, lw=2)
            if si > 0:
                prev_x = x_start + (si - 1) * (box_w + gap)
                arrow(ax, (prev_x + box_w + 0.03, y), (x - 0.03, y),
                      color=chain_colors[ci], lw=1.5)
        # "..." at end
        chain_end_x = x_start + strand_counts[ci] * (box_w + gap)
        ax.text(chain_end_x + 0.12, y,
                "...", fontsize=14, color=chain_colors[ci],
                va="center", family="monospace")

    ax.plot([], [], "s", color=C_YELLOW, markersize=10,
            label="Chain root (triggers rendering)")
    ax.plot([], [], "s", color=C_OVERLAY, markersize=10,
            label="Child strand (skipped in draw loop)")
    ax.legend(loc="lower right", fontsize=9, framealpha=0.3,
              facecolor=C_SURFACE, edgecolor=C_OVERLAY, labelcolor=C_TEXT)

    # ── Text explanation below ──
    txt = (
        "Strands are grouped into chains. Each chain is rendered as one continuous tube.\n"
        "The first strand in a chain is the chain root -- it owns all caches and is the\n"
        "only strand whose draw() method actually does rendering work.\n"
        "\n"
        "When paintGL() loops over all 43 strands, 39 non-root strands return immediately.\n"
        "Only the 4 chain roots call _draw_chain_as_spline(), which collects geometry from\n"
        "every strand in the chain, builds the tube mesh, and sends it to the GPU.\n"
        "\n"
        "This means the rendering cost scales with the number of chains (4), not the total\n"
        "number of strands (43). Each chain root checks its caches before doing any work."
    )
    add_body_text(fig, txt, x=0.06, y=0.34, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 3 – Strand Tube Construction (diagram)
# ════════════════════════════════════════════════════════════════
def page_tube_construction():
    fig = new_page()
    add_title(fig, "Strand Tube Construction",
              "Three-stage pipeline: Control Points  \u2192  Curve  \u2192  Rings  \u2192  Mesh")

    # ── Stage 1: Bezier ──
    ax1 = fig.add_axes([0.04, 0.32, 0.28, 0.52])
    ax1.set_facecolor(C_BG)
    ax1.set_xlim(-0.2, 1.2)
    ax1.set_ylim(-0.3, 1.2)
    ax1.axis("off")
    ax1.set_title("Stage 1: Bezier Curve", fontsize=11, color=C_ACCENT,
                  family="monospace", pad=8)

    cp = np.array([[0, 0], [0.3, 1.0], [0.7, 1.0], [1.0, 0]])
    t = np.linspace(0, 1, 57)
    mt = 1 - t
    curve = ((mt**3)[:, None] * cp[0] + (3*mt**2*t)[:, None] * cp[1] +
             (3*mt*t**2)[:, None] * cp[2] + (t**3)[:, None] * cp[3])
    ax1.plot(curve[:, 0], curve[:, 1], color=C_GREEN, lw=2.5)
    ax1.plot(*cp.T, "o--", color=C_YELLOW, markersize=8, lw=1, alpha=0.6)
    labels = ["P0 (start)", "CP1", "CP2", "P3 (end)"]
    offsets = [(0, -0.12), (-0.08, 0.08), (0.08, 0.08), (0, -0.12)]
    for i, (lbl, off) in enumerate(zip(labels, offsets)):
        ax1.annotate(lbl, cp[i],
                     xytext=(cp[i][0]+off[0], cp[i][1]+off[1]),
                     fontsize=7, color=C_YELLOW, ha="center",
                     family="monospace")
    ax1.text(0.5, -0.22, "57 pts (56 segments)", ha="center", fontsize=8,
             color=C_TEXT, family="monospace")

    # ── Stage 2: Cross-section rings ──
    ax2 = fig.add_axes([0.37, 0.32, 0.28, 0.52])
    ax2.set_facecolor(C_BG)
    ax2.set_xlim(-1.5, 1.5)
    ax2.set_ylim(-0.5, 3.5)
    ax2.axis("off")
    ax2.set_title("Stage 2: Ring Cross-Sections", fontsize=11,
                  color=C_ACCENT, family="monospace", pad=8)

    theta = np.linspace(0, 2*np.pi, 41)
    for y_pos in np.linspace(0, 3, 6):
        x_ring = 0.5 * np.cos(theta)
        z_ring = 0.5 * np.sin(theta) * 0.3 + y_pos
        ax2.plot(x_ring, z_ring, color=C_TEAL, lw=1.5, alpha=0.7)
        ax2.plot(0, y_pos, ".", color=C_GREEN, markersize=5)
    ax2.plot([0, 0], [0, 3], "--", color=C_GREEN, lw=1, alpha=0.5)
    ax2.text(0, -0.35, "40 segments per ring", ha="center", fontsize=8,
             color=C_TEXT, family="monospace")

    # ── Stage 3: Triangle mesh ──
    ax3 = fig.add_axes([0.70, 0.32, 0.28, 0.52])
    ax3.set_facecolor(C_BG)
    ax3.set_xlim(-1.5, 1.5)
    ax3.set_ylim(-0.5, 3.5)
    ax3.axis("off")
    ax3.set_title("Stage 3: Triangle Mesh", fontsize=11, color=C_ACCENT,
                  family="monospace", pad=8)

    ring_count, seg_count = 8, 12
    theta_m = np.linspace(0, 2*np.pi, seg_count + 1)
    ys = np.linspace(0, 3, ring_count)
    for i in range(ring_count):
        xs = 0.5 * np.cos(theta_m)
        zs = 0.5 * np.sin(theta_m) * 0.3 + ys[i]
        ax3.plot(xs, zs, color=C_PEACH, lw=0.7, alpha=0.5)
        if i < ring_count - 1:
            xs2 = 0.5 * np.cos(theta_m)
            zs2 = 0.5 * np.sin(theta_m) * 0.3 + ys[i+1]
            for j in range(0, seg_count, 2):
                ax3.plot([xs[j], xs2[j]], [zs[j], zs2[j]],
                         color=C_PEACH, lw=0.7, alpha=0.5)
                ax3.plot([xs[j], xs2[j+1]], [zs[j], zs2[j+1]],
                         color=C_RED, lw=0.4, alpha=0.4)
    ax3.text(0, -0.35, "4,480 tris / strand", ha="center", fontsize=8,
             color=C_TEXT, family="monospace")

    # Stage arrows
    for x_pos in [0.33, 0.66]:
        fig.text(x_pos, 0.58, "\u2192", fontsize=28, color=C_ACCENT,
                 ha="center", va="center", family="monospace",
                 fontweight="bold")

    # ── Text explanation below ──
    txt = (
        "Each strand is defined by 4 control points (start, CP1, CP2, end). A cubic Bezier\n"
        "curve interpolates these into 57 evenly spaced points (56 segments). At each curve\n"
        "point, a ring of 40 vertices is placed perpendicular to the curve direction using\n"
        "parallel-transport frames (right/up vectors). Adjacent rings are connected into\n"
        "quads, each split into 2 triangles = 4,480 triangles per strand.\n"
        "\n"
        "For a 12-strand chain: 12 x 56 = 672 curve points, 672 x 40 x 2 = 53,760 triangles."
    )
    add_body_text(fig, txt, x=0.06, y=0.28, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 4 – Tube Construction Detail (text-heavy)
# ════════════════════════════════════════════════════════════════
def page_tube_detail():
    fig = new_page()
    add_title(fig, "Tube Construction: Vectorised Steps")

    txt = (
        "STEP A: BEZIER POINTS (vectorised with numpy)\n"
        "\n"
        "  Old way:  for i in range(57): point = (1-t)^3*P0 + ...   (684 Python calls for 12 strands)\n"
        "  New way:  t = np.linspace(0, 1, 57)   then broadcast  t[:,None] * P0[None,:]\n"
        "            All 57 points computed in ~1 numpy call per strand.  12 calls total, not 684.\n"
        "\n"
        "\n"
        "STEP B: PARALLEL TRANSPORT FRAMES (scalar math)\n"
        "\n"
        "  Each curve point needs a right/up coordinate frame to orient its ring. Each frame\n"
        "  depends on the previous one (sequential), so full vectorisation is impossible.\n"
        "\n"
        "  But numpy has ~20us overhead PER CALL for tiny 3-element arrays:\n"
        "    np.dot([a,b,c], [d,e,f])  =  parse args + check types + allocate + compute + wrap  = ~20us\n"
        "    px*tx + py*ty + pz*tz     =  3 float multiplies + 2 adds                           = ~0.1us\n"
        "\n"
        "  So we pre-compute all tangents in one batch:  tangents = pts[1:] - pts[:-1]\n"
        "  Then loop with plain Python scalars:  672 iters x 0.5us = 0.3ms  (vs 50ms with numpy)\n"
        "\n"
        "\n"
        "STEP C: BUILD TRIANGLE MESH (numpy broadcasting -- the big win)\n"
        "\n"
        "  vertex = center + width * x_cs * right + height * y_cs * up\n"
        "\n"
        "  We reshape arrays so numpy broadcasts the entire mesh in one operation:\n"
        "    centers[:, None, :]   (671, 1, 3)  -- one center per curve segment\n"
        "    x_cross[None, :, None] (1, 40, 1)  -- one x per ring position\n"
        "    rights[:, None, :]    (671, 1, 3)  -- one right vector per segment\n"
        "                                  Result: (671, 40, 3) = 80,520 floats in ONE C loop.\n"
        "\n"
        "  All arrays are float32 (4 bytes), not float64 (8 bytes), halving memory and matching\n"
        "  OpenGL's native format -- no conversion needed.\n"
        "\n"
        "\n"
        "STEP D: SEND TO GPU\n"
        "\n"
        "  For cached chains (VBO):     glBindBuffer + glDrawArrays  (GPU reads its own memory)\n"
        "  For the affected chain:      glVertexPointer + glDrawArrays  (GPU reads CPU numpy array)\n"
        "  No VBO is created for the affected chain because the data changes every frame anyway."
    )
    add_body_text(fig, txt, x=0.06, y=0.88, fontsize=9, width=100)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 5 – Three-Layer Cache System (diagram)
# ════════════════════════════════════════════════════════════════
def page_cache_system():
    fig = new_page()
    add_title(fig, "Three-Layer Cache System")

    # ── Diagram on left ──
    ax = fig.add_axes([0.03, 0.08, 0.45, 0.80])
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 10)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    layers = [
        {"title": "Layer 1: Curve Cache",
         "sub": "_curve_cache",
         "key": "Key: (num_segments, _geom_version)",
         "io": "4 control pts  \u2192  57 Bezier pts",
         "where": "Per strand",
         "color": C_GREEN, "y": 7.8},
        {"title": "Layer 2: Chain Geometry Cache",
         "sub": "_chain_cache",
         "key": "Key: (curve_segs, [(id,ver), ...])",
         "io": "Per-strand curves  \u2192  merged chain",
         "where": "On chain root",
         "color": C_ACCENT, "y": 5.2},
        {"title": "Layer 3: VBO Cache",
         "sub": "_vbo_cache",
         "key": "Key: (curve_segs, tube_segs, versions)",
         "io": "Vertices+normals  \u2192  GPU buffers",
         "where": "On chain root, IN GPU RAM",
         "color": C_MAUVE, "y": 2.6},
    ]

    bw, bh = 9.0, 1.8
    bx = 0.5
    for L in layers:
        rounded_box(ax, (bx, L["y"]), bw, bh, "",
                    color=C_SURFACE, edge_color=L["color"], lw=2)
        ax.text(bx + 0.3, L["y"] + bh - 0.25, L["title"],
                va="top", fontsize=10, fontweight="bold",
                color=L["color"], family="monospace")
        ax.text(bx + 0.3, L["y"] + bh - 0.55,
                f"({L['sub']})", va="top", fontsize=8,
                color=C_DIM, family="monospace")
        ax.text(bx + 0.3, L["y"] + bh - 0.85, L["key"],
                va="top", fontsize=8, color=C_TEXT, family="monospace")
        ax.text(bx + 0.3, L["y"] + bh - 1.10, L["io"],
                va="top", fontsize=8, color=C_YELLOW, family="monospace")
        ax.text(bx + 0.3, L["y"] + bh - 1.35, f"Stored: {L['where']}",
                va="top", fontsize=8, color=C_DIM, family="monospace")

    mid_x = bx + bw / 2
    arrow(ax, (mid_x, layers[0]["y"]),
          (mid_x, layers[1]["y"] + bh + 0.08), color=C_GREEN, lw=2.5)
    arrow(ax, (mid_x, layers[1]["y"]),
          (mid_x, layers[2]["y"] + bh + 0.08), color=C_ACCENT, lw=2.5)

    # GPU box
    rounded_box(ax, (2.5, 0.4), 4.5, 1.0, "GPU  (OpenGL  glDrawArrays)",
                color=C_OVERLAY, edge_color=C_PEACH, text_color=C_PEACH,
                fontsize=10, lw=2)
    arrow(ax, (mid_x, layers[2]["y"]),
          (mid_x, 1.45), color=C_MAUVE, lw=2.5)

    # ── Text on right ──
    txt = (
        "The rendering pipeline has three caching\n"
        "layers stacked on top of each other. Each\n"
        "layer stores the output of a computation\n"
        "stage, keyed by a version tuple.\n"
        "\n"
        "Layer 1 (Curve Cache) is per-strand. Each\n"
        "strand caches its own 57-point Bezier curve.\n"
        "The key includes _geom_version, an integer\n"
        "that increments whenever a control point\n"
        "moves. If the version matches, the cached\n"
        "curve is returned (a simple dict lookup).\n"
        "\n"
        "Layer 2 (Chain Geometry Cache) merges all\n"
        "strand curves in a chain into one array of\n"
        "points + parallel-transport frames. The key\n"
        "includes every strand's (id, version) tuple.\n"
        "If ANY strand in the chain changed, this\n"
        "cache misses and the chain is recomputed.\n"
        "\n"
        "Layer 3 (VBO Cache) holds the final triangle\n"
        "mesh as GPU vertex buffer objects. A VBO hit\n"
        "means the geometry already sits in GPU memory\n"
        "-- rendering costs just 5 GL calls (~0.1ms).\n"
        "\n"
        "During a drag, only the affected chain's\n"
        "versions change. The other 3 chains hit all\n"
        "3 cache layers and render almost for free."
    )
    fig.text(0.52, 0.87, txt, va="top", fontsize=9.5,
             color=C_TEXT, family="monospace", linespacing=1.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 6 – Drag Frame Flow (diagram)
# ════════════════════════════════════════════════════════════════
def page_drag_flow():
    fig = new_page()
    add_title(fig, "Drag-Frame Rendering Flow",
              "Example: dragging strand 1_7's end point")

    ax = fig.add_axes([0.05, 0.30, 0.9, 0.56])
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 8)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    # divider
    ax.plot([6, 6], [0.5, 7.5], "--", color=C_OVERLAY, lw=1.5, alpha=0.5)
    ax.text(3.0, 7.7, "AFFECTED CHAIN (miss)", fontsize=11,
            color=C_RED, fontweight="bold", ha="center", family="monospace")
    ax.text(9.0, 7.7, "NON-AFFECTED CHAINS (hit)", fontsize=11,
            color=C_GREEN, fontweight="bold", ha="center", family="monospace")

    # ── Left: cache miss path ──
    lx, bw_l = 0.8, 4.2
    steps_left = [
        ("1_7._geom_version++\n1_8._geom_version++", 6.4, C_RED),
        ("_curve_cache MISS\nRecompute 12x Bezier", 5.0, C_RED),
        ("_chain_cache MISS\nMerge 672 pts + frames", 3.6, C_PEACH),
        ("_build_tube_mesh()\nnumpy broadcast (f32)", 2.2, C_PEACH),
        ("glVertexPointer +\nglDrawArrays (client)", 0.8, C_YELLOW),
    ]
    for txt, y, col in steps_left:
        rounded_box(ax, (lx, y), bw_l, 0.90, txt, color=C_SURFACE,
                    edge_color=col, fontsize=8.5, lw=1.5)
    for i in range(len(steps_left) - 1):
        y1, y2 = steps_left[i][1], steps_left[i+1][1] + 0.90
        arrow(ax, (lx + bw_l/2, y1), (lx + bw_l/2, y2),
              color=C_RED, lw=1.5)
    ax.text(lx + bw_l/2, 0.3, "~40 ms", fontsize=11,
            color=C_PEACH, ha="center", family="monospace",
            fontweight="bold")

    # ── Right: cache hit path ──
    rx, bw_r = 7.0, 4.2
    steps_right = [
        ("_geom_version\nunchanged", 6.4, C_GREEN),
        ("_vbo_cache HIT\nversions match", 4.6, C_GREEN),
        ("_draw_tube_vbo()\n5 GL calls from GPU", 2.8, C_TEAL),
    ]
    for txt, y, col in steps_right:
        rounded_box(ax, (rx, y), bw_r, 0.90, txt, color=C_SURFACE,
                    edge_color=col, fontsize=8.5, lw=1.5)
    arrow(ax, (rx + bw_r/2, 6.4), (rx + bw_r/2, 5.55),
          color=C_GREEN, lw=1.5)
    arrow(ax, (rx + bw_r/2, 4.6), (rx + bw_r/2, 3.75),
          color=C_GREEN, lw=1.5)
    ax.text(rx + bw_r/2, 2.2, "~0.1 ms each", fontsize=11,
            color=C_TEAL, ha="center", family="monospace",
            fontweight="bold")

    # ── Text below ──
    txt = (
        "When you drag 1_7's end point, _update_move() shifts 1_7.end and 1_8.start, then\n"
        "calls _mark_geometry_dirty() on both. This increments their _geom_version and clears\n"
        "their curve caches. Chain 1's root (1_1) detects the version mismatch and rebuilds\n"
        "the entire chain. Chains 2, 3, 4 have unchanged versions -- they skip straight to the\n"
        "cached VBO in GPU memory. Total per frame: ~40ms (1 rebuild) + 3 x 0.1ms (3 hits) = ~40ms."
    )
    add_body_text(fig, txt, x=0.06, y=0.27, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 7 – Drag Detail (text-heavy, per-frame breakdown)
# ════════════════════════════════════════════════════════════════
def page_drag_detail():
    fig = new_page()
    add_title(fig, "Per-Frame Breakdown During Drag")

    txt = (
        "EACH FRAME WHEN DRAGGING 1_7's END:\n"
        "\n"
        "  39 non-root strands:  strand.draw() -> return immediately          ~0 ms\n"
        "\n"
        "  Chain 1 (1_1, AFFECTED):\n"
        "    _get_chain_geometry  -> MISS -> recompute                         ~35 ms\n"
        "      |-- 12x vectorised Bezier points (numpy broadcast)\n"
        "      |-- 672-point scalar parallel transport (plain Python math)\n"
        "      +-- chain twist application\n"
        "    _build_tube_mesh    -> numpy broadcast f32                        ~5 ms\n"
        "      |-- (671, 40, 3) vertices + normals in one operation\n"
        "      +-- glVertexPointer + glDrawArrays (client-side)\n"
        "\n"
        "  Chain 2 (2_1, not affected):\n"
        "    _get_chain_geometry  -> HIT  -> cached                            ~0.01 ms\n"
        "    VBO lookup           -> HIT  -> GPU render                        ~0.1 ms\n"
        "\n"
        "  Chain 3 (3_1, not affected):    same as chain 2                     ~0.1 ms\n"
        "  Chain 4 (4_1, not affected):    same as chain 2                     ~0.1 ms\n"
        "\n"
        "  ---------------------------------------------------------------------------\n"
        "  TOTAL PER FRAME:                                                    ~40 ms = 25 FPS\n"
        "\n"
        "\n"
        "WHY NOT CREATE A VBO FOR THE AFFECTED CHAIN?\n"
        "\n"
        "  Creating a VBO means uploading data to GPU memory with glBufferData(). But the\n"
        "  affected chain's geometry changes every single frame during drag. Uploading to a\n"
        "  VBO that will be stale 16ms later is wasted work. Instead, we use client-side\n"
        "  arrays: glVertexPointer points the GPU directly at our numpy array in CPU RAM.\n"
        "  The GPU reads it once and draws. No upload, no cleanup.\n"
        "\n"
        "  VBO cleanup is also deferred during drag (_defer_vbo_cleanup = True) so old\n"
        "  cache entries aren't deleted mid-operation. After the drag ends, end_drag_operation()\n"
        "  clears stale VBOs and the next static frame creates fresh ones.\n"
        "\n"
        "\n"
        "COMPARISON:\n"
        "\n"
        "  Without VBO cache (all chains rebuild):   4 x ~40ms = ~170ms = 6 FPS\n"
        "  Without numpy (Python loops, per-vertex): all chains = ~3,000ms = 0.3 FPS\n"
        "  Current (VBO + numpy):  1 rebuild + 3 hits = ~40ms = 25 FPS"
    )
    add_body_text(fig, txt, x=0.06, y=0.88, fontsize=9, width=100)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 8 – VBO vs Client-Side Arrays (diagram)
# ════════════════════════════════════════════════════════════════
def page_vbo_vs_clientside():
    fig = new_page()
    add_title(fig, "VBO vs Client-Side Arrays")

    # ── Left: VBO ──
    ax1 = fig.add_axes([0.05, 0.32, 0.42, 0.52])
    ax1.set_xlim(0, 10)
    ax1.set_ylim(0, 8)
    ax1.set_facecolor(C_BG)
    ax1.axis("off")
    ax1.set_title("VBO Path  (cached chains)", fontsize=12,
                  color=C_GREEN, family="monospace", fontweight="bold",
                  pad=10)

    rounded_box(ax1, (1, 6), 3.5, 1.2, "CPU\nnumpy mesh\n(computed once)",
                color=C_SURFACE, edge_color=C_ACCENT, fontsize=10, lw=2)
    arrow(ax1, (2.75, 6), (2.75, 5.1), color=C_YELLOW, lw=3)
    ax1.text(5, 5.5, "glBufferData\n(one-time upload)", fontsize=8,
             color=C_YELLOW, family="monospace")

    rounded_box(ax1, (1, 3.5), 3.5, 1.2,
                "GPU VRAM\nVBO buffers\n(persistent)",
                color=C_SURFACE, edge_color=C_GREEN, fontsize=10, lw=2)
    arrow(ax1, (2.75, 3.5), (2.75, 2.6), color=C_GREEN, lw=3)
    ax1.text(5, 3.0, "glDrawArrays\n(GPU-only read)", fontsize=8,
             color=C_GREEN, family="monospace")

    rounded_box(ax1, (1, 1.2), 3.5, 1.0, "Screen",
                color=C_OVERLAY, edge_color=C_TEAL, fontsize=11, lw=2)

    ax1.annotate("", xy=(0.5, 2.6), xytext=(0.5, 4.7),
                 arrowprops=dict(arrowstyle="->", color=C_GREEN,
                                 lw=1.5, ls="--"))
    ax1.text(0.0, 3.6, "every\nframe", fontsize=7, color=C_GREEN,
             ha="center", family="monospace", rotation=90)

    # ── Right: Client-side ──
    ax2 = fig.add_axes([0.53, 0.32, 0.42, 0.52])
    ax2.set_xlim(0, 10)
    ax2.set_ylim(0, 8)
    ax2.set_facecolor(C_BG)
    ax2.axis("off")
    ax2.set_title("Client-Side Path  (affected chain)", fontsize=12,
                  color=C_RED, family="monospace", fontweight="bold",
                  pad=10)

    rounded_box(ax2, (1, 6), 3.5, 1.2,
                "CPU\nnumpy mesh\n(rebuilt every frame)",
                color=C_SURFACE, edge_color=C_PEACH, fontsize=10, lw=2)
    arrow(ax2, (2.75, 6), (2.75, 5.1), color=C_RED, lw=3)
    ax2.text(5, 5.5, "glVertexPointer\n(every frame!)", fontsize=8,
             color=C_RED, family="monospace")

    rounded_box(ax2, (1, 3.5), 3.5, 1.2,
                "GPU\nreads CPU ptr\n(transient)",
                color=C_SURFACE, edge_color=C_RED, fontsize=10, lw=2)
    arrow(ax2, (2.75, 3.5), (2.75, 2.6), color=C_PEACH, lw=3)
    ax2.text(5, 3.0, "glDrawArrays\n(reads CPU mem)", fontsize=8,
             color=C_PEACH, family="monospace")

    rounded_box(ax2, (1, 1.2), 3.5, 1.0, "Screen",
                color=C_OVERLAY, edge_color=C_TEAL, fontsize=11, lw=2)

    ax2.annotate("", xy=(0.5, 1.2), xytext=(0.5, 7.2),
                 arrowprops=dict(arrowstyle="->", color=C_RED,
                                 lw=1.5, ls="--"))
    ax2.text(0.0, 4.0, "every\nframe", fontsize=7, color=C_RED,
             ha="center", family="monospace", rotation=90)

    # ── Text below ──
    txt = (
        "VBO (Vertex Buffer Object) stores geometry in GPU memory. Once uploaded, the GPU\n"
        "reads from its own fast VRAM on every frame -- the CPU just says \"draw what you have\".\n"
        "Cost: ~0.1ms per chain. This is used for non-affected chains whose data hasn't changed.\n"
        "\n"
        "Client-side arrays keep data in CPU RAM. The GPU must reach across the bus to read it\n"
        "each frame. This is slower, but makes sense for the affected chain: the geometry changes\n"
        "every frame during drag, so uploading to a VBO would be wasted effort."
    )
    add_body_text(fig, txt, x=0.06, y=0.28, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 9 – Numpy Broadcasting (diagram)
# ════════════════════════════════════════════════════════════════
def page_numpy_broadcasting():
    fig = new_page()
    add_title(fig, "Numpy Broadcasting in _build_tube_mesh")

    ax = fig.add_axes([0.05, 0.35, 0.9, 0.52])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 9)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    ax.text(7, 8.7,
            "vertex = center + width * x * right + height * y * up",
            fontsize=12, color=C_YELLOW, ha="center", family="monospace",
            fontweight="bold")

    arrays = [
        ("center[:, None, :]", "(671, 1, 3)", C_GREEN,  1.5, 7.2),
        ("x[None, :, None]",   "(1, 40, 1)",  C_ACCENT, 5.5, 7.2),
        ("right[:, None, :]",  "(671, 1, 3)", C_PEACH,  9.5, 7.2),
    ]
    for name, shape, col, x, y in arrays:
        rounded_box(ax, (x, y), 3.0, 1.0, f"{name}\n{shape}",
                    color=C_SURFACE, edge_color=col, fontsize=10, lw=2)

    ax.text(4.8, 7.7, "\u00d7", fontsize=22, color=C_TEXT, ha="center",
            va="center", family="monospace")
    ax.text(8.8, 7.7, "\u00d7", fontsize=22, color=C_TEXT, ha="center",
            va="center", family="monospace")

    for x_ctr in [3.0, 7.0, 11.0]:
        arrow(ax, (x_ctr, 7.2), (x_ctr, 6.3), color=C_YELLOW, lw=2)

    ax.text(7, 6.0, "Numpy stretches dimensions with size 1 to match:",
            fontsize=10, color=C_TEXT, ha="center", family="monospace")

    stretches = [
        ("dim 0:  671  stays",    C_GREEN,  1.8, 5.3),
        ("dim 1:    1 -> 40",     C_GREEN,  1.8, 4.8),
        ("dim 2:    3  stays",    C_GREEN,  1.8, 4.3),
        ("dim 0:    1 -> 671",    C_ACCENT, 5.8, 5.3),
        ("dim 1:   40  stays",    C_ACCENT, 5.8, 4.8),
        ("dim 2:    1 -> 3",      C_ACCENT, 5.8, 4.3),
        ("dim 0:  671  stays",    C_PEACH,  9.8, 5.3),
        ("dim 1:    1 -> 40",     C_PEACH,  9.8, 4.8),
        ("dim 2:    3  stays",    C_PEACH,  9.8, 4.3),
    ]
    for txt, col, x, y in stretches:
        ax.text(x, y, txt, fontsize=9, color=col, family="monospace")

    arrow(ax, (7, 3.9), (7, 3.2), color=C_YELLOW, lw=3)

    rounded_box(ax, (3.0, 1.8), 8.0, 1.2,
                "Result: (671, 40, 3)  =  80,520 floats\n"
                "All vertices in ONE numpy C-level loop",
                color=C_SURFACE, edge_color=C_YELLOW, fontsize=11, lw=2.5,
                text_color=C_YELLOW)

    ax.text(7, 1.2,
            "N=671 (12 strands x 56 segs)     R=40 ring segments     3=xyz",
            fontsize=8, color=C_DIM, ha="center", family="monospace")

    # ── Text below ──
    txt = (
        "Traditional approach: two nested Python for-loops (671 x 40 = 26,840 iterations),\n"
        "each computing one vertex with Python-level math. Numpy broadcasting replaces this\n"
        "with a single C-level operation over the entire (671, 40, 3) array. Same math,\n"
        "~100x faster because the Python interpreter never touches individual floats.\n"
        "\n"
        "Normals are computed the same way: cross products via broadcasting, then batch-\n"
        "normalised with np.linalg.norm(all_normals, axis=3, keepdims=True)."
    )
    add_body_text(fig, txt, x=0.06, y=0.30, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 10 – Why Scalar Math Beats Numpy for Tiny Arrays
# ════════════════════════════════════════════════════════════════
def page_scalar_vs_numpy():
    fig = new_page()
    add_title(fig, "Why Scalar Math Beats Numpy for Tiny Arrays")

    # ── Diagram: overhead comparison ──
    ax = fig.add_axes([0.08, 0.50, 0.84, 0.35])
    ax.set_facecolor(C_BG)

    categories = ["np.dot([a,b,c],\n[d,e,f])", "a*d + b*e + c*f"]
    # Stacked bar: overhead vs actual compute
    overhead = [20, 0]      # microseconds
    compute = [0.01, 0.1]

    y_pos = [0, 1]
    bars1 = ax.barh(y_pos, overhead, color=C_RED, height=0.5,
                    label="Function overhead", edgecolor=C_OVERLAY)
    bars2 = ax.barh(y_pos, compute, left=overhead, color=C_GREEN,
                    height=0.5, label="Actual computation",
                    edgecolor=C_OVERLAY)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories, fontsize=11, color=C_TEXT,
                       family="monospace")
    ax.set_xlabel("Time (\u00b5s)", fontsize=11, color=C_TEXT,
                  family="monospace")
    ax.invert_yaxis()
    ax.set_xlim(0, 25)

    ax.text(21, 0, "~20 \u00b5s", va="center", fontsize=11, color=C_RED,
            fontweight="bold", family="monospace")
    ax.text(1.5, 1, "~0.1 \u00b5s", va="center", fontsize=11,
            color=C_GREEN, fontweight="bold", family="monospace")

    ax.tick_params(colors=C_TEXT, labelsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(C_OVERLAY)
    ax.spines["left"].set_color(C_OVERLAY)
    leg = ax.legend(fontsize=9, framealpha=0.3, facecolor=C_SURFACE,
                    edgecolor=C_OVERLAY, labelcolor=C_TEXT, loc="upper right")

    # ── Text explanation ──
    txt = (
        "Numpy is designed for large arrays. For a 3-element dot product, the actual\n"
        "math (3 multiplies + 2 adds) takes ~0.01us. But numpy's function call overhead\n"
        "dominates: parsing Python arguments (~5us), checking array types/shapes (~5us),\n"
        "allocating a result array (~5us), wrapping the result as a Python object (~5us).\n"
        "Total: ~20us for 3 multiplications.\n"
        "\n"
        "Plain Python scalar math (a*d + b*e + c*f) takes ~0.1us -- 200x faster.\n"
        "\n"
        "This matters for parallel transport frames, where each of 672 iterations computes\n"
        "a dot product, cross product, and rotation. With numpy: 672 x 75us = 50ms overhead.\n"
        "With scalars: 672 x 0.5us = 0.3ms. The fix: pre-compute tangents in one numpy batch,\n"
        "then loop with plain Python floats.\n"
        "\n"
        "Rule of thumb: numpy is 100x FASTER for arrays with 1000+ elements (C loop amortises\n"
        "the overhead). But 200x SLOWER for tiny arrays (3 elements) where overhead dominates."
    )
    add_body_text(fig, txt, x=0.06, y=0.44, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 11 – Performance Comparison (bar chart)
# ════════════════════════════════════════════════════════════════
def page_performance():
    fig = new_page()
    add_title(fig, "Performance Comparison",
              "Chain rebuild time for 43 strands across 4 chains")

    ax = fig.add_axes([0.12, 0.42, 0.78, 0.42])
    ax.set_facecolor(C_BG)

    methods = ["Original\n(Python loops +\nper-vertex GL)",
               "Display List +\nNumpy mesh",
               "VBO + Numpy\n(current)"]
    times = [3060, 175, 43]
    fps = [f"{1000/t:.1f} FPS" for t in times]
    colors = [C_RED, C_PEACH, C_GREEN]

    bars = ax.barh(range(len(methods)), times, color=colors,
                   edgecolor=C_OVERLAY, linewidth=1.5, height=0.55)

    ax.set_yticks(range(len(methods)))
    ax.set_yticklabels(methods, fontsize=11, color=C_TEXT,
                       family="monospace")
    ax.set_xlabel("Chain Rebuild Time (ms)", fontsize=11, color=C_TEXT,
                  family="monospace")
    ax.invert_yaxis()

    for i, (bar, t, f) in enumerate(zip(bars, times, fps)):
        w = bar.get_width()
        offset = max(w * 0.02, 60)
        ax.text(w + offset, bar.get_y() + bar.get_height()/2,
                f"{t} ms  ({f})", va="center", fontsize=11,
                color=colors[i], fontweight="bold", family="monospace")

    ax.annotate("17.5\u00d7", xy=(175, 1), xytext=(700, 1.35),
                fontsize=11, color=C_PEACH, family="monospace",
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_PEACH, lw=1.5))
    ax.annotate("71\u00d7", xy=(43, 2), xytext=(700, 2.35),
                fontsize=11, color=C_GREEN, family="monospace",
                fontweight="bold",
                arrowprops=dict(arrowstyle="->", color=C_GREEN, lw=1.5))

    ax.set_xlim(0, 3600)
    ax.tick_params(colors=C_TEXT, labelsize=10)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(C_OVERLAY)
    ax.spines["left"].set_color(C_OVERLAY)
    ax.xaxis.label.set_color(C_TEXT)
    ax.xaxis.set_major_locator(plt.MultipleLocator(500))
    ax.grid(axis="x", color=C_OVERLAY, alpha=0.3, lw=0.5)

    # ── Text below ──
    txt = (
        "ORIGINAL: Each strand's tube was built with nested Python for-loops, and each vertex\n"
        "was sent to the GPU individually with glVertex3f(). For 43 strands, this meant millions\n"
        "of Python-level operations per frame. Result: ~3,060ms per chain rebuild, ~0.3 FPS.\n"
        "\n"
        "DISPLAY LIST + NUMPY: Replaced Python loops with numpy broadcasting for mesh construction,\n"
        "and per-vertex GL calls with glVertexPointer + glDrawArrays. OpenGL display lists cached\n"
        "the draw commands. Result: 17.5x speedup to ~175ms, but display lists are deprecated.\n"
        "\n"
        "VBO + NUMPY (current): Replaced display lists with VBOs stored in GPU memory. Only the\n"
        "affected chain rebuilds during drag; others render from cached GPU buffers in ~0.1ms.\n"
        "Combined with float32 arrays and scalar parallel-transport: 71x total speedup to ~43ms."
    )
    add_body_text(fig, txt, x=0.06, y=0.36, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Page 12 – Summary
# ════════════════════════════════════════════════════════════════
def page_summary():
    fig = new_page()
    add_title(fig, "Summary: Key Optimisation Techniques")

    txt = (
        "1. CHAIN-BASED RENDERING\n"
        "   Only 4 chain roots do rendering work, not all 43 strands. Non-root strands\n"
        "   return immediately from draw(). Cost scales with chain count, not strand count.\n"
        "\n"
        "\n"
        "2. THREE-LAYER CACHE with VERSION TRACKING\n"
        "   Each strand has a _geom_version integer. Cache keys include version tuples.\n"
        "   When a control point moves, only that strand's version increments, causing\n"
        "   cache misses only in the affected chain. All other chains hit every layer.\n"
        "\n"
        "\n"
        "3. NUMPY BROADCASTING for MESH CONSTRUCTION\n"
        "   The (N, R, 3) vertex array is computed in one C-level operation instead of\n"
        "   26,840 Python iterations. Uses float32 arrays that OpenGL reads directly.\n"
        "\n"
        "\n"
        "4. SCALAR MATH for SEQUENTIAL OPERATIONS\n"
        "   Parallel transport frames must be computed sequentially. Plain Python float\n"
        "   math avoids numpy's ~20us per-call overhead on 3-element arrays. Result:\n"
        "   672 iterations in 0.3ms instead of 50ms.\n"
        "\n"
        "\n"
        "5. VBO for STATIC CHAINS, CLIENT-SIDE ARRAYS for DYNAMIC\n"
        "   Non-affected chains keep geometry in GPU VRAM (VBO) -- rendering costs ~0.1ms.\n"
        "   The affected chain uses client-side arrays because its data changes every frame.\n"
        "   VBO cleanup is deferred during drag to avoid GPU sync stalls.\n"
        "\n"
        "\n"
        "6. DEFERRED VBO CLEANUP\n"
        "   During drag, _defer_vbo_cleanup prevents glDeleteBuffers from running.\n"
        "   Stale VBO entries accumulate (max 30) but aren't freed until the drag ends.\n"
        "   This avoids expensive GPU pipeline flushes during interactive operations.\n"
        "\n"
        "\n"
        "RESULT:  3,060ms -> 43ms  (71x faster)  |  0.3 FPS -> 25 FPS"
    )
    add_body_text(fig, txt, x=0.06, y=0.88, fontsize=10, width=95)
    return fig


# ════════════════════════════════════════════════════════════════
#  NEW (V3) Page – Dirty Strand and Cache State Flow
# ════════════════════════════════════════════════════════════════
def page_dirty_state():
    fig = new_page()
    add_title(fig, "Dirty Strand + Cache State Flow",
              "How _geom_version and cache keys prevent stale renders")

    ax = fig.add_axes([0.04, 0.32, 0.92, 0.52])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 8)
    ax.set_facecolor(C_BG)
    ax.axis("off")

    rounded_box(ax, (0.7, 5.5), 2.8, 1.4, "Clean Strand\n(version = N)",
                color=C_SURFACE, edge_color=C_GREEN, lw=2, fontsize=9.5)
    rounded_box(ax, (4.3, 5.5), 3.2, 1.4, "Dirty Marked\n_geom_version: N \u2192 N+1",
                color=C_SURFACE, edge_color=C_RED, lw=2, fontsize=9.5)
    rounded_box(ax, (8.3, 5.5), 2.8, 1.4, "Drag Frame\n(defer cleanup)",
                color=C_SURFACE, edge_color=C_PEACH, lw=2, fontsize=9.5)
    rounded_box(ax, (11.7, 5.5), 1.8, 1.4, "Stable\nFrame",
                color=C_SURFACE, edge_color=C_GREEN, lw=2, fontsize=9.5)

    arrow(ax, (3.6, 6.2), (4.2, 6.2), color=C_YELLOW, lw=2.5)
    arrow(ax, (7.6, 6.2), (8.2, 6.2), color=C_YELLOW, lw=2.5)
    arrow(ax, (11.2, 6.2), (11.6, 6.2), color=C_YELLOW, lw=2.5)

    ax.text(9.7, 4.9, "If VBO key matches unchanged chain \u2192 HIT",
            color=C_GREEN, fontsize=8.5, family="monospace", ha="center")
    ax.text(9.7, 4.55, "If versions changed \u2192 MISS \u2192 fresh arrays",
            color=C_RED, fontsize=8.5, family="monospace", ha="center")

    rounded_box(ax, (0.8, 2.6), 6.0, 1.6,
                "Cache Key Inputs\n"
                "(curve_segments, tube_segments,\n"
                " tuple((id(strand), _geom_version), ...))",
                color=C_SURFACE, edge_color=C_ACCENT, lw=2, fontsize=8.8)

    rounded_box(ax, (7.5, 2.6), 5.8, 1.6,
                "During Drag\n"
                "_defer_vbo_cleanup = True\n"
                "Old VBO objects can stay alive temporarily,\n"
                "but wrong versions cannot be selected",
                color=C_SURFACE, edge_color=C_MAUVE, lw=2, fontsize=8.8)

    arrow(ax, (6.9, 3.4), (7.4, 3.4), color=C_ACCENT, lw=2.2)

    rounded_box(ax, (3.8, 0.7), 6.2, 1.2,
                "Key Rule: Version mismatch = stale cache bypassed automatically",
                color=C_OVERLAY, edge_color=C_YELLOW, lw=2.4,
                text_color=C_YELLOW, fontsize=9.8)

    txt = (
        "A dirty strand is any strand whose geometry update increments _geom_version. Cache keys include\n"
        "that version for every strand in the chain, so stale entries are safe to keep temporarily: they\n"
        "simply do not match the new key. During drag, VBO deletion is deferred to avoid GPU sync stalls,\n"
        "while non-affected chains can still hit cached VBOs and render quickly."
    )
    add_body_text(fig, txt, x=0.06, y=0.28, fontsize=9.5)
    return fig


# ════════════════════════════════════════════════════════════════
#  Assemble PDF
# ════════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        description="Generate rendering pipeline V3 PDF documentation."
    )
    parser.add_argument(
        "--printable",
        action="store_true",
        help="Generate printer-friendly PDF (white background, dark text).",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional output PDF path.",
    )
    args = parser.parse_args()

    configure_theme(printable=args.printable)

    global OUT_PDF
    if args.output:
        OUT_PDF = os.path.abspath(args.output)
    elif args.printable:
        OUT_PDF = os.path.join(OUT_DIR, "rendering_pipeline_v3_print.pdf")
    else:
        OUT_PDF = os.path.join(OUT_DIR, "rendering_pipeline_v3.pdf")
    resolved_path = resolve_unlocked_output_path(OUT_PDF)
    if resolved_path != OUT_PDF:
        print(f"Target file is locked, writing to: {resolved_path}")
        OUT_PDF = resolved_path

    pages = [
        ("Title Page",              page_title),
        ("Old vs New",              page_old_vs_new),
        ("Scene Structure",         page_scene_structure),
        ("Tube Construction",       page_tube_construction),
        ("Tube Construction Detail", page_tube_detail),
        ("Cache System",            page_cache_system),
        ("Dirty State",             page_dirty_state),
        ("Drag Flow",               page_drag_flow),
        ("Drag Detail",             page_drag_detail),
        ("VBO vs Client-Side",      page_vbo_vs_clientside),
        ("Numpy Broadcasting",      page_numpy_broadcasting),
        ("Scalar vs Numpy",         page_scalar_vs_numpy),
        ("Performance",             page_performance),
        ("Summary",                 page_summary),
    ]

    print(f"Generating {len(pages)}-page PDF -> {OUT_PDF}")
    with PdfPages(OUT_PDF) as pdf:
        for name, fn in pages:
            print(f"  Page: {name}")
            fig = fn()
            pdf.savefig(fig, facecolor=fig.get_facecolor())
            plt.close(fig)
    print(f"Done! {OUT_PDF}")


if __name__ == "__main__":
    main()
