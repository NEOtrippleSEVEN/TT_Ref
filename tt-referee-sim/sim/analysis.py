"""Matplotlib analysis charts — FPS comparison, detection heatmaps, cost vs accuracy, game stats."""

import random

import matplotlib
matplotlib.use("Agg")  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np

from engine.physics import simulate
from engine.camera import compare_cameras, CAMERA_PRESETS
from engine.trajectories import get_shot, SHOT_PRESETS
from engine.ai_player import AIPlayer, PLAYSTYLES
from engine.game import simulate_game
from engine import table


def _style_chart(ax, title):
    """Apply dark theme styling to chart."""
    ax.set_facecolor("#0f0f1a")
    ax.set_title(title, color="#e0e0e0", fontsize=13, fontweight="bold", pad=12)
    ax.tick_params(colors="#888888", labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color("#333333")
    ax.spines["left"].set_color("#333333")
    ax.xaxis.label.set_color("#aaaaaa")
    ax.yaxis.label.set_color("#aaaaaa")


def chart_detection_vs_speed(save_path=None):
    """Chart 1: Detection Rate vs Ball Speed.

    Three lines (60fps, 120fps, 200fps) across ball speeds.
    """
    speed_shots = ["slow_rally", "medium_rally", "fast_topspin", "smash"]
    speeds = [SHOT_PRESETS[k]["speed"] for k in speed_shots]

    results_by_cam = {k: [] for k in CAMERA_PRESETS}

    for shot_key in speed_shots:
        state = get_shot(shot_key)
        positions, events = simulate(state)
        cam_results = compare_cameras(positions, events)
        for cam_key in CAMERA_PRESETS:
            results_by_cam[cam_key].append(cam_results[cam_key]["detection_rate"])

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "Detection Rate vs Ball Speed")

    colors = {"cheap": "#dc3545", "mid": "#ffc107", "arducam": "#28a745"}
    markers = {"cheap": "o", "mid": "s", "arducam": "D"}

    for cam_key, rates in results_by_cam.items():
        preset = CAMERA_PRESETS[cam_key]
        ax.plot(
            speeds, rates,
            color=colors[cam_key], marker=markers[cam_key],
            linewidth=2, markersize=8, label=f"{preset['fps']} FPS ({preset['label']})",
        )

    ax.set_xlabel("Ball Speed (km/h)")
    ax.set_ylabel("Detection Rate (%)")
    ax.set_ylim(0, 105)
    ax.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="#e0e0e0", fontsize=9)
    ax.grid(True, alpha=0.15)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_ball_distance_between_frames(save_path=None):
    """Chart 2: Ball Distance Between Frames.

    Grouped bar chart: each speed x each fps.
    """
    speed_shots = ["slow_rally", "medium_rally", "fast_topspin", "smash"]
    speeds = [SHOT_PRESETS[k]["speed"] for k in speed_shots]
    speed_labels = [f"{s} km/h" for s in speeds]

    fps_values = [p["fps"] for p in CAMERA_PRESETS.values()]
    cam_labels = [f"{p['fps']}fps" for p in CAMERA_PRESETS.values()]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "Ball Distance Between Frames")

    x = np.arange(len(speeds))
    width = 0.25
    colors = ["#dc3545", "#ffc107", "#28a745"]

    for i, (fps, color, label) in enumerate(zip(fps_values, colors, cam_labels)):
        distances = [(s / 3.6 / fps) * 100 for s in speeds]  # cm
        bars = ax.bar(x + i * width, distances, width, color=color, label=label, alpha=0.85)
        for bar, d in zip(bars, distances):
            ax.text(
                bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.3,
                f"{d:.1f}", ha="center", va="bottom", fontsize=8, color="#aaa",
            )

    # Reference line at ball diameter (4cm)
    ax.axhline(y=4, color="#e94560", linestyle="--", linewidth=1.5, alpha=0.7)
    ax.text(len(speeds) - 0.5, 4.3, "Ball diameter (4cm)", color="#e94560", fontsize=9, ha="right")

    ax.set_xticks(x + width)
    ax.set_xticklabels(speed_labels)
    ax.set_ylabel("Distance (cm)")
    ax.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="#e0e0e0", fontsize=9)
    ax.grid(True, alpha=0.15, axis="y")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_frame_sampling(save_path=None):
    """Chart 3: Frame Sampling Visualization.

    Timeline showing frame positions for one trajectory at 3 fps rates.
    """
    state = get_shot("fast_topspin")
    positions, events = simulate(state)

    fig, axes = plt.subplots(3, 1, figsize=(10, 4), sharex=True)
    fig.set_facecolor("#0f0f1a")
    fig.suptitle("Frame Sampling Visualization (Fast Topspin @ 80 km/h)",
                 color="#e0e0e0", fontsize=13, fontweight="bold")

    colors_det = {"cheap": "#dc3545", "mid": "#ffc107", "arducam": "#28a745"}
    colors_miss = "#444444"

    for idx, (cam_key, preset) in enumerate(CAMERA_PRESETS.items()):
        ax = axes[idx]
        ax.set_facecolor("#0f0f1a")

        frames = compare_cameras(positions, events)[cam_key]["frames"]

        for f in frames:
            color = colors_det[cam_key] if f.detected else colors_miss
            ax.scatter(f.t, 0, c=color, s=15, marker="|", linewidths=1.5)

        ax.set_ylim(-0.5, 0.5)
        ax.set_yticks([])
        ax.set_ylabel(f"{preset['fps']}fps", color="#aaa", fontsize=10, rotation=0, labelpad=40)
        ax.tick_params(colors="#888888", labelsize=8)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_visible(False)
        ax.spines["bottom"].set_color("#333333")

    axes[-1].set_xlabel("Time (s)", color="#aaa")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_cost_vs_accuracy(save_path=None):
    """Chart 4: Cost vs Accuracy at 80 km/h.

    Scatter plot with annotations.
    """
    state = get_shot("fast_topspin")
    positions, events = simulate(state)
    cam_results = compare_cameras(positions, events)

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "Cost vs Detection Accuracy (80 km/h)")

    colors = {"cheap": "#dc3545", "mid": "#ffc107", "arducam": "#28a745"}

    for cam_key, result in cam_results.items():
        cost = result["cost"]
        rate = result["detection_rate"]
        ax.scatter(cost, rate, c=colors[cam_key], s=150, zorder=5, edgecolors="white", linewidth=1.5)
        ax.annotate(
            f"  {result['label']}\n  {rate}%",
            (cost, rate), fontsize=9, color="#e0e0e0",
            xytext=(12, -5), textcoords="offset points",
        )

    ax.set_xlabel("Cost (EUR)")
    ax.set_ylabel("Detection Rate (%)")
    ax.set_ylim(0, 105)
    ax.set_xlim(0, 100)
    ax.grid(True, alpha=0.15)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_matchup_heatmap(n_games=5, save_path=None):
    """Chart 5: Playstyle Matchup Heatmap.

    Grid showing win rates of each playstyle vs every other.
    """
    style_keys = list(PLAYSTYLES.keys())
    n = len(style_keys)
    win_matrix = np.zeros((n, n))

    for i, s1 in enumerate(style_keys):
        for j, s2 in enumerate(style_keys):
            if i == j:
                win_matrix[i][j] = 50.0
                continue
            wins = 0
            for seed in range(n_games):
                random.seed(seed * 100 + i * 10 + j)
                p1 = AIPlayer("P1", s1, 1)
                p2 = AIPlayer("P2", s2, 2)
                result = simulate_game(p1, p2)
                if result.match.winner == 1:
                    wins += 1
            win_matrix[i][j] = wins / n_games * 100

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "Playstyle Matchup Win Rates (P1 vs P2)")

    labels = [PLAYSTYLES[k]["label"] for k in style_keys]
    im = ax.imshow(win_matrix, cmap="RdYlGn", vmin=0, vmax=100, aspect="auto")

    ax.set_xticks(range(n))
    ax.set_yticks(range(n))
    ax.set_xticklabels(labels, rotation=45, ha="right", fontsize=9)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("P2 Style")
    ax.set_ylabel("P1 Style")

    for i in range(n):
        for j in range(n):
            val = win_matrix[i][j]
            color = "white" if val < 30 or val > 70 else "black"
            ax.text(j, i, f"{val:.0f}%", ha="center", va="center",
                    fontsize=10, fontweight="bold", color=color)

    cbar = fig.colorbar(im, ax=ax, shrink=0.8)
    cbar.set_label("P1 Win Rate %", color="#aaa")
    cbar.ax.tick_params(colors="#888")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_rally_length_distribution(n_games=3, save_path=None):
    """Chart 6: Rally Length Distribution across different matchups."""
    matchups = [
        ("aggressive", "defensive", "#e94560"),
        ("pro", "pro", "#28a745"),
        ("beginner", "beginner", "#ffc107"),
    ]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "Rally Length Distribution by Matchup")

    for s1, s2, color in matchups:
        all_lengths = []
        for seed in range(n_games):
            random.seed(seed * 50)
            p1 = AIPlayer("P1", s1, 1)
            p2 = AIPlayer("P2", s2, 2)
            result = simulate_game(p1, p2)
            all_lengths.extend(r.rally_length for r in result.rallies)

        label = f"{PLAYSTYLES[s1]['label']} vs {PLAYSTYLES[s2]['label']}"
        bins = range(1, max(all_lengths) + 2) if all_lengths else range(1, 10)
        ax.hist(all_lengths, bins=bins, alpha=0.6, color=color, label=label, edgecolor=color)

    ax.set_xlabel("Rally Length (shots)")
    ax.set_ylabel("Frequency")
    ax.legend(facecolor="#1a1a2e", edgecolor="#333", labelcolor="#e0e0e0", fontsize=9)
    ax.grid(True, alpha=0.15, axis="y")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def chart_point_reasons(n_games=3, save_path=None):
    """Chart 7: How points are won — breakdown by reason."""
    all_reasons = {}
    for seed in range(n_games):
        random.seed(seed * 77)
        p1 = AIPlayer("P1", "allround", 1)
        p2 = AIPlayer("P2", "allround", 2)
        result = simulate_game(p1, p2)
        for r in result.rallies:
            all_reasons[r.reason] = all_reasons.get(r.reason, 0) + 1

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.set_facecolor("#0f0f1a")
    _style_chart(ax, "How Points Are Won")

    reasons = sorted(all_reasons.items(), key=lambda x: -x[1])
    labels = [r[0] for r in reasons]
    counts = [r[1] for r in reasons]
    colors = ["#e94560", "#28a745", "#ffc107", "#4ecdc4", "#a855f7", "#64748b", "#fb923c"]

    bars = ax.barh(labels, counts, color=colors[:len(labels)], edgecolor="#333", alpha=0.85)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(count), va="center", fontsize=10, color="#e0e0e0")

    ax.set_xlabel("Count")
    ax.invert_yaxis()
    ax.grid(True, alpha=0.15, axis="x")

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, facecolor=fig.get_facecolor())
    return fig


def generate_all_charts(output_dir="."):
    """Generate all analysis charts and save to output directory."""
    import os
    os.makedirs(output_dir, exist_ok=True)

    paths = []

    path = os.path.join(output_dir, "chart_detection_vs_speed.png")
    chart_detection_vs_speed(save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_ball_distance.png")
    chart_ball_distance_between_frames(save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_frame_sampling.png")
    chart_frame_sampling(save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_cost_vs_accuracy.png")
    chart_cost_vs_accuracy(save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_matchup_heatmap.png")
    print("  Generating matchup heatmap (running AI games)...")
    chart_matchup_heatmap(n_games=3, save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_rally_distribution.png")
    print("  Generating rally distribution...")
    chart_rally_length_distribution(n_games=3, save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    path = os.path.join(output_dir, "chart_point_reasons.png")
    print("  Generating point reasons chart...")
    chart_point_reasons(n_games=3, save_path=path)
    paths.append(path)
    print(f"  Saved: {path}")

    plt.close("all")
    return paths
