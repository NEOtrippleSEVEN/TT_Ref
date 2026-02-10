"""Pygame visualizer — full game mode with AI players, larger view, auto-scoring."""

import sys
import random

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
from engine.ai_player import AIPlayer, PLAYSTYLES
from engine.game import simulate_rally, RallyResult

# Window dimensions — MUCH larger
WIN_W = 1400
WIN_H = 820

# Colors
BG_COLOR = (12, 12, 22)
TABLE_GREEN = (26, 100, 46)
LINE_WHITE = (255, 255, 255)
NET_GRAY = (180, 180, 180)
BALL_ORANGE = (255, 136, 0)
BALL_WHITE = (255, 255, 255)
TRAIL_RED = (233, 69, 96)
DETECTED_GREEN = (40, 167, 69)
ACCENT = (233, 69, 96)
CARD_BG = (26, 26, 46)
PANEL_BG = (22, 33, 62)
TEXT_WHITE = (224, 224, 224)
TEXT_DIM = (136, 136, 136)
BOUNCE_TEAL = (78, 205, 196)
EDGE_RED = (255, 107, 107)
NET_YELLOW = (255, 217, 61)
P1_COLOR = (78, 205, 196)
P2_COLOR = (233, 69, 96)

CAMERA_KEYS = ["cheap", "mid", "arducam"]


def _world_to_top(pos, tx, ty, tw, th):
    x = tx + (pos.x + table.TABLE_LENGTH / 2) / table.TABLE_LENGTH * tw
    y = ty + (pos.y + table.TABLE_WIDTH / 2) / table.TABLE_WIDTH * th
    return int(x), int(y)


def _world_to_side(pos, tx, t_surf, tw):
    x = tx + (pos.x + table.TABLE_LENGTH / 2) / table.TABLE_LENGTH * tw
    height_above_table = pos.z - table.TABLE_HEIGHT
    pix_per_meter = tw / table.TABLE_LENGTH
    y = t_surf - height_above_table * pix_per_meter
    return int(x), int(y)


