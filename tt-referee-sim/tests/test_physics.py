"""Tests for the physics engine."""

import math
import pytest

from engine.types import BallState, Vec3, BounceEvent
from engine.physics import simulate
from engine import table


def test_ball_drop_bounce_height():
    """Drop ball from 0.5m above table → bounce height reduced by restitution + drag.

    With air drag on a 2.7g ball, impact velocity is lower than ideal free-fall,
    so bounce height is less than h * e^2. We verify it's in a realistic range.
    """
    drop_height = 0.5
    start_z = table.TABLE_HEIGHT + table.BALL_RADIUS + drop_height
    state = BallState(
        pos=Vec3(0, 0, start_z),
        vel=Vec3(0, 0, 0),
        spin=Vec3(0, 0, 0),
    )
    positions, events = simulate(state, dt=0.001, max_time=2.0)

    # Should have at least one bounce
    bounces = [e for e in events if isinstance(e, BounceEvent)]
    assert len(bounces) >= 1, "Ball should bounce at least once"

    # Find max height after first bounce
    bounce_t = bounces[0].t
    post_bounce = [p for p in positions if p.t > bounce_t]
    max_z_after = max(p.pos.z for p in post_bounce) if post_bounce else 0

    # Bounce height relative to table surface
    bounce_height = max_z_after - table.TABLE_HEIGHT - table.BALL_RADIUS

    # Ideal (no drag): h * e^2 = 0.396m
    # With drag on 2.7g ball, expect ~0.30-0.40m (drag reduces impact velocity)
    ideal = drop_height * table.RESTITUTION**2
    assert 0.25 < bounce_height < ideal + 0.01, (
        f"Bounce height {bounce_height:.4f}m should be between 0.25m and {ideal:.4f}m"
    )
    # Bounce height should be less than ideal due to drag
    assert bounce_height < ideal, "Drag should reduce bounce height below ideal"


def test_gravity_velocity_short():
    """Ball at rest — after 0.1s vel.z should be ≈ -0.981 (drag negligible at low speed)."""
    start_z = table.TABLE_HEIGHT + table.BALL_RADIUS + 10
    state = BallState(
        pos=Vec3(0, 0, start_z),
        vel=Vec3(0, 0, 0),
        spin=Vec3(0, 0, 0),
    )
    positions, _ = simulate(state, dt=0.001, max_time=0.1)

    final = positions[-1]
    # At low speed, drag is negligible — vel.z ≈ -g * t = -0.981
    assert final.vel.z == pytest.approx(-table.GRAVITY * 0.1, rel=0.05), (
        f"After 0.1s, vel.z={final.vel.z:.3f} should be ~-{table.GRAVITY * 0.1:.3f}"
    )


def test_terminal_velocity():
    """Ping pong ball should approach terminal velocity (~9.3 m/s) during long fall."""
    start_z = table.TABLE_HEIGHT + table.BALL_RADIUS + 50
    state = BallState(
        pos=Vec3(0, 0, start_z),
        vel=Vec3(0, 0, 0),
        spin=Vec3(0, 0, 0),
    )
    positions, _ = simulate(state, dt=0.001, max_time=3.0)

    final = positions[-1]
    # Terminal velocity: v_t = sqrt(2mg / (rho * Cd * A))
    v_terminal = math.sqrt(
        2 * table.BALL_MASS * table.GRAVITY
        / (table.AIR_DENSITY * table.DRAG_COEFFICIENT * table.BALL_AREA)
    )
    # Should be near terminal velocity (within 15%)
    assert abs(final.vel.z) == pytest.approx(v_terminal, rel=0.15), (
        f"Terminal vel {abs(final.vel.z):.2f} should be ~{v_terminal:.2f} m/s"
    )


def test_drag_slows_ball():
    """Fast ball should slow down over time due to air drag."""
    state = BallState(
        pos=Vec3(-1.0, 0, table.TABLE_HEIGHT + 0.5),
        vel=Vec3(20.0, 0, 0),
        spin=Vec3(0, 0, 0),
    )
    positions, _ = simulate(state, dt=0.001, max_time=0.5)

    initial_vx = positions[0].vel.x
    final_vx = positions[-1].vel.x

    assert final_vx < initial_vx, "Ball should slow down due to drag"
    assert final_vx > 0, "Ball should still be moving forward"


def test_bounce_side_detection():
    """Ball bouncing at x=0.5 → side='right', at x=-0.5 → side='left'."""
    # Right side bounce
    state = BallState(
        pos=Vec3(0.5, 0, table.TABLE_HEIGHT + 0.3),
        vel=Vec3(0, 0, -1.0),
        spin=Vec3(0, 0, 0),
    )
    _, events = simulate(state, dt=0.001, max_time=1.0)
    bounces = [e for e in events if isinstance(e, BounceEvent)]
    assert len(bounces) >= 1
    assert bounces[0].side == "right"

    # Left side bounce
    state = BallState(
        pos=Vec3(-0.5, 0, table.TABLE_HEIGHT + 0.3),
        vel=Vec3(0, 0, -1.0),
        spin=Vec3(0, 0, 0),
    )
    _, events = simulate(state, dt=0.001, max_time=1.0)
    bounces = [e for e in events if isinstance(e, BounceEvent)]
    assert len(bounces) >= 1
    assert bounces[0].side == "left"


def test_ball_out_of_bounds():
    """Ball launched off the table should trigger OutEvent."""
    state = BallState(
        pos=Vec3(-1.0, 0, table.TABLE_HEIGHT + 0.5),
        vel=Vec3(-10.0, 0, 1.0),  # flying away from table
        spin=Vec3(0, 0, 0),
    )
    _, events = simulate(state, dt=0.001, max_time=3.0)

    from engine.types import OutEvent
    outs = [e for e in events if isinstance(e, OutEvent)]
    assert len(outs) >= 1, "Ball should go out of bounds"


def test_simulation_terminates():
    """Simulation should terminate within max_time."""
    state = BallState(
        pos=Vec3(0, 0, table.TABLE_HEIGHT + 0.5),
        vel=Vec3(5, 0, 2),
        spin=Vec3(0, 0, 0),
    )
    positions, _ = simulate(state, dt=0.001, max_time=1.0)
    assert positions[-1].t <= 1.0 + 0.002
