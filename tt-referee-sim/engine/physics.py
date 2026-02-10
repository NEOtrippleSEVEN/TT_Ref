"""Ball physics simulation — gravity, drag, Magnus effect, bounces, net collision."""

import math
from typing import Union

from engine.types import BallState, BounceEvent, NetEvent, OutEvent, Vec3
from engine import table


def _apply_gravity(vel: Vec3, dt: float) -> Vec3:
    return Vec3(vel.x, vel.y, vel.z - table.GRAVITY * dt)


def _apply_drag(vel: Vec3, dt: float) -> Vec3:
    speed = vel.magnitude()
    if speed < 1e-9:
        return vel.copy()
    drag_force = 0.5 * table.AIR_DENSITY * table.DRAG_COEFFICIENT * table.BALL_AREA * speed**2
    drag_accel = drag_force / table.BALL_MASS
    factor = drag_accel * dt / speed
    # Clamp so drag never reverses direction
    factor = min(factor, 0.99)
    return Vec3(
        vel.x - vel.x * factor,
        vel.y - vel.y * factor,
        vel.z - vel.z * factor,
    )


def _apply_magnus(vel: Vec3, spin: Vec3, dt: float) -> Vec3:
    """Magnus effect: F = (4/3) * pi * r^3 * rho * Cl * (spin x velocity).

    Uses physically correct formula scaled by ball volume and air density,
    which keeps forces realistic for a 40mm, 2.7g ping pong ball.
    """
    if spin.magnitude() < 1e-9:
        return vel.copy()
    cross = spin.cross(vel)
    cross_mag = cross.magnitude()
    if cross_mag < 1e-9:
        return vel.copy()
    # Force magnitude: (4/3) * pi * r^3 * rho * Cl * |omega x v|
    volume_factor = (4.0 / 3.0) * math.pi * table.BALL_RADIUS**3
    force = volume_factor * table.AIR_DENSITY * table.MAGNUS_CL * cross_mag * table.MAGNUS_BOOST
    accel = force / table.BALL_MASS
    return Vec3(
        vel.x + (cross.x / cross_mag) * accel * dt,
        vel.y + (cross.y / cross_mag) * accel * dt,
        vel.z + (cross.z / cross_mag) * accel * dt,
    )


def _check_table_bounce(
    prev: BallState, curr: BallState
) -> tuple[BallState, list[BounceEvent]]:
    """Check and handle ball bouncing on the table surface."""
    events: list[BounceEvent] = []
    bounce_z = table.TABLE_HEIGHT + table.BALL_RADIUS
    half_l = table.TABLE_LENGTH / 2
    half_w = table.TABLE_WIDTH / 2

    if prev.pos.z > bounce_z and curr.pos.z <= bounce_z:
        if abs(curr.pos.x) <= half_l and abs(curr.pos.y) <= half_w:
            curr.pos.z = bounce_z
            curr.vel.z = -curr.vel.z * table.RESTITUTION

            # Spin modifies bounce
            # Topspin (positive spin.x) adds forward speed
            spin_effect = curr.spin.x * 0.002
            curr.vel.x += spin_effect
            # Backspin reduces forward speed
            # (handled by negative spin.x)

            # Friction on bounce
            curr.vel.x *= 0.95
            curr.vel.y *= 0.95

            # Reduce spin on bounce
            curr.spin = Vec3(
                curr.spin.x * 0.7,
                curr.spin.y * 0.7,
                curr.spin.z * 0.7,
            )

            side = "left" if curr.pos.x < 0 else "right"
            is_edge = (
                abs(abs(curr.pos.x) - half_l) < table.EDGE_THRESHOLD
                or abs(abs(curr.pos.y) - half_w) < table.EDGE_THRESHOLD
            )
            events.append(BounceEvent(pos=curr.pos.copy(), t=curr.t, side=side, is_edge=is_edge))

    return curr, events


