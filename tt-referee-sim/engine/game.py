"""Game simulation — full rallies and matches with AI players.

Implements ITTF rules including:
- Serve must bounce on server's side first, then receiver's side
- Let serve: ball clips net on serve but lands legally → replay
- Direct net hit: ball stops, point to opponent
- Double bounce: ball bounces twice on same side → point to opponent
- Ball not returned / missed → point to hitter
- Serve rotation: every 2 points, every 1 at deuce
- Game to 11, win by 2
"""

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
    reason: str           # see VALID_REASONS below
    total_duration: float
    rally_length: int     # number of shots


VALID_REASONS = [
    "ace",              # serve not returned
    "winner",           # shot not reached by opponent
    "unreturned",       # opponent couldn't reach the ball
    "net",              # ball hit net body (didn't go over)
    "net_on_serve",     # serve hit net and didn't land correctly
    "out",              # ball went out of bounds
    "double_bounce",    # ball bounced twice on one side
    "serve_fault",      # serve didn't bounce on server's side
    "let",              # (internal) — replayed, not a final result
    "timeout",          # safety: rally too long
]


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


def _count_bounces_on_side(events: list, side: str) -> int:
    """Count total bounces on a given side."""
    return sum(1 for e in events if isinstance(e, BounceEvent) and e.side == side)


def _ball_hit_net_body(events: list) -> bool:
    """Check if ball hit the net body (not clipped top) — dead ball."""
    for e in events:
        if isinstance(e, NetEvent) and not e.clipped:
            return True
    return False


def _ball_clipped_net(events: list) -> bool:
    """Check if ball clipped the top of the net."""
    for e in events:
        if isinstance(e, NetEvent) and e.clipped:
            return True
    return False


def _ball_went_out(events: list) -> bool:
    """Check if ball went out of bounds."""
    return any(isinstance(e, OutEvent) for e in events)


