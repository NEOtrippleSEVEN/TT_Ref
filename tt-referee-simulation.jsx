import { useState, useRef, useEffect, useCallback, useMemo } from "react";

// ==================== CONSTANTS ====================
const TABLE = {
  length: 2.74, width: 1.525, height: 0.76, netHeight: 0.1525,
};
const BALL = {
  radius: 0.02, mass: 0.0027, restitution: 0.89, dragCoefficient: 0.4,
};
const GRAVITY = 9.81;

const CAMERA_PRESETS = {
  cheap: { label: "Budget USB (60fps)", fps: 60, res: [640, 480], shutter: 1 / 500, globalShutter: false, cost: 25 },
  mid: { label: "Mid-range (120fps)", fps: 120, res: [1280, 720], shutter: 1 / 1000, globalShutter: false, cost: 45 },
  arducam: { label: "Arducam OV9281 (200fps)", fps: 200, res: [1280, 800], shutter: 1 / 2000, globalShutter: true, cost: 75 },
};

// ==================== PHYSICS ENGINE ====================
function createBallState(vx, vy, vz, startX = -TABLE.length / 2 + 0.3, startZ = TABLE.height + 0.15) {
  return {
    pos: { x: startX, y: 0, z: startZ },
    vel: { x: vx, y: vy, z: vz },
    spin: { x: 0, y: 0, z: 0 },
    alive: true, t: 0,
  };
}

const SHOT_PRESETS = {
  slow_rally: { label: "Slow Rally (~30 km/h)", speed: 30, vx: 8.3, vy: 0.2, vz: 1.2 },
  medium_rally: { label: "Medium Rally (~50 km/h)", speed: 50, vx: 13.5, vy: 0.3, vz: 1.8 },
  fast_topspin: { label: "Fast Topspin (~80 km/h)", speed: 80, vx: 21, vy: 0.5, vz: 2.5 },
  smash: { label: "Smash (~100 km/h)", speed: 100, vx: 27, vy: 0.3, vz: 1.5 },
  net_clip: { label: "Net Clip", speed: 35, vx: 9.5, vy: 0.1, vz: 0.45 },
  edge_hit: { label: "Edge Hit", speed: 45, vx: 12, vy: 3.8, vz: 1.0 },
};

function stepPhysics(state, dt) {
  if (!state.alive) return state;
  const s = { ...state, pos: { ...state.pos }, vel: { ...state.vel } };
  s.vel.z -= GRAVITY * dt;
  const speed = Math.sqrt(s.vel.x ** 2 + s.vel.y ** 2 + s.vel.z ** 2);
  const drag = 0.5 * 1.225 * BALL.dragCoefficient * Math.PI * BALL.radius ** 2 * speed;
  if (speed > 0) {
    s.vel.x -= (drag * s.vel.x / speed / BALL.mass) * dt;
    s.vel.y -= (drag * s.vel.y / speed / BALL.mass) * dt;
    s.vel.z -= (drag * s.vel.z / speed / BALL.mass) * dt;
  }
  s.pos.x += s.vel.x * dt;
  s.pos.y += s.vel.y * dt;
  s.pos.z += s.vel.z * dt;
  s.t += dt;
  return s;
}

