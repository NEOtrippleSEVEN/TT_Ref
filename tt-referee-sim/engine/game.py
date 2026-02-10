"""Game simulation — full rallies and matches with AI players."""

import random
from dataclasses import dataclass, field
from typing import Optional

from engine.types import BallState, BounceEvent, NetEvent, OutEvent, Vec3, Match
from engine.physics import simulate
from engine.referee import score_point, create_match
from engine.ai_player import AIPlayer
from engine import table


@dataclass
class RallyShot:
    """One shot within a rally (serve or return)."""
    player: int  # 1 or 2
    ball_state: BallState
    positions: list  # list[BallState]
    events: list     # list of events
    shot_type: str   # "serve" or "return"


@dataclass
class RallyResult:
    """The outcome of a full rally (serve + returns until point)."""
    shots: list           # list[RallyShot]
    winner: int           # 1 or 2
    reason: str           # "ace", "winner", "unforced_error", "net", "out", "unreturned"
    total_duration: float
    rally_length: int     # number of shots


@dataclass
class GameResult:
    """Full game result with all rallies."""
    match: Match
    rallies: list         # list[RallyResult]
    p1: AIPlayer
    p2: AIPlayer
    stats: dict = field(default_factory=dict)


def _find_landing_bounce(events: list, target_side: str) -> Optional[BounceEvent]:
    """Find the first bounce on the target side."""
    for e in events:
        if isinstance(e, BounceEvent) and e.side == target_side:
            return e
    return None


def _ball_hit_net(events: list) -> bool:
    """Check if ball hit the net without clearing."""
    for e in events:
        if isinstance(e, NetEvent) and not e.clipped:
            return True
    return False


def _ball_went_out(events: list, positions: list) -> bool:
    """Check if ball went out without landing on table."""
    has_out = any(isinstance(e, OutEvent) for e in events)
    return has_out


def simulate_rally(
    p1: AIPlayer,
    p2: AIPlayer,
    server: int,
) -> RallyResult:
    """Simulate a full rally from serve to point.

    Args:
        p1: Player 1 (left side).
        p2: Player 2 (right side).
        server: 1 or 2, who serves.

    Returns:
        RallyResult with all shots and outcome.
    """
    serving_player = p1 if server == 1 else p2
    receiving_player = p2 if server == 1 else p1

    shots: list[RallyShot] = []
    current_hitter = serving_player
    current_receiver = receiving_player

    # Serve
    serve_state = current_hitter.generate_serve()
    positions, events = simulate(serve_state, max_time=3.0)

    shots.append(RallyShot(
        player=current_hitter.side,
        ball_state=serve_state,
        positions=positions,
        events=events,
        shot_type="serve",
    ))

    # Check serve outcome
    if _ball_hit_net(events):
        # Let serve — reserve (simplified: just fault, point to receiver)
        return RallyResult(
            shots=shots,
            winner=current_receiver.side,
            reason="net",
            total_duration=positions[-1].t,
            rally_length=1,
        )

    # Check if serve bounced on server's side first (required for valid serve)
    server_side = "left" if current_hitter.side == 1 else "right"
    receiver_side = "right" if current_hitter.side == 1 else "left"

    bounces = [e for e in events if isinstance(e, BounceEvent)]
    receiver_bounces = [b for b in bounces if b.side == receiver_side]

    if not receiver_bounces:
        # Serve didn't reach receiver's side — fault
        return RallyResult(
            shots=shots,
            winner=current_receiver.side,
            reason="out",
            total_duration=positions[-1].t,
            rally_length=1,
        )

    # Rally loop
    max_rally = 50  # safety limit
    total_t = positions[-1].t

    for rally_num in range(max_rally):
        # Find where ball lands on receiver's side
        recv_side_str = "left" if current_receiver.side == 1 else "right"
        landing = _find_landing_bounce(events, recv_side_str)

        if not landing:
            # Ball didn't land on receiver's side
            if _ball_went_out(events, positions):
                # Ball went out — point to receiver of the shot
                return RallyResult(
                    shots=shots,
                    winner=current_receiver.side,
                    reason="out",
                    total_duration=total_t,
                    rally_length=len(shots),
                )
            else:
                # Unreturnable winner
                return RallyResult(
                    shots=shots,
                    winner=current_hitter.side,
                    reason="winner",
                    total_duration=total_t,
                    rally_length=len(shots),
                )

        # Can the receiver reach it?
        ball_vel = Vec3(0, 0, 0)
        # Estimate velocity at bounce
        for i, p in enumerate(positions):
            if p.t >= landing.t:
                ball_vel = p.vel.copy()
                break

        if not current_receiver.can_reach(landing.pos, ball_vel):
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="unreturned",
                total_duration=total_t,
                rally_length=len(shots),
            )

        # Generate return
        return_state = current_receiver.calculate_return(landing)
        positions, events = simulate(return_state, max_time=3.0)

        shots.append(RallyShot(
            player=current_receiver.side,
            ball_state=return_state,
            positions=positions,
            events=events,
            shot_type="return",
        ))

        total_t += positions[-1].t

        # Check if return hit the net
        if _ball_hit_net(events):
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="net",
                total_duration=total_t,
                rally_length=len(shots),
            )

        # Swap roles
        current_hitter, current_receiver = current_receiver, current_hitter

    # Rally too long — random winner
    return RallyResult(
        shots=shots,
        winner=random.choice([1, 2]),
        reason="timeout",
        total_duration=total_t,
        rally_length=len(shots),
    )


