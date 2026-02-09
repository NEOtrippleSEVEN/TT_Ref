# TT Referee Simulation — Python

## What This Is
AI-powered table tennis referee simulation that proves why specific camera
hardware (Arducam OV9281, 200fps global shutter) is needed for real-time
ball tracking. Built for a university FabLab hardware funding pitch.

The simulation has three decoupled engines:
1. Physics Engine — ground truth ball trajectory (gravity, spin, bounce)
2. Camera Engine — simulates what hardware captures at different fps/resolution
3. Referee Engine — makes scoring decisions using ONLY camera data

The gap between ground truth and referee accuracy IS the hardware justification.

## Tech Stack
- Python 3.11+
- Pygame for real-time visualization
- Matplotlib for analysis charts and report generation
- NumPy for physics math
- Streamlit for optional web dashboard
- Pytest for testing

## Project Structure

tt-referee-sim/
├── CLAUDE.md
├── engine/
│   ├── init.py
│   ├── types.py          # Dataclasses: Vec3, BallState, BounceEvent, CameraFrame
│   ├── physics.py        # Ball trajectory — gravity, drag, Magnus effect, bounce
│   ├── table.py          # Official table dimensions, collision zones, net geometry
│   ├── camera.py         # Virtual camera: sampling, motion blur, detection probability
│   ├── referee.py        # Scoring from camera frames only — bounce/net/out detection
│   └── trajectories.py   # Shot presets: serve, rally, topspin, smash, net clip, edge
├── sim/
│   ├── init.py
│   ├── visualizer.py     # Pygame: top-down + side view, animated ball, camera overlay
│   ├── analysis.py       # Matplotlib: fps comparison charts, detection heatmaps
│   └── report.py         # Generate PDF/PNG report for FabLab presentation
├── app.py                # Streamlit dashboard (optional, build last)
├── main.py               # CLI entry point — run sim, play animation, export report
├── tests/
│   ├── test_physics.py   # Drop ball → verify bounce height, drag slows ball
│   ├── test_camera.py    # Frame count = duration × fps, detection drops at high speed
│   ├── test_referee.py   # 11 points, 2-pt deuce, serve rotation every 2 points
│   └── test_trajectories.py
├── requirements.txt
└── README.md

## Build Order (follow strictly)

### Step 1: Engine Core
Build engine/types.py, engine/table.py, engine/physics.py

types.py dataclasses:
- Vec3(x, y, z) — use for position, velocity, spin
- BallState(pos, vel, spin, alive, t)
- BounceEvent(pos, t, side: "left"|"right", is_edge: bool)
- NetEvent(pos, t, clipped: bool)
- CameraFrame(frame_num, t, pos_detected: Vec3|None, confidence, blur_px)
- RefereeDecision(type, side, confidence, frames_used)

table.py constants:
- TABLE_LENGTH = 2.74m, TABLE_WIDTH = 1.525m, TABLE_HEIGHT = 0.76m
- NET_HEIGHT = 0.1525m, NET_OVERHANG = 0.1525m
- BALL_RADIUS = 0.02m, BALL_MASS = 0.0027kg
- RESTITUTION = 0.89, DRAG_COEFFICIENT = 0.4
- GRAVITY = 9.81

physics.py:
- simulate(initial_state, dt=0.001, max_time=3.0) → list[BallState], list[Event]
- Internal timestep 1ms (1000Hz). This is ground truth.
- Gravity: vel.z -= GRAVITY * dt
- Air drag: F_drag = 0.5 * rho * Cd * A * v² (rho=1.225, A=pi*r²)
- Magnus effect: F_magnus = Cl * (spin × velocity), Cl ≈ 0.5 for table tennis
  - Topspin → ball dips faster, bounces lower and faster
  - Backspin → ball floats longer, bounces higher and slower
  - Sidespin → ball curves laterally
- Table bounce: when ball.z crosses TABLE_HEIGHT + BALL_RADIUS
  - vel.z *= -RESTITUTION
  - Spin modifies bounce: topspin adds forward speed, backspin reduces it
  - Record BounceEvent with side (left if x < 0, right if x > 0)
  - Edge detection: within 3cm of table edge
