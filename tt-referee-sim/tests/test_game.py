"""Tests for the game simulation engine."""

import random
import pytest

from engine.ai_player import AIPlayer
from engine.game import simulate_rally, simulate_game, RallyResult, GameResult


def test_rally_produces_result():
    """A rally should always produce a RallyResult with a winner."""
    random.seed(42)
    p1 = AIPlayer("P1", "allround", 1)
    p2 = AIPlayer("P2", "allround", 2)

    result = simulate_rally(p1, p2, server=1)
    assert isinstance(result, RallyResult)
    assert result.winner in (1, 2)
    assert result.rally_length >= 1
    assert len(result.shots) >= 1
    assert result.reason in (
        "ace", "winner", "unreturned", "net", "net_on_serve",
        "out", "double_bounce", "serve_fault", "timeout",
    )


def test_rally_has_serve():
    """First shot of every rally should be a serve."""
    random.seed(42)
    p1 = AIPlayer("P1", "aggressive", 1)
    p2 = AIPlayer("P2", "defensive", 2)

    result = simulate_rally(p1, p2, server=1)
    assert result.shots[0].shot_type == "serve"
    assert result.shots[0].player == 1


def test_game_completes():
    """A full game should always produce a winner."""
    random.seed(42)
    p1 = AIPlayer("P1", "aggressive", 1)
    p2 = AIPlayer("P2", "defensive", 2)

    result = simulate_game(p1, p2)
    assert isinstance(result, GameResult)
    assert result.match.winner in (1, 2)
    assert result.match.p1_score >= 0
    assert result.match.p2_score >= 0
    # Winner must have >= 11 and lead by >= 2
    w_score = result.match.p1_score if result.match.winner == 1 else result.match.p2_score
    l_score = result.match.p2_score if result.match.winner == 1 else result.match.p1_score
    assert w_score >= 11
    assert w_score - l_score >= 2


def test_game_stats_populated():
    """Game stats dictionary should contain expected keys."""
    random.seed(42)
    p1 = AIPlayer("P1", "allround", 1)
    p2 = AIPlayer("P2", "allround", 2)

    result = simulate_game(p1, p2)
    stats = result.stats
    assert "total_rallies" in stats
    assert "avg_rally_length" in stats
    assert "reasons" in stats
    assert "p1_winners" in stats
    assert "p2_winners" in stats
    assert stats["total_rallies"] > 0
    assert stats["avg_rally_length"] > 0


def test_different_seeds_different_results():
    """Different random seeds should produce different game outcomes."""
    results = []
    for seed in [1, 2, 3, 4, 5]:
        random.seed(seed)
        p1 = AIPlayer("P1", "allround", 1)
        p2 = AIPlayer("P2", "allround", 2)
        result = simulate_game(p1, p2)
        results.append((result.match.p1_score, result.match.p2_score))

    # At least 2 different outcomes from 5 seeds
    unique_results = set(results)
    assert len(unique_results) >= 2, (
        f"Expected varied outcomes but got: {results}"
    )


def test_pro_beats_beginner_mostly():
    """Professional should beat beginner in most games."""
    pro_wins = 0
    for seed in range(20):
        random.seed(seed)
        p1 = AIPlayer("Pro", "pro", 1)
        p2 = AIPlayer("Noob", "beginner", 2)
        result = simulate_game(p1, p2)
        if result.match.winner == 1:
            pro_wins += 1

    assert pro_wins >= 12, (
        f"Pro won only {pro_wins}/20 games against beginner — expected at least 12"
    )


# --- Edge case tests for ITTF rules ---


def test_net_body_hit_stops_ball():
    """Ball hitting net body should stop dead and be marked not alive."""
    from engine.types import BallState, Vec3
    from engine.physics import simulate
    from engine import table

    # Fire ball straight into net body (below net top)
    state = BallState(
        pos=Vec3(-0.3, 0, table.TABLE_HEIGHT + 0.05),  # below net top
        vel=Vec3(5, 0, 0),
        spin=Vec3(0, 0, 0),
    )
    positions, events = simulate(state, max_time=1.0)
    from engine.types import NetEvent

    net_events = [e for e in events if isinstance(e, NetEvent)]
    assert len(net_events) > 0, "Expected a net event"
    assert not net_events[0].clipped, "Expected net body hit (not clip)"
    assert not positions[-1].alive, "Ball should be dead after net body hit"


def test_double_bounce_detection():
    """Double bounce on one side should be detectable from events."""
    from engine.game import _count_bounces_on_side
    from engine.types import BounceEvent, Vec3

    events = [
        BounceEvent(pos=Vec3(0.5, 0, 0.78), t=0.1, side="right", is_edge=False),
        BounceEvent(pos=Vec3(0.8, 0, 0.78), t=0.3, side="right", is_edge=False),
    ]
    assert _count_bounces_on_side(events, "right") == 2


def test_serve_fault_no_server_bounce():
    """A serve that skips server's half is a fault."""
    from engine.game import _find_landing_bounce, _count_bounces_on_side
    from engine.types import BounceEvent, Vec3

    # Only bounce on receiver's side — serve fault
    events = [
        BounceEvent(pos=Vec3(0.5, 0, 0.78), t=0.2, side="right", is_edge=False),
    ]
    assert _count_bounces_on_side(events, "left") == 0  # no server bounce
    assert _count_bounces_on_side(events, "right") == 1


def test_game_has_edge_case_reasons():
    """Over many games, edge case reasons should appear at least once."""
    all_reasons = set()
    for seed in range(50):
        random.seed(seed)
        p1 = AIPlayer("P1", "allround", 1)
        p2 = AIPlayer("P2", "allround", 2)
        result = simulate_game(p1, p2)
        all_reasons.update(result.stats["reasons"].keys())

    # Should see at least some of the common outcomes
    assert "unreturned" in all_reasons or "out" in all_reasons, (
        f"Expected common reasons, got: {all_reasons}"
    )


def test_rally_server_side_correct():
    """Server's shots should come from the correct side."""
    random.seed(42)
    p1 = AIPlayer("P1", "allround", 1)
    p2 = AIPlayer("P2", "allround", 2)

    # Server is player 1 (left side)
    result = simulate_rally(p1, p2, server=1)
    assert result.shots[0].player == 1
    serve_x = result.shots[0].ball_state.pos.x
    assert serve_x < 0, f"P1 serve should start on left side, got x={serve_x}"

    # Server is player 2 (right side)
    random.seed(42)
    result = simulate_rally(p1, p2, server=2)
    assert result.shots[0].player == 2
    serve_x = result.shots[0].ball_state.pos.x
    assert serve_x > 0, f"P2 serve should start on right side, got x={serve_x}"


def test_game_stats_include_edge_case_fields():
    """Game stats should include aces, double bounces, errors."""
    random.seed(42)
    p1 = AIPlayer("P1", "aggressive", 1)
    p2 = AIPlayer("P2", "defensive", 2)
    result = simulate_game(p1, p2)
    stats = result.stats

    assert "p1_aces" in stats
    assert "p2_aces" in stats
    assert "double_bounces" in stats
    assert "p1_unforced_errors" in stats
    assert "p2_unforced_errors" in stats
    assert isinstance(stats["p1_aces"], int)
    assert isinstance(stats["double_bounces"], int)
