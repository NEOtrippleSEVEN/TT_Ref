# TT Referee Simulation

AI-powered table tennis referee simulation that proves why specific camera hardware (Arducam OV9281, 200fps global shutter) is needed for real-time ball tracking. Built for a FabLab hardware funding pitch.

## How It Works

Three decoupled engines simulate the full referee pipeline:

1. **Physics Engine** — generates ground truth ball trajectories (gravity, drag, Magnus/spin, bounce, net collision)
2. **Camera Engine** — simulates what different cameras actually capture (frame rate, motion blur, detection probability)
3. **Referee Engine** — makes scoring decisions using *only* camera data (never ground truth)

The gap between ground truth and referee accuracy is the hardware justification.

## Setup

```bash
cd tt-referee-sim
pip install -r requirements.txt
```

## Usage

```bash
python main.py play       # Interactive Pygame visualizer
python main.py analyze    # Generate comparison charts (saved to output/)
python main.py report     # Generate PDF/PNG report for presentation
python main.py test       # Run all tests
python main.py demo       # Full demo: all shots + stats + report generation
```

### Visualizer Controls

| Key | Action |
|-----|--------|
| SPACE | Play / pause animation |
| R | Reset trajectory |
| N | Next shot preset |
| 1 / 2 / 3 | Switch camera (Budget 60fps / Mid 120fps / Arducam 200fps) |
| T | Toggle top-down / side view |
| S | Score point from current trajectory |
| Q | Quit |

## Project Structure

```
tt-referee-sim/
├── engine/            # Pure Python — no UI dependencies
│   ├── types.py       # Dataclasses: Vec3, BallState, BounceEvent, CameraFrame, Match
│   ├── table.py       # ITTF table dimensions and physical constants
│   ├── physics.py     # Ball trajectory simulation (1000Hz timestep)
│   ├── camera.py      # Virtual camera: 3 presets, blur model, detection probability
│   ├── referee.py     # ITTF scoring rules, bounce/net/out detection from camera frames
│   └── trajectories.py # 7 shot presets (30–100 km/h, various spins)
├── sim/
│   ├── visualizer.py  # Pygame real-time visualization
│   ├── analysis.py    # Matplotlib comparison charts
│   └── report.py      # PDF/PNG report generator
├── tests/             # 25 tests (physics, camera, referee, trajectories)
├── main.py            # CLI entry point
└── requirements.txt
```

## Tests

```bash
python main.py test
# or
pytest tests/ -v
```