function detectCollisions(prev, curr) {
  const events = [];
  const halfL = TABLE.length / 2;
  const halfW = TABLE.width / 2;

  // Table bounce
  if (prev.pos.z > TABLE.height + BALL.radius && curr.pos.z <= TABLE.height + BALL.radius) {
    if (Math.abs(curr.pos.x) <= halfL && Math.abs(curr.pos.y) <= halfW) {
      curr.pos.z = TABLE.height + BALL.radius;
      curr.vel.z = -curr.vel.z * BALL.restitution;
      curr.vel.x *= 0.95;
      curr.vel.y *= 0.95;
      const side = curr.pos.x < 0 ? "left" : "right";
      const isEdge = Math.abs(Math.abs(curr.pos.x) - halfL) < 0.03 || Math.abs(Math.abs(curr.pos.y) - halfW) < 0.03;
      events.push({ type: "bounce", side, isEdge, pos: { ...curr.pos }, t: curr.t });
    }
  }

  // Net collision
  if (prev.pos.x < 0 && curr.pos.x >= 0 && curr.pos.z < TABLE.height + TABLE.netHeight + BALL.radius) {
    if (Math.abs(curr.pos.y) <= halfW + 0.1525) {
      if (curr.pos.z >= TABLE.height + BALL.radius) {
        curr.vel.x *= 0.3;
        curr.vel.z += 0.5;
        events.push({ type: "net", pos: { ...curr.pos }, t: curr.t });
      } else {
        curr.vel.x = -curr.vel.x * 0.2;
        curr.vel.z = Math.abs(curr.vel.z) * 0.3;
        events.push({ type: "net_stop", pos: { ...curr.pos }, t: curr.t });
      }
    }
  }

  // Floor / out of bounds
  if (curr.pos.z < BALL.radius) {
    const onTable = Math.abs(curr.pos.x) <= halfL && Math.abs(curr.pos.y) <= halfW;
    if (!onTable) {
      events.push({ type: "out", pos: { ...curr.pos }, t: curr.t });
      curr.alive = false;
    } else {
      curr.pos.z = BALL.radius;
      curr.vel.z = -curr.vel.z * 0.5;
    }
  }

  // Way off the table
  if (Math.abs(curr.pos.x) > halfL + 1.5 || Math.abs(curr.pos.y) > halfW + 1.5) {
    events.push({ type: "out", pos: { ...curr.pos }, t: curr.t });
    curr.alive = false;
  }

  return events;
}

function simulateTrajectory(shotKey) {
  const shot = SHOT_PRESETS[shotKey];
  let state = createBallState(shot.vx, shot.vy, shot.vz);
  const dt = 0.001;
  const positions = [{ ...state.pos, t: 0 }];
  const allEvents = [];
  let maxBounces = 0;

  for (let i = 0; i < 5000 && state.alive; i++) {
    const prev = { ...state, pos: { ...state.pos } };
    state = stepPhysics(state, dt);
    const events = detectCollisions(prev, state);
    allEvents.push(...events);
    maxBounces += events.filter(e => e.type === "bounce").length;
    positions.push({ ...state.pos, t: state.t });
    if (maxBounces > 4) { state.alive = false; }
  }
  return { positions, events: allEvents, duration: state.t };
}

// ==================== CAMERA SIMULATION ====================
function simulateCamera(positions, fps, shutterSpeed, resolution, globalShutter) {
  const frameInterval = 1 / fps;
  const frames = [];
  let frameNum = 0;
  const pixPerMeter = resolution[0] / (TABLE.length + 1);
  const ballPx = BALL.radius * 2 * pixPerMeter;

  for (let t = 0; t < positions[positions.length - 1].t; t += frameInterval) {
    const idx = positions.findIndex(p => p.t >= t);
    if (idx < 0) break;
    const p = positions[idx];
    const prevIdx = Math.max(0, idx - Math.floor(positions.length * frameInterval / positions[positions.length - 1].t));
    const prevP = positions[prevIdx];
    const dx = p.x - prevP.x;
    const dz = p.z - prevP.z;
    const motionPx = Math.sqrt(dx * dx + dz * dz) * pixPerMeter;
    const blurPx = globalShutter ? motionPx * 0.1 : motionPx * (1 / (shutterSpeed * fps));
    const effectiveBallSize = Math.max(ballPx - blurPx * 0.5, 1);
    let confidence;
    if (effectiveBallSize < 2) confidence = 0.1;
    else if (effectiveBallSize < 4) confidence = 0.4;
    else if (blurPx > ballPx * 3) confidence = 0.2;
    else if (blurPx > ballPx * 1.5) confidence = 0.6;
    else confidence = Math.min(0.99, 0.7 + effectiveBallSize / 50);

    const detected = Math.random() < confidence;
    frames.push({
      frameNum: frameNum++,
      t,
      pos: detected ? { ...p } : null,
      confidence,
      blurPx,
      detected,
    });
  }
  return frames;
}

function analyzeAccuracy(positions, events) {
  const results = {};
  for (const [key, preset] of Object.entries(CAMERA_PRESETS)) {
    const frames = simulateCamera(positions, preset.fps, preset.shutter, preset.res, preset.globalShutter);
    const detected = frames.filter(f => f.detected).length;
    const avgConf = frames.reduce((s, f) => s + f.confidence, 0) / frames.length;
    const avgBlur = frames.reduce((s, f) => s + f.blurPx, 0) / frames.length;
    const bounces = events.filter(e => e.type === "bounce");
    let bouncesDetected = 0;
    for (const b of bounces) {
      const nearby = frames.filter(f => Math.abs(f.t - b.t) < 2 / preset.fps && f.detected);
      if (nearby.length >= 2) bouncesDetected++;
    }
    results[key] = {
      ...preset, totalFrames: frames.length, detectedFrames: detected,
      detectionRate: (detected / frames.length * 100).toFixed(1),
      avgConfidence: (avgConf * 100).toFixed(1),
      avgBlurPx: avgBlur.toFixed(1),
      bouncesTotal: bounces.length,
      bouncesDetected,
      frames,
    };
  }
  return results;
}

