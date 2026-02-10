"""Tests for the AI player engine."""

import random
import pytest

from engine.ai_player import AIPlayer, PLAYSTYLES
from engine.types import BallState, BounceEvent, Vec3
from engine import table


def test_all_playstyles_exist():
    """All documented playstyles should be available."""
    expected = ["aggressive", "defensive", "allround", "beginner", "pro"]
    for key in expected:
        assert key in PLAYSTYLES, f"Missing playstyle: {key}"


def test_player_creation():
    """Players should initialize with correct attributes."""
    p = AIPlayer("Test", "aggressive", 1)
    assert p.name == "Test"
    assert p.side == 1
    assert p.playstyle == "aggressive"
    assert 0 < p.power <= 1.0
    assert 0 < p.consistency <= 1.0


def test_generate_serve_left_side():
    """Player 1 (left side) serve should go toward the right."""
    random.seed(42)
    p = AIPlayer("P1", "allround", 1)
    state = p.generate_serve()
    assert isinstance(state, BallState)
    assert state.vel.x > 0, "Left side player serve should go right (vx > 0)"
    assert state.pos.x < 0, "Should start on left side"
    assert state.pos.z > table.TABLE_HEIGHT, "Should start above table"


def test_generate_serve_right_side():
    """Player 2 (right side) serve should go toward the left."""
    random.seed(42)
    p = AIPlayer("P2", "allround", 2)
    state = p.generate_serve()
    assert isinstance(state, BallState)
    assert state.vel.x < 0, "Right side player serve should go left (vx < 0)"
    assert state.pos.x > 0, "Should start on right side"


def test_calculate_return():
    """Return shot should go toward the opposite side."""
    random.seed(42)
    p = AIPlayer("P1", "allround", 1)
    bounce = BounceEvent(
        pos=Vec3(-0.5, 0, table.TABLE_HEIGHT + table.BALL_RADIUS),
        t=0.5,
        side="left",
    )
    ret = p.calculate_return(bounce)
    assert isinstance(ret, BallState)
    assert ret.vel.x > 0, "P1 return should go toward right side"


def test_can_reach_probability():
    """Pro player should reach more balls than beginner over many trials."""
    random.seed(42)
    pro = AIPlayer("Pro", "pro", 1)
    beginner = AIPlayer("Noob", "beginner", 1)

    ball_pos = Vec3(-0.5, 0, table.TABLE_HEIGHT + 0.1)
    ball_vel = Vec3(15, 0, -2)

    pro_reach = sum(pro.can_reach(ball_pos, ball_vel) for _ in range(200))
    beginner_reach = sum(beginner.can_reach(ball_pos, ball_vel) for _ in range(200))

    assert pro_reach > beginner_reach, (
        f"Pro ({pro_reach}/200) should reach more than beginner ({beginner_reach}/200)"
    )


def test_serve_lands_on_table():
    """Serves from various playstyles should mostly produce valid trajectories."""
    from engine.physics import simulate

    random.seed(123)
    valid_count = 0
    total = 30

    for _ in range(total):
        style = random.choice(list(PLAYSTYLES.keys()))
        side = random.choice([1, 2])
        p = AIPlayer("Test", style, side)
        state = p.generate_serve()
        positions, events = simulate(state, max_time=3.0)

        from engine.types import BounceEvent as BE
        bounces = [e for e in events if isinstance(e, BE)]
        if bounces:
            valid_count += 1

    # At least 50% of serves should produce bounces
    assert valid_count >= total * 0.5, (
        f"Only {valid_count}/{total} serves produced bounces"
    )
