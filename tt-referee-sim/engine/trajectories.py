"""Preset shot trajectories for the simulation.

All spin values are in rad/s (real professional values):
  - Beginner topspin:  ~188 rad/s (30 rps / 1800 RPM)
  - Intermediate loop: ~377 rad/s (60 rps / 3600 RPM)
  - Pro topspin loop:  ~628 rad/s (100 rps / 6000 RPM)
  - Elite (Ma Long):   ~880 rad/s (140 rps / 8400 RPM)
  - Backspin chop:     ~377 rad/s (60 rps / 3600 RPM)
  - Serve spin:        ~195 rad/s (31 rps / 1860 RPM)
"""

from engine.types import BallState, Vec3
from engine import table

# All shots start from the left side of the table
_START_X = -table.TABLE_LENGTH / 2 + 0.3
_START_Z = table.TABLE_HEIGHT + 0.40  # ~40cm above table, realistic for waist-height hit

SHOT_PRESETS = {
    "slow_rally": {
        "label": "Slow Push (~30 km/h)",
        "speed": 30,
        "vx": 8.3,
        "vy": 0.2,
        "vz": -0.5,
        "spin": (0, 100, 0),  # light topspin ~16 rps
    },
    "medium_rally": {
        "label": "Medium Topspin Rally (~50 km/h)",
        "speed": 50,
        "vx": 13.5,
        "vy": 0.3,
        "vz": -0.8,
        "spin": (0, 300, 0),  # intermediate topspin ~48 rps
    },
    "fast_topspin": {
        "label": "Fast Topspin Loop (~80 km/h)",
        "speed": 80,
        "vx": 21,
        "vy": 0.4,
        "vz": -2.0,
        "spin": (0, 600, 0),  # pro-level topspin ~96 rps — Magnus adds ~2x gravity dip
    },
    "smash": {
        "label": "Smash (~100 km/h)",
        "speed": 100,
        "vx": 27,
        "vy": 0.2,
        "vz": -3.5,
        "spin": (0, 100, 0),  # flat hit, minimal spin
    },
    "net_clip": {
        "label": "Net Clip",
        "speed": 35,
        "vx": 9.5,
        "vy": 0.1,
        "vz": -0.7,
        "spin": (0, 80, 0),  # barely clears net
    },
    "edge_hit": {
        "label": "Edge Hit (sidespin)",
        "speed": 45,
        "vx": 12,
        "vy": 2.0,
        "vz": -0.8,
        "spin": (200, 150, 0),  # heavy sidespin + topspin
    },
    "backspin_chop": {
        "label": "Backspin Chop",
        "speed": 36,
        "vx": 8,
        "vy": 0.2,
        "vz": -0.8,
        "spin": (0, -350, 0),  # heavy backspin ~56 rps — backspin LIFTS ball, so flat trajectory
    },
}


def get_shot(key: str) -> BallState:
    """Return a BallState ready for physics.simulate() from a preset key."""
    preset = SHOT_PRESETS[key]
    return BallState(
        pos=Vec3(_START_X, 0, _START_Z),
        vel=Vec3(preset["vx"], preset["vy"], preset["vz"]),
        spin=Vec3(*preset["spin"]),
    )


def list_shots() -> list[str]:
    """Return all available shot preset keys."""
    return list(SHOT_PRESETS.keys())