- Net collision: when ball.x crosses 0 and z < TABLE_HEIGHT + NET_HEIGHT
  - If ball clears net top: reduce vel.x to 30%, add slight upward vel
  - If ball hits net body: reflect, heavy speed loss
- Out of bounds: ball hits floor (z < 0) outside table, or travels >1.5m past table

Run tests after: drop a ball from 0.5m → should bounce to ~0.445m (0.89²).

### Step 2: Trajectories
Build engine/trajectories.py

Preset shots (all start from left side, x = -1.07, z = TABLE_HEIGHT + 0.15):
- slow_rally:    vx=8.3,  vy=0.2, vz=1.2,  spin=(0,0,0)     ~30 km/h
- medium_rally:  vx=13.5, vy=0.3, vz=1.8,  spin=(20,0,0)    ~50 km/h topspin
- fast_topspin:  vx=21,   vy=0.5, vz=2.5,  spin=(50,0,0)    ~80 km/h heavy topspin
- smash:         vx=27,   vy=0.3, vz=1.5,  spin=(10,0,0)    ~100 km/h
- net_clip:      vx=9.5,  vy=0.1, vz=0.45, spin=(5,0,0)     just clears net
- edge_hit:      vx=12,   vy=3.8, vz=1.0,  spin=(0,10,0)    hits edge with sidespin
- backspin_chop: vx=10,   vy=0.2, vz=2.0,  spin=(-30,0,0)   defensive chop

Each preset returns a BallState ready for physics.simulate().

### Step 3: Camera Engine
Build engine/camera.py

CAMERA_PRESETS:
- cheap:   fps=60,  resolution=(640,480),   shutter=1/500,  global_shutter=False, cost=25
- mid:     fps=120, resolution=(1280,720),  shutter=1/1000, global_shutter=False, cost=45
- arducam: fps=200, resolution=(1280,800),  shutter=1/2000, global_shutter=True,  cost=75

simulate_camera(positions, fps, shutter_speed, resolution, global_shutter) → list[CameraFrame]:
- Sample position list at intervals of 1/fps
- Calculate ball size in pixels: ball_px = BALL_RADIUS * 2 * (resolution[0] / (TABLE_LENGTH + 1))
- Motion blur: blur_px = ball_speed_in_pixels * exposure_time
  - Rolling shutter: exposure_time = 1/shutter_speed
  - Global shutter: exposure_time = 1/shutter_speed * 0.1 (10x less blur)
- Detection probability model:
  - If effective_ball_size < 2px: confidence = 0.10
  - If effective_ball_size < 4px: confidence = 0.40
  - If blur > 3× ball_size: confidence = 0.20
  - If blur > 1.5× ball_size: confidence = 0.60
  - Otherwise: confidence = min(0.99, 0.70 + ball_size/50)
- Frame detected if random() < confidence

compare_cameras(positions, events) → dict:
- Run all three presets on same trajectory
- Return detection_rate, avg_confidence, avg_blur, bounces_detected per camera

### Step 4: Referee Engine
Build engine/referee.py

CRITICAL: Referee receives ONLY CameraFrame list. Never ground truth.

detect_bounces(frames) → list[BounceEvent]:
- Look for pattern: ball descending → ball near table height → ball ascending
- Requires at least 2 consecutive detected frames near bounce
- Confidence based on frame density around event

detect_net(frames) → list[NetEvent]:
- Ball trajectory interrupted at x ≈ 0
- Speed drops significantly between consecutive frames

detect_out(frames, last_bounce_side) → bool:
- Ball leaves table area without valid bounce on opponent's side
- Or double-bounce detected on same side

Scoring (ITTF rules):
- Match(p1_score, p2_score, server, serve_count, history, deuce, winner)
- Game to 11, must win by 2
- Serve rotates every 2 points
- At deuce (10-10): serve rotates every 1 point
- score_point(match, side) → new Match

### Step 5: Pygame Visualizer
Build sim/visualizer.py

Window: 1200×700

Layout:
- Left 70%: Table view (toggle top-down / side with T key)
- Right 30%: Live stats panel (dark background)

