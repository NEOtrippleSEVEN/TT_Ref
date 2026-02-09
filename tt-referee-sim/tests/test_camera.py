"""Tests for the camera simulation engine."""

import pytest

from engine.types import BallState, Vec3
from engine.camera import simulate_camera, compare_cameras, CAMERA_PRESETS
from engine.physics import simulate
from engine import table
from engine.trajectories import get_shot


def test_frame_count_matches_duration():
    """Frame count should equal duration * fps (±2)."""
    state = get_shot("slow_rally")
    positions, _ = simulate(state)
    duration = positions[-1].t
    fps = 60
    frames = simulate_camera(
        positions, fps=fps, shutter_speed=1/500,
        resolution=(640, 480), global_shutter=False,
    )
    expected = int(duration * fps)
    assert abs(len(frames) - expected) <= 2, (
        f"Expected ~{expected} frames for {duration:.2f}s at {fps}fps, got {len(frames)}"
    )


def test_higher_fps_higher_detection():
    """Higher FPS should yield higher detection rate on the same trajectory."""
    state = get_shot("fast_topspin")
    positions, events = simulate(state)

    results = compare_cameras(positions, events)

    cheap_rate = results["cheap"]["detection_rate"]
    mid_rate = results["mid"]["detection_rate"]
    arducam_rate = results["arducam"]["detection_rate"]

    # Arducam should generally perform better than cheap camera
    # Due to randomness, we run multiple trials
    arducam_better_count = 0
    trials = 10
    for _ in range(trials):
        r = compare_cameras(positions, events)
        if r["arducam"]["detection_rate"] >= r["cheap"]["detection_rate"]:
            arducam_better_count += 1

    assert arducam_better_count >= 7, (
        f"Arducam should beat cheap camera in most trials ({arducam_better_count}/{trials})"
    )


def test_global_shutter_less_blur():
    """Global shutter should produce less motion blur than rolling shutter."""
    state = get_shot("smash")
    positions, _ = simulate(state)

    frames_rolling = simulate_camera(
        positions, fps=200, shutter_speed=1/2000,
        resolution=(1280, 800), global_shutter=False,
    )
    frames_global = simulate_camera(
        positions, fps=200, shutter_speed=1/2000,
        resolution=(1280, 800), global_shutter=True,
    )

    avg_blur_rolling = sum(f.blur_px for f in frames_rolling) / max(len(frames_rolling), 1)
    avg_blur_global = sum(f.blur_px for f in frames_global) / max(len(frames_global), 1)

    assert avg_blur_global < avg_blur_rolling, (
        f"Global shutter blur ({avg_blur_global:.1f}px) should be less than "
        f"rolling shutter ({avg_blur_rolling:.1f}px)"
    )


def test_all_presets_produce_frames():
    """Every camera preset should produce valid frames."""
    state = get_shot("medium_rally")
    positions, events = simulate(state)

    results = compare_cameras(positions, events)

    for key, preset in CAMERA_PRESETS.items():
        assert key in results, f"Missing results for {key}"
        assert results[key]["total_frames"] > 0, f"No frames for {key}"
        assert 0 <= results[key]["detection_rate"] <= 100
