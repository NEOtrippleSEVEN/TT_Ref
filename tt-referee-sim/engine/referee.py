"""Referee engine — scoring decisions from camera frames only (never ground truth)."""

from typing import Optional

from engine.types import (
    BounceEvent,
    CameraFrame,
    Match,
    NetEvent,
    RefereeDecision,
    Vec3,
)
from engine import table


def detect_bounces(frames: list[CameraFrame]) -> list[BounceEvent]:
    """Detect bounces from camera frames only.

    Looks for pattern: ball descending -> near table height -> ascending.
    Requires at least 2 consecutive detected frames near the bounce.
    """
    bounces = []
    detected_frames = [f for f in frames if f.detected and f.pos_detected is not None]

    if len(detected_frames) < 3:
        return bounces

    bounce_z = table.TABLE_HEIGHT + table.BALL_RADIUS
    proximity = 0.05  # 5cm tolerance for "near table"

    for i in range(1, len(detected_frames) - 1):
        prev_f = detected_frames[i - 1]
        curr_f = detected_frames[i]
        next_f = detected_frames[i + 1]

        prev_z = prev_f.pos_detected.z
        curr_z = curr_f.pos_detected.z
        next_z = next_f.pos_detected.z

        # Descending -> near table -> ascending
        if prev_z > curr_z and next_z > curr_z:
            if abs(curr_z - bounce_z) < proximity:
                half_l = table.TABLE_LENGTH / 2
                half_w = table.TABLE_WIDTH / 2
                x = curr_f.pos_detected.x
                y = curr_f.pos_detected.y

                # Must be on the table
                if abs(x) <= half_l + 0.02 and abs(y) <= half_w + 0.02:
                    side = "left" if x < 0 else "right"
                    is_edge = (
                        abs(abs(x) - half_l) < table.EDGE_THRESHOLD
                        or abs(abs(y) - half_w) < table.EDGE_THRESHOLD
                    )

                    # Confidence based on frame density
                    dt = next_f.t - prev_f.t
                    conf = min(0.99, 0.5 + 1.0 / (dt * 60))  # more frames = more confident

                    bounces.append(BounceEvent(
                        pos=curr_f.pos_detected.copy() if curr_f.pos_detected else Vec3(),
                        t=curr_f.t,
                        side=side,
                        is_edge=is_edge,
                    ))

    return bounces


def detect_net(frames: list[CameraFrame]) -> list[NetEvent]:
    """Detect net interactions from camera frames.

    Ball trajectory interrupted at x ≈ 0, speed drops significantly.
    """
    net_events = []
    detected_frames = [f for f in frames if f.detected and f.pos_detected is not None]

    if len(detected_frames) < 3:
        return net_events

    for i in range(1, len(detected_frames) - 1):
        prev_f = detected_frames[i - 1]
        curr_f = detected_frames[i]
        next_f = detected_frames[i + 1]

        x = curr_f.pos_detected.x

        # Near the net (x ≈ 0)
        if abs(x) < 0.15:
            # Check for speed drop
            dt_prev = curr_f.t - prev_f.t
            dt_next = next_f.t - curr_f.t

            if dt_prev > 0 and dt_next > 0:
                vx_before = (curr_f.pos_detected.x - prev_f.pos_detected.x) / dt_prev
                vx_after = (next_f.pos_detected.x - curr_f.pos_detected.x) / dt_next

                # Significant speed reduction or direction change at net
                if abs(vx_after) < abs(vx_before) * 0.5 or (vx_before > 0 and vx_after < 0):
                    clipped = curr_f.pos_detected.z > table.TABLE_HEIGHT + table.NET_HEIGHT * 0.8
                    net_events.append(NetEvent(
                        pos=curr_f.pos_detected.copy() if curr_f.pos_detected else Vec3(),
                        t=curr_f.t,
                        clipped=clipped,
                    ))

    return net_events


def detect_out(frames: list[CameraFrame], last_bounce_side: Optional[str] = None) -> bool:
    """Detect if the ball went out of bounds.

    Ball leaves table area without valid bounce on opponent's side,
    or double-bounce detected on same side.
    """
    detected_frames = [f for f in frames if f.detected and f.pos_detected is not None]

    if len(detected_frames) < 2:
        return False

    # Check if last detected positions are off the table
    last_few = detected_frames[-3:] if len(detected_frames) >= 3 else detected_frames
    half_l = table.TABLE_LENGTH / 2
    half_w = table.TABLE_WIDTH / 2

    for f in last_few:
        x, y, z = f.pos_detected.x, f.pos_detected.y, f.pos_detected.z
        if (
            abs(x) > half_l + 0.1
            or abs(y) > half_w + 0.1
            or z < table.TABLE_HEIGHT - 0.1
        ):
            return True

    return False


def score_point(match: Match, side: str) -> Match:
    """Score a point. Side indicates where the ball landed/went out.

    If ball lands on 'left' side, Player 2 scores (ball passed Player 1).
    If ball lands on 'right' side, Player 1 scores (ball passed Player 2).

    ITTF rules:
    - Game to 11, must win by 2
    - Serve rotates every 2 points
    - At deuce (10-10): serve rotates every point
    """
    m = Match(
        p1_score=match.p1_score,
        p2_score=match.p2_score,
        server=match.server,
        serve_count=match.serve_count,
        history=list(match.history),
        deuce=match.deuce,
        winner=match.winner,
    )

    if m.winner is not None:
        return m  # Game already over

    if side == "left":
        m.p2_score += 1
    else:
        m.p1_score += 1

    m.history.append({
        "p1": m.p1_score,
        "p2": m.p2_score,
        "server": m.server,
        "side": side,
    })

    m.serve_count += 1
    m.deuce = m.p1_score >= 10 and m.p2_score >= 10
    interval = 1 if m.deuce else 2

    if m.serve_count >= interval:
        m.server = 2 if m.server == 1 else 1
        m.serve_count = 0

    # Check for winner
    if m.p1_score >= 11 and m.p1_score - m.p2_score >= 2:
        m.winner = 1
    if m.p2_score >= 11 and m.p2_score - m.p1_score >= 2:
        m.winner = 2

    return m


def create_match() -> Match:
    """Create a new match with default state."""
    return Match()
