"""Preset shot trajectories for the simulation."""

from engine.types import BallState, Vec3
from engine import table

# All shots start from the left side of the table
_START_X = -table.TABLE_LENGTH / 2 + 0.3
_START_Z = table.TABLE_HEIGHT + 0.40  # ~40cm above table, realistic for waist-height hit

SHOT_PRESETS = {
    "slow_rally": {
        "label": "Slow Rally (~30 km/h)",
        "speed": 30,
        "vx": 8.3,
        "vy": 0.2,
        "vz": -0.5,
        "spin": (0, 5, 0),
    },
    "medium_rally": {
        "label": "Medium Rally (~50 km/h)",
        "speed": 50,
        "vx": 13.5,
        "vy": 0.3,
        "vz": -1.0,
        "spin": (0, 30, 0),  # topspin around y-axis dips the ball
    },
    "fast_topspin": {
        "label": "Fast Topspin (~80 km/h)",
        "speed": 80,
        "vx": 21,
        "vy": 0.4,
        "vz": -1.5,
        "spin": (0, 55, 0),  # heavy topspin — strong downward dip
    },
    "smash": {
        "label": "Smash (~100 km/h)",
        "speed": 100,
        "vx": 27,
        "vy": 0.2,
        "vz": -3.5,
        "spin": (0, 20, 0),
    },
    "net_clip": {
        "label": "Net Clip",
        "speed": 35,
        "vx": 9.5,
        "vy": 0.1,
        "vz": -0.7,
        "spin": (0, 5, 0),  # barely clears net
    },
    "edge_hit": {
        "label": "Edge Hit",
        "speed": 45,
        "vx": 12,
        "vy": 2.0,
        "vz": -0.8,
        "spin": (15, 10, 0),  # sidespin + topspin
    },
    "backspin_chop": {
        "label": "Backspin Chop",
        "speed": 36,
        "vx": 10,
        "vy": 0.2,
        "vz": -0.8,
        "spin": (0, -10, 0),  # backspin lifts slightly, floats longer
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
