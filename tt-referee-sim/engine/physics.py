"""Ball physics simulation — gravity, drag, Magnus effect, bounces, net collision.

Uses real spin values in rad/s (pro topspin: ~628 rad/s = 100 rps).
Magnus effect calibrated so heavy topspin produces ~2x gravity of downward force.
"""

import math
import random
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
    """Magnus effect: F = (4/3) * pi * r^3 * rho * Cl * (spin x velocity) * BOOST.

    With real spin values (100-900 rad/s), MAGNUS_BOOST=0.20 gives:
    - Pro topspin (628 rad/s, 21 m/s): ~20 m/s^2 downward = ~2x gravity
    - Medium rally (300 rad/s, 13 m/s): ~6 m/s^2 = ~0.6x gravity
    - Light topspin (100 rad/s, 8 m/s): ~1 m/s^2 = subtle effect
    """
    if spin.magnitude() < 1e-9:
        return vel.copy()
    cross = spin.cross(vel)
    cross_mag = cross.magnitude()
    if cross_mag < 1e-9:
        return vel.copy()
    # Force magnitude: (4/3) * pi * r^3 * rho * Cl * |omega x v| * BOOST
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

            # Spin-bounce interaction (physically correct for BOTH directions)
            # Contact point velocity = -spin.y * R (from cross product of spin × r_contact)
            # Friction force on ball = FRICTION * spin.y * R (always correct sign)
            # Topspin (+x travel, spin.y>0 OR -x travel, spin.y<0) accelerates forward
            # Backspin (opposite signs) decelerates
            spin_velocity = curr.spin.y * table.BALL_RADIUS
            curr.vel.x += table.BALL_TABLE_FRICTION * spin_velocity

            # Sidespin (spin.x) deflects laterally on bounce
            side_spin_vel = curr.spin.x * table.BALL_RADIUS
            curr.vel.y += table.BALL_TABLE_FRICTION * side_spin_vel * 0.5

            # Topspin reduces bounce height, backspin increases it
            # Topspin = spin.y and vel.x have same sign (forward spin)
            # Backspin = spin.y and vel.x have opposite signs
            if curr.spin.y * curr.vel.x > 0:
                curr.vel.z *= 0.92  # topspin: lower, faster bounce
            elif curr.spin.y * curr.vel.x < 0:
                curr.vel.z *= 1.08  # backspin: higher, slower bounce

            # General friction on bounce
            curr.vel.x *= 0.95
            curr.vel.y *= 0.95

            # Spin decays on bounce (~22% loss per research)
            curr.spin = Vec3(
                curr.spin.x * table.SPIN_DECAY_ON_BOUNCE,
                curr.spin.y * table.SPIN_DECAY_ON_BOUNCE,
                curr.spin.z * table.SPIN_DECAY_ON_BOUNCE,
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
    """Check and handle ball hitting the net.

    Two zones:
    - Net top clip (within ball radius of net top): ball may dribble over or fall back
    - Net body hit (below net top): ball stops, falls on hitter's side
    """
    events: list[NetEvent] = []
    half_w = table.TABLE_WIDTH / 2 + table.NET_OVERHANG
    net_top = table.TABLE_HEIGHT + table.NET_HEIGHT
    clip_zone_top = net_top + table.BALL_RADIUS
    clip_zone_bottom = net_top - table.BALL_RADIUS

    # Detect crossing in either direction (left->right or right->left)
    crossed = (prev.pos.x < 0 and curr.pos.x >= 0) or (prev.pos.x > 0 and curr.pos.x <= 0)
    if not crossed:
        return curr, events

    if abs(curr.pos.y) > half_w:
        return curr, events  # Ball goes around the net (legal in real TT!)

    # Ball height at net crossing
    if curr.pos.z < clip_zone_top:
        if curr.pos.z >= clip_zone_bottom:
            # NET CLIP — ball grazes the top of the net
            # Unpredictable: sometimes dribbles over, sometimes falls back
            if random.random() < 0.6:
                # Ball dribbles over the net (lucky net cord)
                curr.vel.x *= 0.10  # almost all horizontal speed lost
                curr.vel.z = random.uniform(0.1, 0.4)  # small upward pop
                curr.vel.y *= 0.3
            else:
                # Ball falls back on hitter's side
                curr.vel.x = -curr.vel.x * 0.05  # tiny reverse
                curr.vel.z = random.uniform(0.05, 0.2)
            events.append(NetEvent(pos=curr.pos.copy(), t=curr.t, clipped=True))
        else:
            # NET BODY HIT — ball hits the mesh, stops dead
            # Ball falls on hitter's side — point to opponent
            curr.vel.x = 0.0
            curr.vel.y = 0.0
            curr.vel.z = 0.05  # tiny upward so it falls naturally
            curr.pos.x = prev.pos.x  # snap back to hitter's side
            curr.alive = False  # ball is dead
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
