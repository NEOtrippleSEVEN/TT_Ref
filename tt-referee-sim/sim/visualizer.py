"""Pygame visualizer — top-down + side view, animated ball, camera overlay."""

import sys

try:
    import pygame
except ImportError:
    pygame = None

from engine.types import BallState, BounceEvent, NetEvent, OutEvent, Vec3, Match
from engine import table
from engine.physics import simulate
from engine.camera import simulate_camera, compare_cameras, CAMERA_PRESETS
from engine.referee import score_point, create_match
from engine.trajectories import get_shot, list_shots, SHOT_PRESETS

# Window dimensions
WIN_W = 1200
WIN_H = 700

# Colors
BG_COLOR = (15, 15, 26)
TABLE_GREEN = (26, 92, 45)
TABLE_DARK = (20, 70, 35)
LINE_WHITE = (255, 255, 255)
NET_GRAY = (180, 180, 180)
BALL_ORANGE = (255, 136, 0)
BALL_WHITE = (255, 255, 255)
TRAIL_RED = (233, 69, 96)
DETECTED_GREEN = (40, 167, 69)
MISSED_RED = (220, 53, 69)
ACCENT = (233, 69, 96)
CARD_BG = (26, 26, 46)
PANEL_BG = (22, 33, 62)
TEXT_WHITE = (224, 224, 224)
TEXT_DIM = (136, 136, 136)
BOUNCE_TEAL = (78, 205, 196)
EDGE_RED = (255, 107, 107)
NET_YELLOW = (255, 217, 61)

# Camera preset keys
CAMERA_KEYS = ["cheap", "mid", "arducam"]


def _world_to_top(pos, tx, ty, tw, th):
    """Convert world coordinates to top-down screen position."""
    x = tx + (pos.x + table.TABLE_LENGTH / 2) / table.TABLE_LENGTH * tw
    y = ty + (pos.y + table.TABLE_WIDTH / 2) / table.TABLE_WIDTH * th
    return int(x), int(y)


def _world_to_side(pos, tx, t_surf, tw):
    """Convert world coordinates to side-view screen position."""
    x = tx + (pos.x + table.TABLE_LENGTH / 2) / table.TABLE_LENGTH * tw
    # Height relative to table surface, not ground — keeps ball near the drawn table
    height_above_table = pos.z - table.TABLE_HEIGHT
    pix_per_meter = tw / table.TABLE_LENGTH
    y = t_surf - height_above_table * pix_per_meter
    return int(x), int(y)