def _check_net_collision(
    prev: BallState, curr: BallState
) -> tuple[BallState, list[NetEvent]]:
    """Check and handle ball hitting the net."""
    events: list[NetEvent] = []
    half_w = table.TABLE_WIDTH / 2 + table.NET_OVERHANG
    net_top = table.TABLE_HEIGHT + table.NET_HEIGHT + table.BALL_RADIUS

    # Detect crossing in either direction (left→right or right→left)
    crossed = (prev.pos.x < 0 and curr.pos.x >= 0) or (prev.pos.x > 0 and curr.pos.x <= 0)
    if not crossed:
        return curr, events

    if abs(curr.pos.y) <= half_w:
        if table.TABLE_HEIGHT + table.BALL_RADIUS <= curr.pos.z < net_top:
            # Ball clips top of net
            curr.vel.x *= 0.3
            curr.vel.z = abs(curr.vel.z) * 0.4
            events.append(NetEvent(pos=curr.pos.copy(), t=curr.t, clipped=True))
        elif curr.pos.z < table.TABLE_HEIGHT + table.BALL_RADIUS:
            # Ball hits net body — reflect with heavy loss
            curr.vel.x = -curr.vel.x * 0.15
            curr.vel.z = abs(curr.vel.z) * 0.2
            events.append(NetEvent(pos=curr.pos.copy(), t=curr.t, clipped=False))

    return curr, events


def _check_out_of_bounds(
    curr: BallState,
) -> tuple[BallState, list[OutEvent]]:
    """Check if ball is out of play."""
    events: list[OutEvent] = []
    half_l = table.TABLE_LENGTH / 2
    half_w = table.TABLE_WIDTH / 2

    # Ball hits the floor outside the table
    if curr.pos.z < table.BALL_RADIUS:
        on_table = abs(curr.pos.x) <= half_l and abs(curr.pos.y) <= half_w
        if not on_table:
            events.append(OutEvent(pos=curr.pos.copy(), t=curr.t))
            curr.alive = False
        else:
            # Ball on table surface but below expected — snap up
            curr.pos.z = table.BALL_RADIUS
            curr.vel.z = -curr.vel.z * 0.5

    # Way off the table
    if (
        abs(curr.pos.x) > half_l + table.OUT_OF_BOUNDS_MARGIN
        or abs(curr.pos.y) > half_w + table.OUT_OF_BOUNDS_MARGIN
    ):
        events.append(OutEvent(pos=curr.pos.copy(), t=curr.t))
        curr.alive = False

    return curr, events


def simulate(
    initial_state: BallState,
    dt: float = 0.001,
    max_time: float = 5.0,
) -> tuple[list[BallState], list[Union[BounceEvent, NetEvent, OutEvent]]]:
    """Run full physics simulation from initial state.

    Returns (positions, events) where positions is sampled at every timestep
    and events contains bounces, net hits, and out-of-bounds.
    """
    state = initial_state.copy()
    positions = [state.copy()]
    all_events: list[Union[BounceEvent, NetEvent, OutEvent]] = []
    max_bounces = 10

    bounce_count = 0
    steps = int(max_time / dt)

    for _ in range(steps):
        if not state.alive:
            break

        prev = state.copy()

        # Physics integration
        state.vel = _apply_gravity(state.vel, dt)
        state.vel = _apply_drag(state.vel, dt)
        state.vel = _apply_magnus(state.vel, state.spin, dt)

        # Update position
        state.pos.x += state.vel.x * dt
        state.pos.y += state.vel.y * dt
        state.pos.z += state.vel.z * dt
        state.t += dt

        # Collision detection
        state, bounce_events = _check_table_bounce(prev, state)
        all_events.extend(bounce_events)
        bounce_count += len(bounce_events)

        state, net_events = _check_net_collision(prev, state)
        all_events.extend(net_events)

        state, out_events = _check_out_of_bounds(state)
        all_events.extend(out_events)

        positions.append(state.copy())

        if bounce_count > max_bounces:
            state.alive = False

    return positions, all_events
