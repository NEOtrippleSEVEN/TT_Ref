"""Generate PDF/PNG report for FabLab presentation."""

import os
import random

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import numpy as np

from engine.physics import simulate
from engine.camera import compare_cameras, CAMERA_PRESETS
from engine.trajectories import get_shot, SHOT_PRESETS
from engine.ai_player import AIPlayer, PLAYSTYLES
from engine.game import simulate_game
from engine import table


def generate_report(output_dir=".", filename="tt_referee_report"):
    """Generate a multi-panel report combining all key findings.

    Saves as both PDF and PNG.
    """
    os.makedirs(output_dir, exist_ok=True)

    # Run simulations for key shots
    speed_shots = ["slow_rally", "medium_rally", "fast_topspin", "smash"]
    all_results = {}
    for key in speed_shots:
        state = get_shot(key)
        positions, events = simulate(state)
        all_results[key] = compare_cameras(positions, events)

    # Run a sample AI game for stats
    random.seed(42)
    p1 = AIPlayer("Aggressive", "aggressive", 1)
    p2 = AIPlayer("Defensive", "defensive", 2)
    game_result = simulate_game(p1, p2)

    # Create figure
    fig = plt.figure(figsize=(16, 22))
    fig.set_facecolor("#0f0f1a")

    gs = gridspec.GridSpec(5, 2, hspace=0.35, wspace=0.3)

    # ---- Title ----
    fig.text(
        0.5, 0.97, "AI Table Tennis Referee — Hardware Justification",
        ha="center", va="top", fontsize=20, fontweight="bold", color="#e94560",
    )
    fig.text(
        0.5, 0.955,
        "Why the Arducam OV9281 (200fps, Global Shutter) is the right camera for real-time ball tracking",
        ha="center", va="top", fontsize=11, color="#aaaaaa",
    )

    # ---- Chart 1: Detection Rate vs Speed ----
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor("#0f0f1a")
    ax1.set_title("Detection Rate vs Ball Speed", color="#e0e0e0", fontsize=12, fontweight="bold")

    speeds = [SHOT_PRESETS[k]["speed"] for k in speed_shots]
    colors = {"cheap": "#dc3545", "mid": "#ffc107", "arducam": "#28a745"}

    for cam_key in CAMERA_PRESETS:
        rates = [all_results[sk][cam_key]["detection_rate"] for sk in speed_shots]
        preset = CAMERA_PRESETS[cam_key]
        ax1.plot(speeds, rates, color=colors[cam_key], marker="o", linewidth=2,
                 label=f"{preset['fps']}fps")

    ax1.set_xlabel("Ball Speed (km/h)", color="#aaa")
    ax1.set_ylabel("Detection Rate (%)", color="#aaa")
    ax1.set_ylim(0, 105)
    ax1.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="#e0e0e0", fontsize=9)
    ax1.grid(True, alpha=0.15)
    ax1.tick_params(colors="#888")
    for spine in ax1.spines.values():
        spine.set_color("#333")

    # ---- Chart 2: Ball Distance Between Frames ----
    ax2 = fig.add_subplot(gs[0, 1])
    ax2.set_facecolor("#0f0f1a")
    ax2.set_title("Ball Travel Between Frames", color="#e0e0e0", fontsize=12, fontweight="bold")

    x = np.arange(len(speeds))
    width = 0.25
    cam_colors = list(colors.values())

    for i, (cam_key, preset) in enumerate(CAMERA_PRESETS.items()):
        distances = [(s / 3.6 / preset["fps"]) * 100 for s in speeds]
        ax2.bar(x + i * width, distances, width, color=cam_colors[i],
                label=f"{preset['fps']}fps", alpha=0.85)

    ax2.axhline(y=4, color="#e94560", linestyle="--", linewidth=1.5, alpha=0.7)
    ax2.text(3.5, 4.5, "Ball diameter", color="#e94560", fontsize=8, ha="right")
    ax2.set_xticks(x + width)
    ax2.set_xticklabels([f"{s}km/h" for s in speeds])
    ax2.set_ylabel("Distance (cm)", color="#aaa")
    ax2.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="#e0e0e0", fontsize=8)
    ax2.grid(True, alpha=0.15, axis="y")
    ax2.tick_params(colors="#888")
    for spine in ax2.spines.values():
        spine.set_color("#333")

    # ---- Chart 3: Camera Comparison Table ----
    ax3 = fig.add_subplot(gs[1, :])
    ax3.set_facecolor("#0f0f1a")
    ax3.axis("off")
    ax3.set_title("Camera Comparison at 80 km/h (Fast Topspin)",
                   color="#e0e0e0", fontsize=12, fontweight="bold", pad=15)

    topspin_results = all_results["fast_topspin"]
    headers = ["Camera", "FPS", "Resolution", "Shutter", "Detection %",
               "Confidence %", "Blur (px)", "Cost"]
    table_data = []
    for cam_key, result in topspin_results.items():
        table_data.append([
            result["label"],
            str(result["fps"]),
            f"{result['resolution'][0]}x{result['resolution'][1]}",
            "Global" if result["global_shutter"] else "Rolling",
            f"{result['detection_rate']}%",
            f"{result['avg_confidence']}%",
            f"{result['avg_blur_px']}",
            f"EUR {result['cost']}",
        ])

    tbl = ax3.table(
        cellText=table_data, colLabels=headers,
        cellLoc="center", loc="center",
        colColours=["#e94560"] * len(headers),
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(10)
    tbl.scale(1, 1.8)
    for key, cell in tbl.get_celld().items():
        cell.set_edgecolor("#333")
        if key[0] == 0:
            cell.set_text_props(color="white", fontweight="bold")
            cell.set_facecolor("#e94560")
        else:
            cell.set_facecolor("#1a1a2e")
            cell.set_text_props(color="#e0e0e0")
            if key[0] == 3:  # Arducam row
                cell.set_facecolor("#1a3a2a")

    # ---- Chart 4: Cost vs Accuracy ----
    ax4 = fig.add_subplot(gs[2, 0])
    ax4.set_facecolor("#0f0f1a")
    ax4.set_title("Cost vs Accuracy (80 km/h)", color="#e0e0e0", fontsize=12, fontweight="bold")

    for cam_key, result in topspin_results.items():
        ax4.scatter(result["cost"], result["detection_rate"],
                    c=colors[cam_key], s=150, zorder=5, edgecolors="white", linewidth=1.5)
        ax4.annotate(
            f"  {result['label']}", (result["cost"], result["detection_rate"]),
            fontsize=8, color="#e0e0e0", xytext=(8, -3), textcoords="offset points",
        )

    ax4.set_xlabel("Cost (EUR)", color="#aaa")
    ax4.set_ylabel("Detection Rate (%)", color="#aaa")
    ax4.set_ylim(0, 105)
    ax4.set_xlim(0, 100)
    ax4.grid(True, alpha=0.15)
    ax4.tick_params(colors="#888")
    for spine in ax4.spines.values():
        spine.set_color("#333")

    # ---- Chart 5: AI Game Stats ----
    ax5 = fig.add_subplot(gs[2, 1])
    ax5.set_facecolor("#0f0f1a")
    ax5.axis("off")
    ax5.set_title("AI Match Analysis", color="#e0e0e0", fontsize=12, fontweight="bold", pad=15)

    gs2 = game_result.stats
    game_text = (
        f"Aggressive vs Defensive\n"
        f"Final Score: {gs2['p1_points']} - {gs2['p2_points']}\n"
        f"Total Rallies: {gs2['total_rallies']}\n"
        f"Avg Rally Length: {gs2['avg_rally_length']} shots\n"
        f"Max Rally Length: {gs2['max_rally_length']} shots\n\n"
        f"P1 Winners: {gs2['p1_winners']}  |  P2 Winners: {gs2['p2_winners']}\n"
        f"P1 Errors: {gs2['p1_unforced_errors']}  |  P2 Errors: {gs2['p2_unforced_errors']}\n\n"
        f"Point breakdown:\n"
    )
    for reason, count in sorted(gs2["reasons"].items(), key=lambda x: -x[1]):
        game_text += f"  {reason}: {count}\n"

    ax5.text(0.05, 0.95, game_text, transform=ax5.transAxes,
             fontsize=10, color="#e0e0e0", va="top", family="monospace",
             bbox=dict(boxstyle="round,pad=0.5", facecolor="#1a1a2e", edgecolor="#333"))

    # ---- Chart 6: Frame sampling ----
    for i, (cam_key, preset) in enumerate(CAMERA_PRESETS.items()):
        ax = fig.add_subplot(gs[3, 0] if i == 0 else gs[3, 1] if i == 2 else gs[4, 0])
        ax.set_facecolor("#0f0f1a")
        ax.set_title(f"{preset['fps']}fps Frame Coverage", color="#e0e0e0", fontsize=11)

        result = topspin_results[cam_key]
        frames = result["frames"]
        detected = [f for f in frames if f.detected]
        missed = [f for f in frames if not f.detected]

        if detected:
            ax.scatter([f.t for f in detected], [1] * len(detected),
                       c=colors[cam_key], s=10, marker="|", linewidths=2)
        if missed:
            ax.scatter([f.t for f in missed], [0] * len(missed),
                       c="#444", s=10, marker="|", linewidths=2)

        ax.set_ylim(-0.5, 1.5)
        ax.set_yticks([0, 1])
        ax.set_yticklabels(["missed", "detected"], fontsize=8)
        ax.set_xlabel("Time (s)", color="#aaa", fontsize=9)
        ax.tick_params(colors="#888", labelsize=8)
        for spine in ax.spines.values():
            spine.set_color("#333")

    # ---- Summary text ----
    arducam_80 = topspin_results["arducam"]
    cheap_80 = topspin_results["cheap"]

    summary = (
        f"KEY FINDINGS\n\n"
        f"At 80 km/h (fast topspin), the Arducam OV9281 achieves {arducam_80['detection_rate']}% "
        f"detection rate vs {cheap_80['detection_rate']}% for the budget 60fps camera.\n\n"
        f"The ball travels {(80/3.6/60)*100:.1f}cm between frames at 60fps, but only "
        f"{(80/3.6/200)*100:.1f}cm at 200fps — critical for accurate bounce detection.\n\n"
        f"Global shutter eliminates motion blur entirely, averaging {arducam_80['avg_blur_px']}px blur "
        f"vs {cheap_80['avg_blur_px']}px on the budget rolling-shutter camera.\n\n"
        f"AI game simulation ({gs2['total_rallies']} rallies, avg {gs2['avg_rally_length']} shots/rally) "
        f"validates the referee engine works end-to-end with realistic play patterns.\n\n"
        f"HARDWARE BUDGET: EUR 215 total (Pi 5 EUR 95 + Camera EUR 75 + Lens EUR 25 + Accessories EUR 20)"
    )

    fig.text(
        0.5, 0.02, summary,
        ha="center", va="bottom", fontsize=10, color="#e0e0e0",
        bbox=dict(boxstyle="round,pad=0.8", facecolor="#1a3a2a", edgecolor="#28a745", alpha=0.9),
        linespacing=1.5,
    )

    # Save
    pdf_path = os.path.join(output_dir, f"{filename}.pdf")
    png_path = os.path.join(output_dir, f"{filename}.png")

    fig.savefig(pdf_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    fig.savefig(png_path, dpi=150, facecolor=fig.get_facecolor(), bbox_inches="tight")
    plt.close(fig)

    print(f"  Report saved: {pdf_path}")
    print(f"  Report saved: {png_path}")

    return pdf_path, png_path
