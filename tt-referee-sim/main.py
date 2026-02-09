#!/usr/bin/env python3
"""CLI entry point for the TT Referee Simulation.

Usage:
    python main.py play              Launch Pygame visualizer
    python main.py analyze           Generate comparison charts
    python main.py report            Generate PDF report
    python main.py test              Run all tests
    python main.py demo              Full demo: play each shot, show stats, generate report
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def cmd_play():
    """Launch the Pygame visualizer."""
    print("Launching TT Referee Visualizer...")
    print("Controls: SPACE=play  R=reset  N=next  1/2/3=camera  T=view  S=score  Q=quit")
    print("-" * 60)
    from sim.visualizer import run_visualizer
    run_visualizer()


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
    """Full demo: run all shots, show stats, generate report."""
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