def _draw_table_top(surface, margin=20):
    w, h = surface.get_size()
    tw = w - margin * 2
    th = int(tw * (table.TABLE_WIDTH / table.TABLE_LENGTH))
    tx = margin
    ty = (h - th) // 2

    pygame.draw.rect(surface, TABLE_GREEN, (tx, ty, tw, th))
    pygame.draw.rect(surface, LINE_WHITE, (tx, ty, tw, th), 2)
    pygame.draw.line(surface, LINE_WHITE, (tx + tw // 2, ty), (tx + tw // 2, ty + th), 2)
    dash_len, gap = 8, 5
    cx = tx
    while cx < tx + tw:
        pygame.draw.line(surface, (200, 200, 200), (cx, ty + th // 2), (min(cx + dash_len, tx + tw), ty + th // 2), 1)
        cx += dash_len + gap
    pygame.draw.rect(surface, NET_GRAY, (tx + tw // 2 - 1, ty - 6, 2, th + 12))
    return tx, ty, tw, th


def _draw_table_side(surface, margin=20):
    w, h = surface.get_size()
    tw = w - margin * 2
    t_surf = int(h * 0.62)
    tx = margin

    pygame.draw.rect(surface, (80, 50, 22), (tx, t_surf, tw, 6))
    pygame.draw.rect(surface, TABLE_GREEN, (tx, t_surf - 4, tw, 4))
    pygame.draw.rect(surface, LINE_WHITE, (tx, t_surf - 4, tw, 4), 1)
    net_x = tx + tw // 2
    net_h = int(table.NET_HEIGHT / table.TABLE_LENGTH * tw)
    pygame.draw.line(surface, NET_GRAY, (net_x, t_surf), (net_x, t_surf - net_h - 4), 3)
    return tx, t_surf, tw


def run_visualizer():
    """Launch the Pygame visualizer — full game mode with AI."""
    if pygame is None:
        print("ERROR: pygame is not installed. Run: pip install pygame")
        return

    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("TT Referee — AI Match Simulation")
    clock = pygame.time.Clock()

    font_sm = pygame.font.SysFont("monospace", 12)
    font_md = pygame.font.SysFont("monospace", 14)
    font_lg = pygame.font.SysFont("monospace", 20)
    font_xl = pygame.font.SysFont("monospace", 42, bold=True)
    font_title = pygame.font.SysFont("monospace", 15, bold=True)
    font_header = pygame.font.SysFont("monospace", 11)

    view = "top"
    camera_idx = 2
    playing = False
    auto_mode = False
    play_speed = 0.3

    styles = list(PLAYSTYLES.keys())
    p1_style_idx = 0
    p2_style_idx = 1

    def make_players():
        return (
            AIPlayer("P1", styles[p1_style_idx], 1),
            AIPlayer("P2", styles[p2_style_idx], 2),
        )

    p1, p2 = make_players()
    match = create_match()
    rally_results: list[RallyResult] = []

    all_positions = []
    all_events = []
    cam_frames = []
    cam_results = {}
    rally_duration = 0.0
    current_rally: RallyResult = None
    rally_msg = "Press G to start a game, or SPACE for single rally"

    def run_single_rally():
        nonlocal all_positions, all_events, cam_frames, cam_results, rally_duration, current_rally
        rally = simulate_rally(p1, p2, match.server)
        current_rally = rally

        all_positions = []
        all_events = []
        t_offset = 0.0
        for shot in rally.shots:
            for p in shot.positions:
                cp = p.copy()
                cp.t += t_offset
                all_positions.append(cp)
            for e in shot.events:
                kwargs = {}
                if isinstance(e, BounceEvent):
                    kwargs = {"side": e.side, "is_edge": e.is_edge}
                elif isinstance(e, NetEvent):
                    kwargs = {"clipped": e.clipped}
                ec = type(e)(pos=e.pos.copy(), t=e.t + t_offset, **kwargs)
                all_events.append(ec)
            if shot.positions:
                t_offset += shot.positions[-1].t

        rally_duration = t_offset
        cam_key = CAMERA_KEYS[camera_idx]
        preset = CAMERA_PRESETS[cam_key]
        cam_frames = simulate_camera(
            all_positions, preset["fps"], preset["shutter_speed"],
            preset["resolution"], preset["global_shutter"],
        )
        cam_results = compare_cameras(all_positions, all_events)
        return rally

    canvas_w = int(WIN_W * 0.75)
    canvas_h = WIN_H - 50
    canvas_surface = pygame.Surface((canvas_w, canvas_h))

    running = True
    start_ticks = 0
    play_t = 0.0
    game_active = False

    while running:
        clock.tick(60)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_q:
                    running = False
                elif event.key == pygame.K_SPACE:
                    if all_positions:
                        playing = not playing
                        if playing:
                            start_ticks = pygame.time.get_ticks()
                            play_t = 0.0
                    else:
                        run_single_rally()
                        rally_msg = f"Rally: {current_rally.rally_length} shots — {current_rally.reason}"
                        playing = True
                        start_ticks = pygame.time.get_ticks()
                        play_t = 0.0
                elif event.key == pygame.K_g:
                    game_active = True
                    match = create_match()
                    rally_results = []
                    p1, p2 = make_players()
                    run_single_rally()
                    rally_msg = f"Game started! Rally: {current_rally.rally_length} shots"
                    playing = True
                    start_ticks = pygame.time.get_ticks()
                    play_t = 0.0
                elif event.key == pygame.K_r:
                    run_single_rally()
                    rally_msg = f"Rally: {current_rally.rally_length} shots — {current_rally.reason}"
                    playing = True
                    start_ticks = pygame.time.get_ticks()
                    play_t = 0.0
                elif event.key == pygame.K_t:
                    view = "side" if view == "top" else "top"
                elif event.key == pygame.K_1:
                    camera_idx = 0
                elif event.key == pygame.K_2:
                    camera_idx = 1
                elif event.key == pygame.K_3:
                    camera_idx = 2
                elif event.key == pygame.K_LEFTBRACKET:
                    p1_style_idx = (p1_style_idx - 1) % len(styles)
                    p1, p2 = make_players()
                elif event.key == pygame.K_RIGHTBRACKET:
                    p1_style_idx = (p1_style_idx + 1) % len(styles)
                    p1, p2 = make_players()
                elif event.key == pygame.K_MINUS:
                    p2_style_idx = (p2_style_idx - 1) % len(styles)
                    p1, p2 = make_players()
                elif event.key == pygame.K_EQUALS:
                    p2_style_idx = (p2_style_idx + 1) % len(styles)
                    p1, p2 = make_players()
                elif event.key == pygame.K_a:
                    auto_mode = not auto_mode

        # Update animation
        if playing and all_positions:
            elapsed_ms = pygame.time.get_ticks() - start_ticks
            play_t = (elapsed_ms / 1000.0) * play_speed
            if play_t >= rally_duration:
                playing = False
                play_t = rally_duration
                if game_active and current_rally and match.winner is None:
                    if current_rally.winner == 1:
                        match = score_point(match, "right")
                    else:
                        match = score_point(match, "left")
                    rally_results.append(current_rally)
                    if match.winner:
                        rally_msg = f"GAME OVER! P{match.winner} wins {match.p1_score}-{match.p2_score}"
                        game_active = False
                    elif auto_mode:
                        run_single_rally()
                        rally_msg = f"{match.p1_score}-{match.p2_score} | {current_rally.rally_length} shots — {current_rally.reason}"
                        playing = True
                        start_ticks = pygame.time.get_ticks()
                        play_t = 0.0

        # ---- DRAW ----
        screen.fill(BG_COLOR)

        # Header
        pygame.draw.rect(screen, CARD_BG, (0, 0, WIN_W, 42))
        pygame.draw.line(screen, ACCENT, (0, 41), (WIN_W, 41), 2)
        dot = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(dot, ACCENT, (5, 5), 5)
        screen.blit(dot, (12, 16))
        screen.blit(font_title.render("TT REFEREE", True, TEXT_WHITE), (28, 13))
        screen.blit(font_sm.render("AI Match v2.0", True, TEXT_DIM), (155, 16))
        controls = font_header.render(
            "SPACE:play  G:game  R:rally  A:auto  T:view  1/2/3:cam  [/]:P1  -/=:P2  Q:quit",
            True, TEXT_DIM,
        )
        screen.blit(controls, (WIN_W - controls.get_width() - 10, 17))

        # ---- TABLE CANVAS ----
        canvas_surface.fill((8, 8, 18))
        cam_key = CAMERA_KEYS[camera_idx]

        if view == "top":
            tx, ty, tw, th = _draw_table_top(canvas_surface)
            to_screen = lambda p: _world_to_top(p, tx, ty, tw, th)
        else:
            tx, t_surf, tw = _draw_table_side(canvas_surface)
            to_screen = lambda p: _world_to_side(p, tx, t_surf, tw)

        # Trail
        if all_positions and len(all_positions) > 1:
            trail_end = len(all_positions)
            if playing:
                trail_end = next(
                    (i for i, p in enumerate(all_positions) if p.t >= play_t),
                    len(all_positions),
                )
            pts = []
            step = max(1, len(all_positions) // 800)
            for i in range(0, min(trail_end, len(all_positions)), step):
                pts.append(to_screen(all_positions[i].pos))
            if len(pts) > 1:
                pygame.draw.lines(canvas_surface, TRAIL_RED, False, pts, 2)

        # Camera frame dots
        for f in cam_frames:
            if playing and f.t > play_t:
                break
            if f.pos_detected:
                sp = to_screen(f.pos_detected)
                color = DETECTED_GREEN if f.detected else (80, 80, 80)
                pygame.draw.circle(canvas_surface, color, sp, 3)

        # Ball
        if all_positions:
            idx = len(all_positions) - 1
            if playing:
                idx = next(
                    (i for i, p in enumerate(all_positions) if p.t >= play_t),
                    len(all_positions) - 1,
                )
            if 0 <= idx < len(all_positions):
                bp = to_screen(all_positions[idx].pos)
                glow = pygame.Surface((34, 34), pygame.SRCALPHA)
                pygame.draw.circle(glow, (*ACCENT, 40), (17, 17), 16)
                canvas_surface.blit(glow, (bp[0] - 17, bp[1] - 17))
                pygame.draw.circle(canvas_surface, BALL_ORANGE, bp, 8)
                pygame.draw.circle(canvas_surface, BALL_WHITE, (bp[0] - 2, bp[1] - 2), 3)
                pygame.draw.circle(canvas_surface, LINE_WHITE, bp, 8, 1)

        # Event markers
        for e in all_events:
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
            canvas_surface.blit(txt, (ep[0] - txt.get_width() // 2, ep[1] - 18))

        # Rally message
        if rally_msg:
            overlay = pygame.Surface((canvas_w, 26), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            canvas_surface.blit(overlay, (0, canvas_h - 26))
            canvas_surface.blit(font_md.render(rally_msg, True, TEXT_WHITE), (10, canvas_h - 22))

        screen.blit(canvas_surface, (0, 46))

        # ---- STATS PANEL ----
        panel_x = canvas_w + 2
        panel_w = WIN_W - panel_x
        pygame.draw.rect(screen, PANEL_BG, (panel_x, 46, panel_w, WIN_H - 46))
        pygame.draw.line(screen, (42, 42, 74), (panel_x, 46), (panel_x, WIN_H), 1)

        px = panel_x + 10
        py = 56

        # Score
        screen.blit(font_title.render("SCORE", True, ACCENT), (px, py))
        py += 24
        screen.blit(font_xl.render(str(match.p1_score), True, P1_COLOR), (px, py))
        screen.blit(font_lg.render("-", True, TEXT_DIM), (px + 55, py + 10))
        screen.blit(font_xl.render(str(match.p2_score), True, P2_COLOR), (px + 80, py))
        py += 50
        if match.deuce:
            screen.blit(font_md.render("DEUCE!", True, NET_YELLOW), (px, py))
            py += 18
        if match.winner:
            screen.blit(font_lg.render(f"P{match.winner} WINS!", True, NET_YELLOW), (px, py))
            py += 24
        else:
            screen.blit(font_sm.render(f"Server: P{match.server}", True, TEXT_DIM), (px, py))
            py += 16
        py += 10

        # Players
        pygame.draw.line(screen, (42, 42, 74), (px, py), (px + panel_w - 20, py), 1)
        py += 8
        screen.blit(font_title.render("PLAYERS", True, ACCENT), (px, py))
        py += 20
        screen.blit(font_md.render(f"P1: {PLAYSTYLES[styles[p1_style_idx]]['label']}", True, P1_COLOR), (px, py))
        py += 16
        screen.blit(font_sm.render(f"  Pwr:{p1.power:.0%}  Con:{p1.consistency:.0%}  Spn:{p1.spin_ability:.0%}", True, TEXT_DIM), (px, py))
        py += 18
        screen.blit(font_md.render(f"P2: {PLAYSTYLES[styles[p2_style_idx]]['label']}", True, P2_COLOR), (px, py))
        py += 16
        screen.blit(font_sm.render(f"  Pwr:{p2.power:.0%}  Con:{p2.consistency:.0%}  Spn:{p2.spin_ability:.0%}", True, TEXT_DIM), (px, py))
        py += 22

        # Camera
        pygame.draw.line(screen, (42, 42, 74), (px, py), (px + panel_w - 20, py), 1)
        py += 8
        screen.blit(font_title.render("CAMERA", True, ACCENT), (px, py))
        py += 20
        preset = CAMERA_PRESETS[cam_key]
        screen.blit(font_md.render(preset["label"], True, TEXT_WHITE), (px, py))
        py += 16
        cr = cam_results.get(cam_key, {})
        det_rate = cr.get("detection_rate", 0)
        det_color = DETECTED_GREEN if det_rate > 85 else NET_YELLOW if det_rate > 60 else EDGE_RED
        screen.blit(font_lg.render(f"{det_rate}%", True, det_color), (px, py))
        screen.blit(font_sm.render("detect", True, TEXT_DIM), (px + 65, py + 4))
        py += 24
        screen.blit(font_sm.render(f"  Blur: {cr.get('avg_blur_px', 0)} px", True, TEXT_DIM), (px, py))
        py += 20

        # Match stats
        if rally_results:
            pygame.draw.line(screen, (42, 42, 74), (px, py), (px + panel_w - 20, py), 1)
            py += 8
            screen.blit(font_title.render("MATCH STATS", True, ACCENT), (px, py))
            py += 20
            avg_len = sum(r.rally_length for r in rally_results) / max(len(rally_results), 1)
            max_len = max((r.rally_length for r in rally_results), default=0)
            screen.blit(font_sm.render(f"Rallies: {len(rally_results)}", True, TEXT_DIM), (px, py))
            py += 14
            screen.blit(font_sm.render(f"Avg rally: {avg_len:.1f} shots", True, TEXT_DIM), (px, py))
            py += 14
            screen.blit(font_sm.render(f"Longest: {max_len} shots", True, TEXT_DIM), (px, py))
            py += 18
            reasons = {}
            for r in rally_results:
                reasons[r.reason] = reasons.get(r.reason, 0) + 1
            for reason, count in sorted(reasons.items(), key=lambda x: -x[1])[:5]:
                screen.blit(font_sm.render(f"  {reason}: {count}", True, TEXT_DIM), (px, py))
                py += 14

        # Status
        py = WIN_H - 28
        state_txt = "PLAYING" if playing else "PAUSED"
        state_color = DETECTED_GREEN if playing else TEXT_DIM
        screen.blit(font_sm.render(state_txt, True, state_color), (px, py))
        screen.blit(font_sm.render(f"Auto:{'ON' if auto_mode else 'OFF'}", True, DETECTED_GREEN if auto_mode else TEXT_DIM), (px + 85, py))
        screen.blit(font_sm.render(f"View:{view}", True, TEXT_DIM), (px + 170, py))

        pygame.display.flip()

    pygame.quit()
