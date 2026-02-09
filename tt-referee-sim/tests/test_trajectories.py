"""Tests for shot trajectory presets."""

import pytest

from engine.types import BallState, BounceEvent, Vec3
from engine.trajectories import get_shot, list_shots, SHOT_PRESETS
from engine.physics import simulate
from engine import table


def test_all_presets_exist():
    """All documented presets should be available."""
    expected = [
        "slow_rally", "medium_rally", "fast_topspin", "smash",
        "net_clip", "edge_hit", "backspin_chop",
    ]
    available = list_shots()
    for key in expected:
        assert key in available, f"Missing preset: {key}"


def test_get_shot_returns_ball_state():
    """get_shot should return a valid BallState."""
    for key in list_shots():
        state = get_shot(key)
        assert isinstance(state, BallState)
        assert state.alive is True
        assert state.t == 0.0
        assert state.vel.x > 0  # All shots go from left to right


def test_all_shots_simulate():
    """Every preset should run through physics without crashing."""
    for key in list_shots():
        state = get_shot(key)
        positions, events = simulate(state)
        assert len(positions) > 10, f"Shot {key} produced too few positions"


def test_shots_start_from_left_side():
    """All shots should start from the left side of the table."""
    for key in list_shots():
        state = get_shot(key)
        assert state.pos.x < 0, f"Shot {key} should start on left side (x < 0)"


def test_fast_shots_reach_right_side():
    """Fast shots (rally, topspin, smash) should reach the right side."""
    fast_shots = ["medium_rally", "fast_topspin", "smash"]
    for key in fast_shots:
        state = get_shot(key)
        positions, _ = simulate(state)
        max_x = max(p.pos.x for p in positions)
        assert max_x > 0, f"Shot {key} should reach the right side (max_x={max_x:.2f})"