def _draw_table_top(surface, margin=40):
    """Draw top-down table view. Returns table dimensions."""
    w, h = surface.get_size()
    tw = w - margin * 2
    th = int(tw * (table.TABLE_WIDTH / table.TABLE_LENGTH))
    tx = margin
    ty = (h - th) // 2

    # Table surface
    pygame.draw.rect(surface, TABLE_GREEN, (tx, ty, tw, th))
    # Border
    pygame.draw.rect(surface, LINE_WHITE, (tx, ty, tw, th), 2)
    # Center line (net)
    pygame.draw.line(surface, LINE_WHITE, (tx + tw // 2, ty), (tx + tw // 2, ty + th), 2)
    # Center dashed line
    dash_len = 6
    gap = 4
    cx = tx
    while cx < tx + tw:
        pygame.draw.line(surface, LINE_WHITE, (cx, ty + th // 2), (min(cx + dash_len, tx + tw), ty + th // 2), 1)
        cx += dash_len + gap
    # Net posts
    pygame.draw.rect(surface, NET_GRAY, (tx + tw // 2 - 1, ty - 8, 2, th + 16))

    return tx, ty, tw, th


def _draw_table_side(surface, margin=40):
    """Draw side-view table. Returns table dimensions."""
    w, h = surface.get_size()
    tw = w - margin * 2
    t_surf = int(h * 0.65)
    tx = margin

    # Table legs
    pygame.draw.rect(surface, (92, 58, 26), (tx, t_surf, tw, 6))
    # Table surface
    pygame.draw.rect(surface, TABLE_GREEN, (tx, t_surf - 3, tw, 3))
    pygame.draw.rect(surface, LINE_WHITE, (tx, t_surf - 3, tw, 3), 1)
    # Net
    net_x = tx + tw // 2
    net_h = int(table.NET_HEIGHT / table.TABLE_LENGTH * tw)
    pygame.draw.line(surface, NET_GRAY, (net_x, t_surf), (net_x, t_surf - net_h - 3), 2)

    return tx, t_surf, tw


def run_visualizer():
    """Launch the Pygame visualizer window."""
    if pygame is None:
        print("ERROR: pygame is not installed. Run: pip install pygame")
        return

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("TT Referee — AI Simulation")
    clock = pygame.time.Clock()

    # State
    shot_keys = list_shots()
    shot_idx = 1  # medium_rally
    camera_idx = 2  # arducam
    view = "top"  # "top" or "side"
    show_trail = True
    show_camera_frames = True
    playing = False
    play_t = 0.0
    play_speed = 0.3
    match = create_match()

    # Fonts
    font_sm = pygame.font.SysFont("monospace", 11)
    font_md = pygame.font.SysFont("monospace", 13)
    font_lg = pygame.font.SysFont("monospace", 18)
    font_xl = pygame.font.SysFont("monospace", 36, bold=True)
    font_title = pygame.font.SysFont("monospace", 14, bold=True)

    # Initial simulation
    def run_sim():
        key = shot_keys[shot_idx]
        state = get_shot(key)
        positions, events = simulate(state)
        cam_key = CAMERA_KEYS[camera_idx]
        preset = CAMERA_PRESETS[cam_key]
        frames = simulate_camera(
            positions, preset["fps"], preset["shutter_speed"],
            preset["resolution"], preset["global_shutter"],
        )
        cam_results = compare_cameras(positions, events)
        return positions, events, frames, cam_results

    positions, events, cam_frames, cam_results = run_sim()

    # Canvas for the table (left 70%)
    canvas_w = int(WIN_W * 0.70)
    canvas_h = WIN_H - 60  # leave room for header
    canvas_surface = pygame.Surface((canvas_w, canvas_h))

    running = True
    start_ticks = 0

    while running:
        dt_ms = clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    playing = not playing
                    if playing:
                        start_ticks = pygame.time.get_ticks()
                        play_t = 0.0
                elif event.key == pygame.K_r:
                    playing = False
                    play_t = 0.0
                    positions, events, cam_frames, cam_results = run_sim()
                elif event.key == pygame.K_t:
                    view = "side" if view == "top" else "top"
                elif event.key == pygame.K_n:
                    shot_idx = (shot_idx + 1) % len(shot_keys)
                    playing = False
                    play_t = 0.0
                    positions, events, cam_frames, cam_results = run_sim()
                elif event.key == pygame.K_1:
                    camera_idx = 0
                    positions, events, cam_frames, cam_results = run_sim()
                elif event.key == pygame.K_2:
                    camera_idx = 1
                    positions, events, cam_frames, cam_results = run_sim()
                elif event.key == pygame.K_3:
                    camera_idx = 2
                    positions, events, cam_frames, cam_results = run_sim()
                elif event.key == pygame.K_s:
                    # Score from sim
                    bounces = [e for e in events if isinstance(e, BounceEvent)]
                    if bounces:
                        last = bounces[-1]
                        match = score_point(match, last.side)

        # Update animation
        if playing:
            elapsed_ms = pygame.time.get_ticks() - start_ticks
            play_t = (elapsed_ms / 1000.0) * play_speed
            duration = positions[-1].t if positions else 0
            if play_t >= duration:
                playing = False
                play_t = duration

        # ---- DRAW ----
        screen.fill(BG_COLOR)

        # Header bar
        pygame.draw.rect(screen, CARD_BG, (0, 0, WIN_W, 44))
        pygame.draw.line(screen, ACCENT, (0, 43), (WIN_W, 43), 2)

        # Title
        dot_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(dot_surf, ACCENT, (5, 5), 5)
        screen.blit(dot_surf, (12, 17))
        title = font_title.render("TT REFEREE", True, TEXT_WHITE)
        screen.blit(title, (28, 14))
        ver = font_sm.render("AI Simulation v0.1", True, TEXT_DIM)
        screen.blit(ver, (145, 17))

        # Controls hint
        controls = font_sm.render(
            "SPACE:play  R:reset  N:next shot  1/2/3:camera  T:view  S:score  Q:quit",
            True, TEXT_DIM,
        )
        screen.blit(controls, (WIN_W - controls.get_width() - 10, 17))

        # ---- TABLE CANVAS ----
        canvas_surface.fill((10, 10, 21))
        shot_key = shot_keys[shot_idx]
        cam_key = CAMERA_KEYS[camera_idx]

        if view == "top":
            tx, ty, tw, th = _draw_table_top(canvas_surface)
            to_screen = lambda p: _world_to_top(p, tx, ty, tw, th)
        else:
            tx, t_surf, tw = _draw_table_side(canvas_surface)
            to_screen = lambda p: _world_to_side(p, tx, t_surf, tw)

        # Trail
        if show_trail and len(positions) > 1:
            if playing:
                trail_end = next(
                    (i for i, p in enumerate(positions) if p.t >= play_t),
                    len(positions),
                )
            else:
                trail_end = len(positions)

            trail_points = []
            for i in range(0, min(trail_end, len(positions)), max(1, len(positions) // 500)):
                trail_points.append(to_screen(positions[i].pos))

            if len(trail_points) > 1:
                pygame.draw.lines(canvas_surface, (*TRAIL_RED, 90), False, trail_points, 2)

        # Camera frame dots
        if show_camera_frames:
            for f in cam_frames:
                if playing and f.t > play_t:
                    break
                if f.pos_detected:
                    sp = to_screen(f.pos_detected)
                    color = DETECTED_GREEN if f.detected else (255, 193, 7)
                    pygame.draw.circle(canvas_surface, color, sp, 3)

        # Current ball position
        duration = positions[-1].t if positions else 0
        if playing:
            idx = next(
                (i for i, p in enumerate(positions) if p.t >= play_t),
                len(positions) - 1,
            )
        else:
            idx = len(positions) - 1

        if 0 <= idx < len(positions):
            bp = to_screen(positions[idx].pos)
            # Glow effect
            glow = pygame.Surface((30, 30), pygame.SRCALPHA)
            pygame.draw.circle(glow, (*ACCENT, 50), (15, 15), 14)
            canvas_surface.blit(glow, (bp[0] - 15, bp[1] - 15))
            # Ball
            pygame.draw.circle(canvas_surface, BALL_ORANGE, bp, 7)
            pygame.draw.circle(canvas_surface, BALL_WHITE, (bp[0] - 2, bp[1] - 2), 3)
            pygame.draw.circle(canvas_surface, LINE_WHITE, bp, 7, 1)

        # Event markers
        for e in events:
            if playing and e.t > play_t:
                break
            ep = to_screen(e.pos)
            if isinstance(e, BounceEvent):
                color = EDGE_RED if e.is_edge else BOUNCE_TEAL
                label = "EDGE" if e.is_edge else "BOUNCE"
            elif isinstance(e, NetEvent):
                color = NET_YELLOW
                label = "NET"
            elif isinstance(e, OutEvent):
                color = EDGE_RED
                label = "OUT"
            else:
                continue
            txt = font_sm.render(label, True, color)
            canvas_surface.blit(txt, (ep[0] - txt.get_width() // 2, ep[1] - 16))

        # Info overlay
        overlay = pygame.Surface((210, 55), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        canvas_surface.blit(overlay, (8, 8))
        canvas_surface.blit(
            font_sm.render(f"Shot: {SHOT_PRESETS[shot_key]['label']}", True, TEXT_DIM),
            (14, 12),
        )
        canvas_surface.blit(
            font_sm.render(f"Camera: {CAMERA_PRESETS[cam_key]['label']}", True, TEXT_DIM),
            (14, 26),
        )
        t_display = play_t if playing else duration
        canvas_surface.blit(
            font_sm.render(f"Time: {t_display:.3f}s", True, TEXT_DIM),
            (14, 40),
        )

        screen.blit(canvas_surface, (0, 50))

        # ---- STATS PANEL (right 30%) ----
        panel_x = canvas_w + 4
        panel_w = WIN_W - panel_x
        pygame.draw.rect(screen, PANEL_BG, (panel_x, 50, panel_w, WIN_H - 50))
        pygame.draw.line(screen, (42, 42, 74), (panel_x, 50), (panel_x, WIN_H), 1)

        px = panel_x + 12
        py = 62

        # Shot info
        screen.blit(font_title.render("SHOT", True, ACCENT), (px, py))
        py += 20
        screen.blit(font_md.render(SHOT_PRESETS[shot_key]["label"], True, TEXT_WHITE), (px, py))
        py += 16
        screen.blit(font_sm.render(f"Speed: {SHOT_PRESETS[shot_key]['speed']} km/h", True, TEXT_DIM), (px, py))
        py += 24

        # Camera info
        screen.blit(font_title.render("CAMERA", True, ACCENT), (px, py))
        py += 20
        preset = CAMERA_PRESETS[cam_key]
        screen.blit(font_md.render(preset["label"], True, TEXT_WHITE), (px, py))
        py += 16
        screen.blit(font_sm.render(f"€{preset['cost']}  {preset['resolution'][0]}x{preset['resolution'][1]}", True, TEXT_DIM), (px, py))
        py += 24

        # Detection stats
        cr = cam_results.get(cam_key, {})
        screen.blit(font_title.render("DETECTION", True, ACCENT), (px, py))
        py += 20

        det_rate = cr.get("detection_rate", 0)
        det_color = DETECTED_GREEN if det_rate > 85 else NET_YELLOW if det_rate > 60 else MISSED_RED
        screen.blit(font_lg.render(f"{det_rate}%", True, det_color), (px, py))
        py += 22
        screen.blit(font_sm.render("detection rate", True, TEXT_DIM), (px, py))
        py += 18

        screen.blit(font_md.render(f"Confidence: {cr.get('avg_confidence', 0)}%", True, TEXT_WHITE), (px, py))
        py += 16
        bd = cr.get("bounces_detected", 0)
        bt = cr.get("bounces_total", 0)
        bc = DETECTED_GREEN if bd == bt else NET_YELLOW
        screen.blit(font_md.render(f"Bounces: {bd}/{bt}", True, bc), (px, py))
        py += 16
        screen.blit(font_md.render(f"Blur: {cr.get('avg_blur_px', 0)} px", True, TEXT_WHITE), (px, py))
        py += 30

        # Score
        screen.blit(font_title.render("SCORE", True, ACCENT), (px, py))
        py += 22

        p1_color = BOUNCE_TEAL
        p2_color = ACCENT
        screen.blit(font_xl.render(str(match.p1_score), True, p1_color), (px, py))
        dash = font_lg.render("-", True, TEXT_DIM)
        screen.blit(dash, (px + 50, py + 8))
        screen.blit(font_xl.render(str(match.p2_score), True, p2_color), (px + 70, py))
        py += 44

        server_txt = f"Server: P{match.server}"
        screen.blit(font_sm.render(server_txt, True, TEXT_DIM), (px, py))
        py += 14

        if match.deuce:
            screen.blit(font_sm.render("DEUCE", True, NET_YELLOW), (px, py))
            py += 14

        if match.winner:
            screen.blit(font_md.render(f"P{match.winner} WINS!", True, NET_YELLOW), (px, py))
            py += 20

        # Toggle states
        py = WIN_H - 50
        trail_txt = f"Trail: {'ON' if show_trail else 'OFF'}"
        cam_txt = f"Cam frames: {'ON' if show_camera_frames else 'OFF'}"
        screen.blit(font_sm.render(trail_txt, True, TEXT_DIM), (px, py))
        screen.blit(font_sm.render(cam_txt, True, TEXT_DIM), (px, py + 14))

        # Play state indicator
        state_txt = "PLAYING" if playing else "PAUSED"
        state_color = DETECTED_GREEN if playing else TEXT_DIM
        screen.blit(font_sm.render(state_txt, True, state_color), (px + 140, py))

        pygame.display.flip()

    pygame.quit()
