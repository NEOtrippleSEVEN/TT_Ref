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
    assert result.reason in ("ace", "winner", "unforced_error", "net", "out", "unreturned", "timeout")


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
