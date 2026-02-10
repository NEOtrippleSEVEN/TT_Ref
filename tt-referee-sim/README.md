# TT Referee Simulation

AI-powered table tennis referee simulation that proves why specific camera hardware (Arducam OV9281, 200fps global shutter) is needed for real-time ball tracking. Built for a FabLab hardware funding pitch.

## How It Works

Three decoupled engines simulate the full referee pipeline:

1. **Physics Engine** — generates ground truth ball trajectories (gravity, drag, Magnus/spin, bounce, net collision)
2. **Camera Engine** — simulates what different cameras actually capture (frame rate, motion blur, detection probability)
3. **Referee Engine** — makes scoring decisions using *only* camera data (never ground truth)

Plus two game-level engines:

4. **AI Player Engine** — five playstyles (aggressive, defensive, allround, beginner, pro) with probabilistic shot selection
5. **Game Engine** — full match simulation with serve/return rallies, ITTF scoring (game to 11, win by 2)

The gap between ground truth and referee accuracy is the hardware justification.

## Setup

```bash
cd tt-referee-sim
pip install -r requirements.txt
```

## Usage

```bash
python main.py play       # Interactive Pygame visualizer with AI match mode
python main.py game       # Run AI match in text mode (prints rally-by-rally)
python main.py game aggressive pro   # Specify playstyles for each player
python main.py analyze    # Generate all analysis charts (saved to output/)
python main.py report     # Generate PDF/PNG report for presentation
python main.py test       # Run all 38 tests
python main.py demo       # Full demo: all shots + AI game + charts + report
```

### Visualizer Controls

| Key | Action |
|-----|--------|
| SPACE | Play / pause animation |
| G | Start a full AI game |
| A | Toggle auto-play (auto-advance rallies) |
| R | New random rally |
| T | Toggle top-down / side view |
| 1 / 2 / 3 | Switch camera (Budget 60fps / Mid 120fps / Arducam 200fps) |
| [ / ] | Cycle P1 playstyle |
| - / = | Cycle P2 playstyle |
| Q | Quit |

### AI Playstyles

| Style | Power | Consistency | Spin | Speed |
|-------|-------|-------------|------|-------|
| Aggressive | 90% | 65% | 70% | 85% |
| Defensive | 50% | 90% | 80% | 70% |
| All-Round | 70% | 78% | 75% | 78% |
| Beginner | 40% | 40% | 20% | 50% |
| Professional | 85% | 92% | 95% | 92% |

## Project Structure

```
tt-referee-sim/
├── engine/            # Pure Python — no UI dependencies
│   ├── types.py       # Dataclasses: Vec3, BallState, BounceEvent, CameraFrame, Match
│   ├── table.py       # ITTF table dimensions and physical constants
│   ├── physics.py     # Ball trajectory simulation (1000Hz timestep)
│   ├── camera.py      # Virtual camera: 3 presets, blur model, detection probability
│   ├── referee.py     # ITTF scoring rules, bounce/net/out detection from camera frames
│   ├── trajectories.py # 7 shot presets (30-100 km/h, various spins)
│   ├── ai_player.py   # AI player engine with 5 playstyles
│   └── game.py        # Full match simulation (rallies, scoring, stats)
├── sim/
│   ├── visualizer.py  # Pygame real-time visualization with game mode
│   ├── analysis.py    # 7 Matplotlib analysis charts (camera + game stats)
│   └── report.py      # PDF/PNG report generator
├── tests/             # 38 tests (physics, camera, referee, trajectories, AI, game)
├── main.py            # CLI entry point
└── requirements.txt
```

## Analysis Charts

The `analyze` command generates 7 charts:

1. **Detection Rate vs Ball Speed** — shows Arducam's advantage at high speeds
2. **Ball Distance Between Frames** — how far the ball travels between camera samples
3. **Frame Sampling Visualization** — timeline of detected vs missed frames
4. **Cost vs Detection Accuracy** — Arducam is the best value
5. **Playstyle Matchup Heatmap** — win rates of each AI style vs every other
6. **Rally Length Distribution** — how long rallies last across different matchups
7. **Point Win Reasons** — breakdown of aces, winners, errors, net, out

## Tests

```bash
python main.py test
# or
cd tt-referee-sim && pytest tests/ -v
```