def simulate_game(
    p1: AIPlayer,
    p2: AIPlayer,
) -> GameResult:
    """Simulate a full game to 11 points (win by 2).

    Returns GameResult with all rallies and final score.
    """
    match = create_match()
    rallies: list[RallyResult] = []

    while match.winner is None:
        rally = simulate_rally(p1, p2, server=match.server)
        rallies.append(rally)

        # Score the point
        # Winner of the rally gets the point
        if rally.winner == 1:
            match = score_point(match, "right")  # P1 won → scored on right
        else:
            match = score_point(match, "left")   # P2 won → scored on left

    # Compute stats
    stats = _compute_game_stats(rallies, p1, p2)

    return GameResult(
        match=match,
        rallies=rallies,
        p1=p1,
        p2=p2,
        stats=stats,
    )


def _compute_game_stats(rallies: list[RallyResult], p1: AIPlayer, p2: AIPlayer) -> dict:
    """Compute game statistics."""
    p1_points = sum(1 for r in rallies if r.winner == 1)
    p2_points = sum(1 for r in rallies if r.winner == 2)

    rally_lengths = [r.rally_length for r in rallies]
    avg_rally = sum(rally_lengths) / max(len(rally_lengths), 1)
    max_rally = max(rally_lengths) if rally_lengths else 0

    reasons = {}
    for r in rallies:
        reasons[r.reason] = reasons.get(r.reason, 0) + 1

    p1_winners = sum(1 for r in rallies if r.winner == 1 and r.reason == "winner")
    p2_winners = sum(1 for r in rallies if r.winner == 2 and r.reason == "winner")
    p1_errors = sum(1 for r in rallies if r.winner == 2 and r.reason in ("net", "out"))
    p2_errors = sum(1 for r in rallies if r.winner == 1 and r.reason in ("net", "out"))

    total_duration = sum(r.total_duration for r in rallies)

    return {
        "p1_points": p1_points,
        "p2_points": p2_points,
        "total_rallies": len(rallies),
        "avg_rally_length": round(avg_rally, 1),
        "max_rally_length": max_rally,
        "reasons": reasons,
        "p1_winners": p1_winners,
        "p2_winners": p2_winners,
        "p1_unforced_errors": p1_errors,
        "p2_unforced_errors": p2_errors,
        "total_duration": round(total_duration, 2),
        "p1_name": p1.name,
        "p2_name": p2.name,
        "p1_style": p1.label,
        "p2_style": p2.label,
    }
