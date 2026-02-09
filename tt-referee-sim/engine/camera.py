"""Virtual camera simulation — sampling, motion blur, detection probability."""

import random
from typing import Optional

from engine.types import BallState, CameraFrame, Vec3
from engine import table

CAMERA_PRESETS = {
    "cheap": {
        "label": "Budget USB (60fps)",
        "fps": 60,
        "resolution": (640, 480),
        "shutter_speed": 1 / 500,
        "global_shutter": False,
        "cost": 25,
    },
    "mid": {
        "label": "Mid-range (120fps)",
        "fps": 120,
        "resolution": (1280, 720),
        "shutter_speed": 1 / 1000,
        "global_shutter": False,
        "cost": 45,
    },
    "arducam": {
        "label": "Arducam OV9281 (200fps)",
        "fps": 200,
        "resolution": (1280, 800),
        "shutter_speed": 1 / 2000,
        "global_shutter": True,
        "cost": 75,
    },
}


def _find_position_at_time(positions: list[BallState], t: float) -> Optional[BallState]:
    """Find the position closest to time t via binary search."""
    if not positions or t < positions[0].t or t > positions[-1].t:
        return None
    lo, hi = 0, len(positions) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if positions[mid].t < t:
            lo = mid + 1
        else:
            hi = mid
    return positions[lo]


def simulate_camera(
    positions: list[BallState],
    fps: int,
    shutter_speed: float,
    resolution: tuple[int, int],
    global_shutter: bool,
) -> list[CameraFrame]:
    """Simulate what a camera captures from ground truth positions.

    Args:
        positions: Ground truth ball states from physics simulation.
        fps: Frames per second.
        shutter_speed: 1/exposure_time (e.g. 1/1000).
        resolution: (width, height) in pixels.
        global_shutter: True for global shutter, False for rolling.

    Returns:
        List of CameraFrame objects.
    """
    if not positions:
        return []

    frame_interval = 1.0 / fps
    pix_per_meter = resolution[0] / (table.TABLE_LENGTH + 1)
    ball_px = table.BALL_RADIUS * 2 * pix_per_meter

    frames = []
    frame_num = 0
    max_t = positions[-1].t

    t = 0.0
    while t < max_t:
        curr = _find_position_at_time(positions, t)
        if curr is None:
            t += frame_interval
            frame_num += 1
            continue

        # Find previous position for motion estimation
        prev_t = max(0, t - frame_interval)
        prev = _find_position_at_time(positions, prev_t)
        if prev is None:
            prev = curr

        # Motion in world coordinates
        dx = curr.pos.x - prev.pos.x
        dy = curr.pos.y - prev.pos.y
        dz = curr.pos.z - prev.pos.z
        motion_m = (dx**2 + dy**2 + dz**2) ** 0.5
        motion_px = motion_m * pix_per_meter

        # Motion blur calculation
        # Blur = motion per frame * (exposure_time / frame_interval)
        # exposure_time = shutter_speed (e.g. 1/2000 s), frame_interval = 1/fps
        blur_ratio = shutter_speed * fps  # fraction of frame time spent exposing
        if global_shutter:
            blur_px = motion_px * blur_ratio * 0.1  # Global shutter: 10x less blur
        else:
            blur_px = motion_px * blur_ratio

        # Effective ball size after blur
        effective_ball_size = max(ball_px - blur_px * 0.5, 1)

        # Detection probability model
        if effective_ball_size < 2:
            confidence = 0.10
        elif effective_ball_size < 4:
            confidence = 0.40
        elif blur_px > ball_px * 3:
            confidence = 0.20
        elif blur_px > ball_px * 1.5:
            confidence = 0.60
        else:
            confidence = min(0.99, 0.70 + effective_ball_size / 50)

        detected = random.random() < confidence

        frames.append(CameraFrame(
            frame_num=frame_num,
            t=t,
            pos_detected=curr.pos.copy() if detected else None,
            confidence=confidence,
            blur_px=blur_px,
            detected=detected,
        ))

        t += frame_interval
        frame_num += 1

    return frames


def compare_cameras(
    positions: list[BallState],
    events: list,
) -> dict:
    """Run all camera presets on the same trajectory and compare.

    Returns dict keyed by preset name with detection stats.
    """
    from engine.types import BounceEvent

    results = {}
    for key, preset in CAMERA_PRESETS.items():
        frames = simulate_camera(
            positions,
            fps=preset["fps"],
            shutter_speed=preset["shutter_speed"],
            resolution=preset["resolution"],
            global_shutter=preset["global_shutter"],
        )

        detected_count = sum(1 for f in frames if f.detected)
        total = len(frames) if frames else 1
        avg_conf = sum(f.confidence for f in frames) / total if frames else 0
        avg_blur = sum(f.blur_px for f in frames) / total if frames else 0

        bounces = [e for e in events if isinstance(e, BounceEvent)]
        bounces_detected = 0
        for b in bounces:
            nearby = [
                f for f in frames
                if abs(f.t - b.t) < 2 / preset["fps"] and f.detected
            ]
            if len(nearby) >= 2:
                bounces_detected += 1

        results[key] = {
            **preset,
            "total_frames": total,
            "detected_frames": detected_count,
            "detection_rate": round(detected_count / total * 100, 1),
            "avg_confidence": round(avg_conf * 100, 1),
            "avg_blur_px": round(avg_blur, 1),
            "bounces_total": len(bounces),
            "bounces_detected": bounces_detected,
            "frames": frames,
        }

    return results