def simulate_rally(
    p1: AIPlayer,
    p2: AIPlayer,
    server: int,
) -> RallyResult:
    """Simulate a full rally from serve to point.

    Implements all ITTF rules:
    - Serve must bounce on server's side first
    - Let serve (net clip on serve) → replay
    - Net body hit → point to opponent
    - Double bounce on one side → point to opponent
    - Ball not returned → point to hitter

    Args:
        p1: Player 1 (left side).
        p2: Player 2 (right side).
        server: 1 or 2, who serves.

    Returns:
        RallyResult with all shots and outcome.
    """
    serving_player = p1 if server == 1 else p2
    receiving_player = p2 if server == 1 else p1

    max_lets = 10  # Safety limit on consecutive let serves

    for let_attempt in range(max_lets):
        shots: list[RallyShot] = []
        current_hitter = serving_player
        current_receiver = receiving_player

        # === SERVE ===
        serve_state = current_hitter.generate_serve()
        positions, events = simulate(serve_state, max_time=3.0)

        shots.append(RallyShot(
            player=current_hitter.side,
            ball_state=serve_state,
            positions=positions,
            events=events,
            shot_type="serve",
        ))

        server_side = "left" if current_hitter.side == 1 else "right"
        receiver_side = "right" if current_hitter.side == 1 else "left"

        # --- Check: serve hit net body? (dead ball) ---
        if _ball_hit_net_body(events):
            return RallyResult(
                shots=shots,
                winner=current_receiver.side,
                reason="net_on_serve",
                total_duration=positions[-1].t,
                rally_length=1,
            )

        # --- Check: let serve (net clip + lands on receiver's side) ---
        if _ball_clipped_net(events):
            receiver_bounces = [e for e in events if isinstance(e, BounceEvent) and e.side == receiver_side]
            if receiver_bounces:
                # LET — replay the serve (ball clipped net but landed legally)
                continue  # retry serve
            else:
                # Clipped net but didn't land on receiver's side — fault
                return RallyResult(
                    shots=shots,
                    winner=current_receiver.side,
                    reason="net_on_serve",
                    total_duration=positions[-1].t,
                    rally_length=1,
                )

        # --- Check: serve must bounce on server's side first ---
        bounces = [e for e in events if isinstance(e, BounceEvent)]
        server_bounces = [b for b in bounces if b.side == server_side]
        receiver_bounces = [b for b in bounces if b.side == receiver_side]

        if not server_bounces:
            # Serve didn't bounce on server's side — fault
            return RallyResult(
                shots=shots,
                winner=current_receiver.side,
                reason="serve_fault",
                total_duration=positions[-1].t,
                rally_length=1,
            )

        if not receiver_bounces:
            # Serve bounced on server's side but didn't reach receiver's side
            if _ball_went_out(events):
                return RallyResult(
                    shots=shots,
                    winner=current_receiver.side,
                    reason="out",
                    total_duration=positions[-1].t,
                    rally_length=1,
                )
            return RallyResult(
                shots=shots,
                winner=current_receiver.side,
                reason="serve_fault",
                total_duration=positions[-1].t,
                rally_length=1,
            )

        # --- Check: double bounce on receiver's side (ace!) ---
        if _count_bounces_on_side(events, receiver_side) >= 2:
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="ace",
                total_duration=positions[-1].t,
                rally_length=1,
            )

        # Serve is valid — proceed to rally
        break
    else:
        # Too many lets — just give point to receiver (extremely rare)
        return RallyResult(
            shots=shots,
            winner=current_receiver.side,
            reason="net_on_serve",
            total_duration=positions[-1].t if positions else 0,
            rally_length=1,
        )

    # === RALLY LOOP ===
    max_rally = 50
    total_t = positions[-1].t

    for rally_num in range(max_rally):
        # Find where ball lands on receiver's side
        recv_side_str = "left" if current_receiver.side == 1 else "right"
        landing = _find_landing_bounce(events, recv_side_str)

        if not landing:
            # Ball didn't land on receiver's side
            if _ball_went_out(events):
                # Ball went out — point to receiver of the shot
                return RallyResult(
                    shots=shots,
                    winner=current_receiver.side,
                    reason="out",
                    total_duration=total_t,
                    rally_length=len(shots),
                )
            else:
                # Unreturnable winner (ball went past them)
                return RallyResult(
                    shots=shots,
                    winner=current_hitter.side,
                    reason="winner",
                    total_duration=total_t,
                    rally_length=len(shots),
                )

        # --- Check: double bounce on receiver's side ---
        if _count_bounces_on_side(events, recv_side_str) >= 2:
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="double_bounce",
                total_duration=total_t,
                rally_length=len(shots),
            )

        # Can the receiver reach it?
        ball_vel = Vec3(0, 0, 0)
        for p in positions:
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

        # --- Check: return hit net body (dead ball) ---
        if _ball_hit_net_body(events):
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="net",
                total_duration=total_t,
                rally_length=len(shots),
            )

        # --- Check: return went out ---
        hitter_side_str = "left" if current_receiver.side == 1 else "right"
        opponent_side_str = "left" if current_hitter.side == 1 else "right"

        if _ball_went_out(events) and not _find_landing_bounce(events, opponent_side_str):
            return RallyResult(
                shots=shots,
                winner=current_hitter.side,
                reason="out",
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
        if rally.winner == 1:
            match = score_point(match, "right")  # P1 won → scored on right
        else:
            match = score_point(match, "left")   # P2 won → scored on left

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

    p1_winners = sum(1 for r in rallies if r.winner == 1 and r.reason in ("winner", "ace"))
    p2_winners = sum(1 for r in rallies if r.winner == 2 and r.reason in ("winner", "ace"))
    p1_errors = sum(1 for r in rallies if r.winner == 2 and r.reason in ("net", "out", "serve_fault", "net_on_serve"))
    p2_errors = sum(1 for r in rallies if r.winner == 1 and r.reason in ("net", "out", "serve_fault", "net_on_serve"))
    p1_aces = sum(1 for r in rallies if r.winner == 1 and r.reason == "ace")
    p2_aces = sum(1 for r in rallies if r.winner == 2 and r.reason == "ace")
    double_bounces = sum(1 for r in rallies if r.reason == "double_bounce")
    lets = sum(1 for r in rallies if r.reason == "let")  # shouldn't appear in final results

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
        "p1_aces": p1_aces,
        "p2_aces": p2_aces,
        "double_bounces": double_bounces,
        "total_duration": round(total_duration, 2),
        "p1_name": p1.name,
        "p2_name": p2.name,
        "p1_style": p1.label,
        "p2_style": p2.label,
    }