// ==================== SCORING ENGINE ====================
function createMatch() {
  return { p1: 0, p2: 0, server: 1, serveCount: 0, history: [], deuce: false, winner: null };
}
function scorePoint(match, side) {
  const m = { ...match, history: [...match.history] };
  if (side === "left") m.p2++;
  else m.p1++;
  m.history.push({ p1: m.p1, p2: m.p2, server: m.server, side });
  m.serveCount++;
  m.deuce = m.p1 >= 10 && m.p2 >= 10;
  const interval = m.deuce ? 1 : 2;
  if (m.serveCount >= interval) { m.server = m.server === 1 ? 2 : 1; m.serveCount = 0; }
  if (m.p1 >= 11 && m.p1 - m.p2 >= 2) m.winner = 1;
  if (m.p2 >= 11 && m.p2 - m.p1 >= 2) m.winner = 2;
  return m;
}

// ==================== DRAWING HELPERS ====================
function drawTable(ctx, w, h, view) {
  const margin = 40;
  if (view === "top") {
    const tw = w - margin * 2;
    const th = tw * (TABLE.width / TABLE.length);
    const tx = margin;
    const ty = (h - th) / 2;
    ctx.fillStyle = "#1a5c2d";
    ctx.fillRect(tx, ty, tw, th);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 2;
    ctx.strokeRect(tx, ty, tw, th);
    ctx.beginPath(); ctx.moveTo(tx + tw / 2, ty); ctx.lineTo(tx + tw / 2, ty + th); ctx.stroke();
    ctx.setLineDash([6, 4]);
    ctx.beginPath(); ctx.moveTo(tx, ty + th / 2); ctx.lineTo(tx + tw, ty + th / 2); ctx.stroke();
    ctx.setLineDash([]);
    ctx.fillStyle = "#cccccc";
    ctx.fillRect(tx + tw / 2 - 1, ty - 8, 2, th + 16);
    return { tx, ty, tw, th, scale: tw / TABLE.length };
  } else {
    const tw = w - margin * 2;
    const tSurf = h * 0.65;
    const tx = margin;
    ctx.fillStyle = "#5c3a1a";
    ctx.fillRect(tx, tSurf, tw, 6);
    ctx.fillStyle = "#1a5c2d";
    ctx.fillRect(tx, tSurf - 3, tw, 3);
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = 1;
    ctx.strokeRect(tx, tSurf - 3, tw, 3);
    const netX = tx + tw / 2;
    const netH = TABLE.netHeight / TABLE.length * tw;
    ctx.strokeStyle = "#cccccc";
    ctx.lineWidth = 2;
    ctx.beginPath(); ctx.moveTo(netX, tSurf); ctx.lineTo(netX, tSurf - netH - 3); ctx.stroke();
    ctx.strokeStyle = "#aaaaaa";
    ctx.lineWidth = 1;
    ctx.setLineDash([2, 2]);
    ctx.beginPath(); ctx.moveTo(netX - 3, tSurf - netH - 3); ctx.lineTo(netX + 3, tSurf - netH - 3); ctx.stroke();
    ctx.setLineDash([]);
    return { tx, tSurf, tw, scale: tw / TABLE.length, netH };
  }
}

function worldToTop(pos, td) {
  const x = td.tx + (pos.x + TABLE.length / 2) / TABLE.length * td.tw;
  const y = td.ty + (pos.y + TABLE.width / 2) / TABLE.width * td.th;
  return { x, y };
}

function worldToSide(pos, td) {
  const x = td.tx + (pos.x + TABLE.length / 2) / TABLE.length * td.tw;
  const y = td.tSurf - (pos.z - 0) / TABLE.length * td.tw;
  return { x, y };
}

// ==================== MAIN COMPONENT ====================
const ACCENT = "#e94560";
const BG_DARK = "#0f0f1a";
const CARD_BG = "#1a1a2e";
const SURFACE = "#16213e";

