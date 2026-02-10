#!/usr/bin/env python3
"""CLI entry point for the TT Referee Simulation.

Usage:
    python main.py play              Launch Pygame visualizer
    python main.py game              Run AI match (text mode) and print stats
    python main.py analyze           Generate comparison charts
    python main.py report            Generate PDF report
    python main.py test              Run all tests
    python main.py demo              Full demo: play each shot, AI game, report
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_play():
    """Launch the Pygame visualizer."""
    print("Launching TT Referee Visualizer...")
    print("Controls: SPACE=play  G=game  R=rally  A=auto  T=view  1/2/3=cam  Q=quit")
    print("-" * 60)
    from sim.visualizer import run_visualizer
    run_visualizer()


def cmd_game():
    """Run an AI match in text mode and print stats."""
    import random
    from engine.ai_player import AIPlayer, PLAYSTYLES

    print("=" * 60)
    print("  AI TABLE TENNIS MATCH")
    print("=" * 60)

    # Parse optional arguments
    styles = list(PLAYSTYLES.keys())
    p1_style = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in styles else "aggressive"
    p2_style = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] in styles else "defensive"

    p1 = AIPlayer("Player 1", p1_style, 1)
    p2 = AIPlayer("Player 2", p2_style, 2)

    print(f"\n  P1: {p1.label} (pwr:{p1.power:.0%} con:{p1.consistency:.0%} spn:{p1.spin_ability:.0%})")
    print(f"  P2: {p2.label} (pwr:{p2.power:.0%} con:{p2.consistency:.0%} spn:{p2.spin_ability:.0%})")
    print()

    from engine.game import simulate_game
    result = simulate_game(p1, p2)
    m = result.match
    s = result.stats

    # Print rally-by-rally
    for i, rally in enumerate(result.rallies):
        score_after = result.match.history[i] if i < len(result.match.history) else {}
        p1s = score_after.get("p1", "?")
        p2s = score_after.get("p2", "?")
        print(f"  Rally {i+1:2d}: {rally.rally_length} shots, "
              f"P{rally.winner} wins ({rally.reason})  [{p1s}-{p2s}]")

    print()
    print(f"  FINAL SCORE: {m.p1_score} - {m.p2_score}")
    print(f"  WINNER: Player {m.winner} ({p1.label if m.winner == 1 else p2.label})")
    print()
    print(f"  Total rallies: {s['total_rallies']}")
    print(f"  Avg rally length: {s['avg_rally_length']} shots")
    print(f"  Max rally length: {s['max_rally_length']} shots")
    print(f"  P1 winners: {s['p1_winners']}  |  P2 winners: {s['p2_winners']}")
    print(f"  P1 errors:  {s['p1_unforced_errors']}  |  P2 errors:  {s['p2_unforced_errors']}")
    print(f"  Point reasons: {dict(sorted(s['reasons'].items(), key=lambda x: -x[1]))}")
    print()
    print("  Available styles: " + ", ".join(styles))
    print("  Usage: python main.py game [p1_style] [p2_style]")
    print("=" * 60)


def cmd_analyze():
    """Generate all analysis charts."""
    print("Generating analysis charts...")
    print("-" * 60)
    from sim.analysis import generate_all_charts
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    paths = generate_all_charts(output_dir=output_dir)
    print(f"\nDone! {len(paths)} charts saved to {output_dir}/")


def cmd_report():
    """Generate the full PDF/PNG report."""
    print("Generating hardware justification report...")
    print("-" * 60)
    from sim.report import generate_report
    output_dir = os.path.join(os.path.dirname(__file__), "output")
    pdf, png = generate_report(output_dir=output_dir)
    print(f"\nDone! Report ready for FabLab presentation.")


def cmd_test():
    """Run all tests."""
    import subprocess
    print("Running tests...")
    print("-" * 60)
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-v"],
        cwd=os.path.dirname(os.path.abspath(__file__)),
    )
    sys.exit(result.returncode)


def cmd_demo():
    """Full demo: all shots, AI game, charts, and report."""
    print("=" * 60)
    print("  TT REFEREE — AI SIMULATION DEMO")
    print("=" * 60)
    print()

    from engine.trajectories import get_shot, list_shots, SHOT_PRESETS
    from engine.physics import simulate
    from engine.camera import compare_cameras, CAMERA_PRESETS

    # Run each shot and show stats
    for key in list_shots():
        preset = SHOT_PRESETS[key]
        state = get_shot(key)
        positions, events = simulate(state)
        cam_results = compare_cameras(positions, events)

        print(f"Shot: {preset['label']} ({preset['speed']} km/h)")
        print(f"  Duration: {positions[-1].t:.3f}s  |  Events: {len(events)}")

        for cam_key, result in cam_results.items():
            det = result["detection_rate"]
            marker = "***" if det > 85 else "   "
            print(f"  {marker} {result['label']:30s}  Detection: {det:5.1f}%  "
                  f"Blur: {result['avg_blur_px']:5.1f}px  "
                  f"Bounces: {result['bounces_detected']}/{result['bounces_total']}")
        print()

    # Run AI match
    print("-" * 60)
    cmd_game()

    # Generate report
    print("-" * 60)
    cmd_report()

    # Generate charts
    print("-" * 60)
    cmd_analyze()

    print()
    print("=" * 60)
    print("  Demo complete! Check the 'output' folder for reports.")
    print("=" * 60)


COMMANDS = {
    "play": cmd_play,
    "game": cmd_game,
    "analyze": cmd_analyze,
    "report": cmd_report,
    "test": cmd_test,
    "demo": cmd_demo,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(__doc__)
        print("Available commands:")
        for name, func in COMMANDS.items():
            print(f"  {name:12s} {func.__doc__}")
        sys.exit(1)

    COMMANDS[sys.argv[1]]()


if __name__ == "__main__":
    main()
