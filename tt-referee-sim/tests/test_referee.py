"""Tests for the referee scoring engine."""

import pytest

from engine.types import Match
from engine.referee import score_point, create_match


def test_score_11_0_winner():
    """Score 11-0 → winner declared (Player 1)."""
    match = create_match()
    for _ in range(11):
        match = score_point(match, "right")  # P1 scores

    assert match.p1_score == 11
    assert match.p2_score == 0
    assert match.winner == 1


def test_deuce_mode():
    """Score 10-10 → deuce mode, serve every point."""
    match = create_match()
    # Get to 10-10
    for _ in range(10):
        match = score_point(match, "right")  # P1
        match = score_point(match, "left")   # P2

    assert match.p1_score == 10
    assert match.p2_score == 10
    assert match.deuce is True


def test_win_after_deuce():
    """Score 12-10 → winner (2 point lead)."""
    match = create_match()
    for _ in range(10):
        match = score_point(match, "right")
        match = score_point(match, "left")

    # Now 10-10, add 2 more for P1
    match = score_point(match, "right")
    assert match.winner is None  # 11-10, no winner yet

    match = score_point(match, "right")
    assert match.p1_score == 12
    assert match.p2_score == 10
    assert match.winner == 1


def test_no_winner_at_11_10():
    """Score 11-10 → no winner yet (need 2 point lead)."""
    match = create_match()
    for _ in range(10):
        match = score_point(match, "right")
        match = score_point(match, "left")

    match = score_point(match, "right")
    assert match.p1_score == 11
    assert match.p2_score == 10
    assert match.winner is None


def test_serve_rotation_normal():
    """Serve rotates every 2 points normally."""
    match = create_match()
    assert match.server == 1

    match = score_point(match, "right")
    assert match.server == 1  # Still server 1 after 1 point

    match = score_point(match, "right")
    assert match.server == 2  # Rotates after 2 points

    match = score_point(match, "left")
    assert match.server == 2  # Still server 2 after 1 point

    match = score_point(match, "left")
    assert match.server == 1  # Back to server 1


def test_serve_rotation_deuce():
    """At deuce (10-10), serve rotates every 1 point."""
    match = create_match()
    for _ in range(10):
        match = score_point(match, "right")
        match = score_point(match, "left")

    assert match.deuce is True
    server_before = match.server

    match = score_point(match, "right")
    assert match.server != server_before  # Should rotate after 1 point at deuce


def test_game_already_over():
    """Scoring after game is over should not change score."""
    match = create_match()
    for _ in range(11):
        match = score_point(match, "right")

    assert match.winner == 1
    score_before = match.p1_score

    match = score_point(match, "right")
    assert match.p1_score == score_before  # Score unchanged


def test_history_tracking():
    """Every point should be recorded in history."""
    match = create_match()
    match = score_point(match, "right")
    match = score_point(match, "left")
    match = score_point(match, "right")

    assert len(match.history) == 3
    assert match.history[0]["p1"] == 1
    assert match.history[1]["p2"] == 1
    assert match.history[2]["p1"] == 2


def test_player2_wins():
    """Player 2 can also win."""
    match = create_match()
    for _ in range(11):
        match = score_point(match, "left")

    assert match.p2_score == 11
    assert match.winner == 2