Top-down view:
- Green table with white lines, center line dashed
- Gray net line
- Ball as orange/white circle with glow effect
- Trail: fading red line showing path
- Camera frame markers: green dots (detected) / red dots (missed)
- Bounce markers: "BOUNCE" / "NET" / "EDGE" / "OUT" text labels

Side view:
- Table as horizontal line at correct height
- Net as vertical line
- Ball trajectory showing arc
- Same markers

Stats panel (right side):
- Current shot name and speed
- Selected camera preset
- Detection rate (color coded: green >85%, yellow >60%, red <60%)
- Bounces detected / total
- Average confidence
- Score (P1 vs P2)
- Server indicator

Controls:
- SPACE: play/pause animation
- R: reset, new random trajectory
- 1/2/3: switch camera preset (cheap/mid/arducam)
- T: toggle top/side view
- S: score point from current trajectory
- N: next shot preset
- Q: quit
- A: run analysis (generate comparison chart)

Animation: play trajectory at 0.3x speed so it's visible.

### Step 6: Analysis & Report
Build sim/analysis.py and sim/report.py

analysis.py generates matplotlib charts:

Chart 1: "Detection Rate vs Ball Speed"
- X axis: ball speed (30, 50, 80, 100 km/h)
- Y axis: detection rate %
- Three lines: 60fps, 120fps, 200fps
- Arducam line should be clearly superior at high speeds

Chart 2: "Ball Distance Between Frames"
- Grouped bar chart: each speed × each fps
- Shows cm traveled between frames
- Reference line at 4cm (ball diameter) — below this = good tracking

Chart 3: "Frame Sampling Visualization"
- For one trajectory, show timeline with frame positions
- Three rows: 60fps (sparse dots), 120fps (medium), 200fps (dense)
- Color: green=detected, red=missed

Chart 4: "Cost vs Accuracy"
- Scatter: x=cost, y=detection rate at 80km/h
- Annotate each point with camera name
- Shows Arducam is best value

report.py:
- Combine all charts into single figure or multi-page PDF
- Add title: "AI Table Tennis Referee — Hardware Justification"
- Add summary text with key findings
- Save as tt_referee_report.pdf and tt_referee_report.png

### Step 7: CLI Entry Point
Build main.py
python main.py play              # Launch Pygame visualizer
python main.py analyze           # Generate comparison charts
python main.py report            # Generate PDF report
python main.py test              # Run all tests
python main.py demo              # Full demo: play each shot, show stats, generate report


### Step 8: Streamlit Dashboard (optional, only if time permits)
Build app.py

- Shot selector dropdown
- Camera selector
- Animated canvas (using st.empty + matplotlib animation frames)
- Live stats
- Score tracking
- Download report button

## Important Implementation Notes

1. Engine modules MUST be pure Python — no Pygame, no Streamlit imports.
   They take data in, return data out. This is critical because later
   the camera engine will be swapped for real OpenCV frames.

2. All physics values are in SI units (meters, seconds, kg).
   Convert to pixels only in the visualizer.

3. The detection probability model doesn't need to be perfect — it needs
   to show a CLEAR difference between 60fps and 200fps. The trend matters
   more than exact numbers.

4. Run tests after each step. Don't proceed if tests fail.

5. The Pygame visualizer should work standalone — someone should be able to
   run `python main.py play` and immediately see a ball bouncing on a table
   with camera detection overlay.

## Testing Requirements

test_physics.py:
- Ball drop: 0.5m drop → bounce height ≈ 0.5 * 0.89² = 0.396m (±5%)
- Gravity: ball at rest, after 1s vel.z should be ≈ -9.81
- Drag: fast ball should slow down over time
- Bounce side detection: ball bouncing at x=0.5 → side="right"

test_camera.py:
- Frame count: 1 second at 60fps → 60 frames
- Higher fps → higher detection rate on same trajectory
- Global shutter → less motion blur than rolling shutter

test_referee.py:
- Score 11-0 → winner declared
- Score 10-10 → deuce mode, serve every point
- Score 12-10 → winner (2 point lead)
- Score 11-10 → no winner yet
- Serve rotation: every 2 points normally, every 1 at deuce