export default function TTRefereeSim() {
  const canvasRef = useRef(null);
  const animRef = useRef(null);
  const [shotKey, setShotKey] = useState("medium_rally");
  const [cameraKey, setCameraKey] = useState("arducam");
  const [view, setView] = useState("top");
  const [playing, setPlaying] = useState(false);
  const [playT, setPlayT] = useState(0);
  const [showTrail, setShowTrail] = useState(true);
  const [showCameraFrames, setShowCameraFrames] = useState(true);
  const [match, setMatch] = useState(createMatch);
  const [tab, setTab] = useState("sim");

  const simData = useMemo(() => {
    const { positions, events, duration } = simulateTrajectory(shotKey);
    const cameraResults = analyzeAccuracy(positions, events);
    return { positions, events, duration, cameraResults };
  }, [shotKey]);

  const currentCamera = CAMERA_PRESETS[cameraKey];
  const camResult = simData.cameraResults[cameraKey];

  const draw = useCallback((t) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = "#0a0a15";
    ctx.fillRect(0, 0, w, h);

    const td = drawTable(ctx, w, h, view);
    const toScreen = view === "top" ? (p) => worldToTop(p, td) : (p) => worldToSide(p, td);

    // Trail
    if (showTrail) {
      const trailEnd = playing ? simData.positions.findIndex(p => p.t >= t) : simData.positions.length;
      ctx.beginPath();
      for (let i = 0; i < trailEnd && i < simData.positions.length; i++) {
        const sp = toScreen(simData.positions[i]);
        if (i === 0) ctx.moveTo(sp.x, sp.y);
        else ctx.lineTo(sp.x, sp.y);
      }
      ctx.strokeStyle = "rgba(233,69,96,0.35)";
      ctx.lineWidth = 2;
      ctx.stroke();
    }

    // Camera frame dots
    if (showCameraFrames && camResult) {
      for (const f of camResult.frames) {
        if (playing && f.t > t) break;
        if (f.pos) {
          const sp = toScreen(f.pos);
          ctx.beginPath();
          ctx.arc(sp.x, sp.y, 3, 0, Math.PI * 2);
          ctx.fillStyle = f.detected ? "rgba(40,167,69,0.7)" : "rgba(255,193,7,0.5)";
          ctx.fill();
        }
      }
    }

    // Current ball
    const idx = playing
      ? simData.positions.findIndex(p => p.t >= t)
      : simData.positions.length - 1;
    if (idx >= 0 && idx < simData.positions.length) {
      const bp = toScreen(simData.positions[idx]);
      const grad = ctx.createRadialGradient(bp.x - 2, bp.y - 2, 1, bp.x, bp.y, 8);
      grad.addColorStop(0, "#ffffff");
      grad.addColorStop(0.5, "#ff8800");
      grad.addColorStop(1, "#e94560");
      ctx.beginPath();
      ctx.arc(bp.x, bp.y, 7, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5;
      ctx.stroke();
    }

    // Event markers
    for (const e of simData.events) {
      if (playing && e.t > t) break;
      const ep = toScreen(e.pos);
      ctx.font = "bold 11px monospace";
      if (e.type === "bounce") {
        ctx.fillStyle = e.isEdge ? "#ff6b6b" : "#4ecdc4";
        ctx.fillText(e.isEdge ? "EDGE" : "BOUNCE", ep.x - 20, ep.y - 12);
      } else if (e.type === "net" || e.type === "net_stop") {
        ctx.fillStyle = "#ffd93d";
        ctx.fillText("NET", ep.x - 10, ep.y - 12);
      } else if (e.type === "out") {
        ctx.fillStyle = "#ff6b6b";
        ctx.fillText("OUT", ep.x - 10, ep.y - 12);
      }
    }

    // Info overlay
    ctx.fillStyle = "rgba(0,0,0,0.6)";
    ctx.fillRect(8, 8, 200, 50);
    ctx.fillStyle = "#aaa";
    ctx.font = "11px monospace";
    ctx.fillText(`Shot: ${SHOT_PRESETS[shotKey].label}`, 14, 24);
    ctx.fillText(`Camera: ${currentCamera.label}`, 14, 38);
    ctx.fillText(`Time: ${(playing ? t : simData.duration).toFixed(3)}s`, 14, 52);
  }, [view, shotKey, cameraKey, showTrail, showCameraFrames, simData, camResult, currentCamera, playing]);

  useEffect(() => {
    if (!playing) { draw(0); return; }
    let start = null;
    const speed = 0.3;
    const animate = (ts) => {
      if (!start) start = ts;
      const elapsed = ((ts - start) / 1000) * speed;
      if (elapsed >= simData.duration) { setPlaying(false); draw(simData.duration); return; }
      setPlayT(elapsed);
      draw(elapsed);
      animRef.current = requestAnimationFrame(animate);
    };
    animRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(animRef.current);
  }, [playing, draw, simData.duration]);

  useEffect(() => { if (!playing) draw(0); }, [shotKey, cameraKey, view, showTrail, showCameraFrames, draw, playing]);

  // Score from sim events
  const handleScoreFromSim = () => {
    const bounces = simData.events.filter(e => e.type === "bounce");
    const lastBounce = bounces[bounces.length - 1];
    if (lastBounce) {
      setMatch(prev => scorePoint(prev, lastBounce.side));
    }
  };

  const resetMatch = () => setMatch(createMatch());

  const btnClass = "px-3 py-1.5 rounded text-xs font-semibold transition-all cursor-pointer ";
  const activeBtn = btnClass + "bg-[#e94560] text-white shadow-lg shadow-[#e9456040]";
  const inactiveBtn = btnClass + "bg-[#16213e] text-gray-300 hover:bg-[#1f2b47]";

  return (
    <div style={{ background: BG_DARK, color: "#e0e0e0", minHeight: "100vh", fontFamily: "'JetBrains Mono', 'SF Mono', 'Fira Code', monospace" }}>
      {/* Header */}
      <div style={{ background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)", borderBottom: "2px solid #e94560", padding: "12px 20px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#e94560", boxShadow: "0 0 10px #e94560" }} />
          <span style={{ fontSize: 16, fontWeight: 700, letterSpacing: 1 }}>TT REFEREE</span>
          <span style={{ fontSize: 11, color: "#888", marginLeft: 4 }}>AI Simulation v0.1</span>
        </div>
        <div style={{ display: "flex", gap: 4 }}>
          {["sim", "analysis", "score"].map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={tab === t ? activeBtn : inactiveBtn}>
              {t === "sim" ? "⚡ Simulation" : t === "analysis" ? "📊 Analysis" : "🏓 Score"}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: 16, maxWidth: 960, margin: "0 auto" }}>
        {/* ===== SIMULATION TAB ===== */}
        {tab === "sim" && (
          <>
            {/* Controls */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, marginBottom: 12 }}>
              <div style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: "1px solid #2a2a4a" }}>
                <div style={{ fontSize: 10, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>Shot Type</div>
                <select value={shotKey} onChange={e => { setShotKey(e.target.value); setPlaying(false); }}
                  style={{ width: "100%", background: SURFACE, color: "#e0e0e0", border: "1px solid #333", borderRadius: 4, padding: "6px 8px", fontSize: 12 }}>
                  {Object.entries(SHOT_PRESETS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
              </div>
              <div style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: "1px solid #2a2a4a" }}>
                <div style={{ fontSize: 10, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>Camera Preset</div>
                <select value={cameraKey} onChange={e => setCameraKey(e.target.value)}
                  style={{ width: "100%", background: SURFACE, color: "#e0e0e0", border: "1px solid #333", borderRadius: 4, padding: "6px 8px", fontSize: 12 }}>
                  {Object.entries(CAMERA_PRESETS).map(([k, v]) => <option key={k} value={k}>{v.label}</option>)}
                </select>
              </div>
              <div style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: "1px solid #2a2a4a" }}>
                <div style={{ fontSize: 10, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>View</div>
                <div style={{ display: "flex", gap: 4 }}>
                  <button onClick={() => setView("top")} className={view === "top" ? activeBtn : inactiveBtn}>Top-Down</button>
                  <button onClick={() => setView("side")} className={view === "side" ? activeBtn : inactiveBtn}>Side</button>
                </div>
              </div>
            </div>

            {/* Canvas */}
            <div style={{ background: CARD_BG, borderRadius: 8, border: "1px solid #2a2a4a", overflow: "hidden", marginBottom: 12 }}>
              <canvas ref={canvasRef} width={920} height={380}
                style={{ width: "100%", display: "block" }} />
              <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "8px 12px", borderTop: "1px solid #2a2a4a", background: "#12121f" }}>
                <button onClick={() => setPlaying(!playing)} className={activeBtn}>
                  {playing ? "⏸ Pause" : "▶ Play"}
                </button>
                <button onClick={() => { setPlaying(false); draw(0); }} className={inactiveBtn}>⟲ Reset</button>
                <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, cursor: "pointer", marginLeft: 12 }}>
                  <input type="checkbox" checked={showTrail} onChange={e => setShowTrail(e.target.checked)} /> Trail
                </label>
                <label style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 11, cursor: "pointer" }}>
                  <input type="checkbox" checked={showCameraFrames} onChange={e => setShowCameraFrames(e.target.checked)} /> Camera frames
                </label>
                <div style={{ flex: 1 }} />
                <span style={{ fontSize: 10, color: "#666" }}>
                  Green dots = detected frames | Speed: {SHOT_PRESETS[shotKey].speed} km/h
                </span>
              </div>
            </div>

            {/* Quick Stats Row */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 12 }}>
              {[
                { label: "Detection Rate", value: `${camResult?.detectionRate}%`, color: parseFloat(camResult?.detectionRate) > 85 ? "#28a745" : parseFloat(camResult?.detectionRate) > 60 ? "#ffc107" : "#dc3545" },
                { label: "Avg Confidence", value: `${camResult?.avgConfidence}%`, color: "#4ecdc4" },
                { label: "Bounces Detected", value: `${camResult?.bouncesDetected}/${camResult?.bouncesTotal}`, color: camResult?.bouncesDetected === camResult?.bouncesTotal ? "#28a745" : "#ffc107" },
                { label: "Avg Motion Blur", value: `${camResult?.avgBlurPx} px`, color: parseFloat(camResult?.avgBlurPx) < 5 ? "#28a745" : "#ffc107" },
              ].map((s, i) => (
                <div key={i} style={{ background: CARD_BG, borderRadius: 8, padding: "10px 14px", border: "1px solid #2a2a4a", textAlign: "center" }}>
                  <div style={{ fontSize: 22, fontWeight: 700, color: s.color }}>{s.value}</div>
                  <div style={{ fontSize: 9, color: "#888", marginTop: 2, textTransform: "uppercase", letterSpacing: 0.5 }}>{s.label}</div>
                </div>
              ))}
            </div>

            {/* Events Log */}
            <div style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: "1px solid #2a2a4a" }}>
              <div style={{ fontSize: 10, color: "#888", marginBottom: 6, textTransform: "uppercase", letterSpacing: 1 }}>Events Detected</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {simData.events.map((e, i) => (
                  <span key={i} style={{
                    padding: "3px 8px", borderRadius: 4, fontSize: 11, fontWeight: 600,
                    background: e.type === "bounce" ? (e.isEdge ? "#5c2020" : "#1a3a2a") : e.type.startsWith("net") ? "#3a3520" : "#3a2020",
                    color: e.type === "bounce" ? (e.isEdge ? "#ff8a8a" : "#4ecdc4") : e.type.startsWith("net") ? "#ffd93d" : "#ff6b6b",
                  }}>
                    {e.type === "bounce" ? `${e.isEdge ? "EDGE" : "BOUNCE"} (${e.side})` : e.type.toUpperCase()} @ {e.t.toFixed(3)}s
                  </span>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ===== ANALYSIS TAB ===== */}
        {tab === "analysis" && (
          <>
            <div style={{ background: CARD_BG, borderRadius: 8, padding: 16, border: "1px solid #2a2a4a", marginBottom: 12 }}>
              <div style={{ fontSize: 14, fontWeight: 700, marginBottom: 4 }}>📊 Camera Comparison: {SHOT_PRESETS[shotKey].label}</div>
              <div style={{ fontSize: 11, color: "#888", marginBottom: 12 }}>Same trajectory analyzed at three different camera configurations</div>

              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                <thead>
                  <tr style={{ borderBottom: "2px solid #e94560" }}>
                    {["Camera", "FPS", "Resolution", "Detection %", "Confidence", "Bounces", "Blur (px)", "Cost"].map(h => (
                      <th key={h} style={{ padding: "6px 8px", textAlign: "left", color: "#aaa", fontSize: 10, textTransform: "uppercase" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(simData.cameraResults).map(([k, r]) => (
                    <tr key={k} style={{ borderBottom: "1px solid #2a2a4a", background: k === "arducam" ? "#1a2a1a" : "transparent" }}>
                      <td style={{ padding: "8px", fontWeight: 600, color: k === "arducam" ? "#4ecdc4" : "#ccc" }}>{r.label}</td>
                      <td style={{ padding: "8px" }}>{r.fps}</td>
                      <td style={{ padding: "8px", fontSize: 10 }}>{r.res[0]}×{r.res[1]}</td>
                      <td style={{ padding: "8px", fontWeight: 700, color: parseFloat(r.detectionRate) > 85 ? "#28a745" : parseFloat(r.detectionRate) > 60 ? "#ffc107" : "#dc3545" }}>
                        {r.detectionRate}%
                      </td>
                      <td style={{ padding: "8px" }}>{r.avgConfidence}%</td>
                      <td style={{ padding: "8px", color: r.bouncesDetected === r.bouncesTotal ? "#28a745" : "#ffc107" }}>
                        {r.bouncesDetected}/{r.bouncesTotal}
                      </td>
                      <td style={{ padding: "8px", color: parseFloat(r.avgBlurPx) < 5 ? "#28a745" : "#ffc107" }}>{r.avgBlurPx}</td>
                      <td style={{ padding: "8px" }}>€{r.cost}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Visual FPS Comparison */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 12 }}>
              {Object.entries(simData.cameraResults).map(([k, r]) => {
                const total = r.totalFrames;
                const detected = r.detectedFrames;
                return (
                  <div key={k} style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: k === "arducam" ? "2px solid #4ecdc4" : "1px solid #2a2a4a" }}>
                    <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 8, color: k === "arducam" ? "#4ecdc4" : "#ccc" }}>
                      {r.fps} FPS {k === "arducam" ? "★ RECOMMENDED" : ""}
                    </div>
                    {/* Frame strip visualization */}
                    <div style={{ display: "flex", flexWrap: "wrap", gap: 1, marginBottom: 8 }}>
                      {r.frames.slice(0, 60).map((f, i) => (
                        <div key={i} style={{
                          width: 4, height: 12, borderRadius: 1,
                          background: f.detected ? "#28a745" : "#dc3545",
                          opacity: 0.8,
                        }} />
                      ))}
                    </div>
                    <div style={{ fontSize: 10, color: "#888" }}>
                      <span style={{ color: "#28a745" }}>■</span> detected &nbsp;
                      <span style={{ color: "#dc3545" }}>■</span> missed
                    </div>
                    <div style={{ fontSize: 18, fontWeight: 700, marginTop: 6, color: k === "arducam" ? "#28a745" : parseFloat(r.detectionRate) > 60 ? "#ffc107" : "#dc3545" }}>
                      {r.detectionRate}%
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Key Insight Box */}
            <div style={{ background: "linear-gradient(135deg, #1a2a1a 0%, #162a1e 100%)", borderRadius: 8, padding: 16, border: "1px solid #28a745", marginBottom: 12 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: "#4ecdc4", marginBottom: 6 }}>💡 Key Finding</div>
              <div style={{ fontSize: 12, lineHeight: 1.6 }}>
                At <strong style={{ color: "#e94560" }}>{SHOT_PRESETS[shotKey].speed} km/h</strong>, the ball travels{" "}
                <strong>{(SHOT_PRESETS[shotKey].speed / 3.6 / 60).toFixed(2)}m</strong> between frames at 60fps vs{" "}
                <strong>{(SHOT_PRESETS[shotKey].speed / 3.6 / 200).toFixed(2)}m</strong> at 200fps.
                The Arducam OV9281's global shutter eliminates motion blur entirely, maintaining{" "}
                <strong style={{ color: "#28a745" }}>{simData.cameraResults.arducam?.detectionRate}%</strong> detection
                vs the budget camera's <strong style={{ color: "#dc3545" }}>{simData.cameraResults.cheap?.detectionRate}%</strong>.
                For €50 more, you get {(parseFloat(simData.cameraResults.arducam?.detectionRate) - parseFloat(simData.cameraResults.cheap?.detectionRate)).toFixed(1)}% higher accuracy.
              </div>
            </div>

            {/* Ball travel between frames */}
            <div style={{ background: CARD_BG, borderRadius: 8, padding: 16, border: "1px solid #2a2a4a" }}>
              <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Ball Distance Between Frames (at {SHOT_PRESETS[shotKey].speed} km/h)</div>
              {Object.entries(CAMERA_PRESETS).map(([k, p]) => {
                const dist = SHOT_PRESETS[shotKey].speed / 3.6 / p.fps;
                const pct = dist / 0.5 * 100;
                return (
                  <div key={k} style={{ marginBottom: 8 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                      <span>{p.fps} FPS</span>
                      <span style={{ fontWeight: 700 }}>{(dist * 100).toFixed(1)} cm</span>
                    </div>
                    <div style={{ height: 8, background: "#0a0a15", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{
                        height: "100%", borderRadius: 4, width: `${Math.min(pct, 100)}%`,
                        background: pct < 20 ? "#28a745" : pct < 50 ? "#ffc107" : "#dc3545",
                      }} />
                    </div>
                  </div>
                );
              })}
              <div style={{ fontSize: 10, color: "#666", marginTop: 6 }}>Ball diameter: 4cm. At 60fps on a smash, the ball moves 46cm between frames — invisible to tracking.</div>
            </div>
          </>
        )}

        {/* ===== SCORE TAB ===== */}
        {tab === "score" && (
          <>
            {/* Scoreboard */}
            <div style={{
              background: "linear-gradient(135deg, #1a1a2e 0%, #0f0f1a 100%)",
              borderRadius: 12, padding: 24, border: "2px solid #e94560",
              textAlign: "center", marginBottom: 16
            }}>
              {match.winner && (
                <div style={{ fontSize: 14, color: "#ffd93d", fontWeight: 700, marginBottom: 8 }}>
                  🏆 Player {match.winner} Wins!
                </div>
              )}
              <div style={{ display: "flex", justifyContent: "center", alignItems: "center", gap: 32 }}>
                <div>
                  <div style={{ fontSize: 10, color: "#888", textTransform: "uppercase", letterSpacing: 1 }}>
                    Player 1 {match.server === 1 ? "🏓" : ""}
                  </div>
                  <div style={{ fontSize: 56, fontWeight: 700, color: "#4ecdc4", lineHeight: 1 }}>{match.p1}</div>
                </div>
                <div style={{ fontSize: 24, color: "#444" }}>—</div>
                <div>
                  <div style={{ fontSize: 10, color: "#888", textTransform: "uppercase", letterSpacing: 1 }}>
                    Player 2 {match.server === 2 ? "🏓" : ""}
                  </div>
                  <div style={{ fontSize: 56, fontWeight: 700, color: ACCENT, lineHeight: 1 }}>{match.p2}</div>
                </div>
              </div>
              {match.deuce && <div style={{ marginTop: 8, color: "#ffd93d", fontSize: 12, fontWeight: 600 }}>⚡ DEUCE — Serve alternates every point</div>}
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 16 }}>
              <button onClick={() => setMatch(prev => scorePoint(prev, "right"))}
                style={{ padding: "12px", borderRadius: 8, background: "#1a3a2a", border: "1px solid #28a745", color: "#4ecdc4", fontWeight: 700, cursor: "pointer", fontSize: 13 }}>
                Point P1 (Right)
              </button>
              <button onClick={handleScoreFromSim}
                style={{ padding: "12px", borderRadius: 8, background: SURFACE, border: `1px solid ${ACCENT}`, color: ACCENT, fontWeight: 700, cursor: "pointer", fontSize: 13 }}>
                Score from Sim ⚡
              </button>
              <button onClick={() => setMatch(prev => scorePoint(prev, "left"))}
                style={{ padding: "12px", borderRadius: 8, background: "#3a2020", border: "1px solid #dc3545", color: "#ff8a8a", fontWeight: 700, cursor: "pointer", fontSize: 13 }}>
                Point P2 (Left)
              </button>
            </div>

            <button onClick={resetMatch} className={inactiveBtn} style={{ marginBottom: 16, width: "100%" }}>
              Reset Match
            </button>

            {/* Match History */}
            {match.history.length > 0 && (
              <div style={{ background: CARD_BG, borderRadius: 8, padding: 12, border: "1px solid #2a2a4a" }}>
                <div style={{ fontSize: 10, color: "#888", marginBottom: 8, textTransform: "uppercase", letterSpacing: 1 }}>Point History</div>
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4 }}>
                  {match.history.map((h, i) => (
                    <div key={i} style={{
                      padding: "4px 8px", borderRadius: 4, fontSize: 11,
                      background: h.side === "right" ? "#1a3a2a" : "#3a2020",
                      color: h.side === "right" ? "#4ecdc4" : "#ff8a8a",
                    }}>
                      {h.p1}-{h.p2}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
