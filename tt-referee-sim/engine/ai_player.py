"""AI player engine — two players with different playstyles for simulated matches.

Spin values use real rad/s units:
  - Beginner: 50-200 rad/s
  - Intermediate: 200-400 rad/s
  - Pro: 400-700 rad/s
  - Elite: 600-900 rad/s
"""

import random
import math

from engine.types import BallState, BounceEvent, Vec3
from engine import table


# Player playstyle presets
PLAYSTYLES = {
    "aggressive": {
        "label": "Aggressive",
        "skill": 0.80,
        "power": 0.90,
        "consistency": 0.65,
        "spin_ability": 0.70,
        "speed": 0.85,
        "preferred_shots": ["smash", "fast_topspin", "medium_rally"],
    },
    "defensive": {
        "label": "Defensive",
        "skill": 0.75,
        "power": 0.50,
        "consistency": 0.90,
        "spin_ability": 0.80,
        "speed": 0.70,
        "preferred_shots": ["backspin_chop", "slow_rally", "medium_rally"],
    },
    "allround": {
        "label": "All-Round",
        "skill": 0.78,
        "power": 0.70,
        "consistency": 0.78,
        "spin_ability": 0.75,
        "speed": 0.78,
        "preferred_shots": ["medium_rally", "fast_topspin", "slow_rally"],
    },
    "beginner": {
        "label": "Beginner",
        "skill": 0.45,
        "power": 0.40,
        "consistency": 0.40,
        "spin_ability": 0.20,
        "speed": 0.50,
        "preferred_shots": ["slow_rally", "slow_rally", "medium_rally"],
    },
    "pro": {
        "label": "Professional",
        "skill": 0.95,
        "power": 0.85,
        "consistency": 0.92,
        "spin_ability": 0.95,
        "speed": 0.92,
        "preferred_shots": ["fast_topspin", "smash", "medium_rally", "backspin_chop"],
    },
}

# Speed and trajectory parameters for each shot type (base_vx, base_vz_down)
_SHOT_PARAMS = {
    "slow_rally":     (8, 0.5),
    "medium_rally":   (13, 1.0),
    "fast_topspin":   (20, 2.0),
    "smash":          (26, 3.5),
    "backspin_chop":  (8, 0.8),
}

# Spin ranges in rad/s for each shot type (min, max) — realistic values
_SHOT_SPIN = {
    "slow_rally":     (50, 150),       # light topspin
    "medium_rally":   (200, 400),      # intermediate topspin
    "fast_topspin":   (400, 700),      # heavy topspin
    "smash":          (50, 150),       # flat hit, minimal spin
    "backspin_chop":  (-500, -150),    # backspin (negative = backspin)
}


class AIPlayer:
    """An AI table tennis player that generates return shots."""

    def __init__(self, name: str, playstyle: str, side: int):
        """Create a player.

        Args:
            name: Display name.
            playstyle: Key from PLAYSTYLES.
            side: 1 (left, x<0) or 2 (right, x>0).
        """
        self.name = name
        self.side = side
        preset = PLAYSTYLES[playstyle]
        self.playstyle = playstyle
        self.label = preset["label"]
        self.skill = preset["skill"]
        self.power = preset["power"]
        self.consistency = preset["consistency"]
        self.spin_ability = preset["spin_ability"]
        self.speed = preset["speed"]
        self.preferred_shots = preset["preferred_shots"]

    def can_reach(self, ball_pos: Vec3, ball_vel: Vec3) -> bool:
        """Whether the player can reach the incoming ball."""
        speed = ball_vel.magnitude()
        difficulty = min(1.0, speed / 35.0)
        reach_prob = self.speed * (1.0 - difficulty * 0.5)
        off_center = abs(ball_pos.y) / (table.TABLE_WIDTH / 2)
        reach_prob -= off_center * 0.15
        reach_prob = max(0.1, min(0.99, reach_prob))
        return random.random() < reach_prob

    def calculate_return(self, incoming_bounce: BounceEvent) -> BallState:
        """Calculate a return shot from an incoming bounce on this player's side.

        Uses analytical trajectory calculation to ensure net clearance.
        Returns a BallState ready for physics.simulate().
        """
        my_half = -1 if self.side == 1 else 1
        target_dir = -my_half  # Hit toward opposite side

        # Pick shot type based on playstyle + randomness
        shot_type = random.choice(self.preferred_shots)

        base_vx, _ = _SHOT_PARAMS.get(shot_type, (12, 1.0))

        # Scale by power with randomness
        power_noise = random.gauss(1.0, 0.08)
        vx = base_vx * self.power * power_noise * target_dir

        # Start position: near the bounce point, slightly behind
        start_x = incoming_bounce.pos.x + my_half * random.uniform(0.1, 0.3)
        if self.side == 1:
            start_x = min(start_x, -0.2)
        else:
            start_x = max(start_x, 0.2)

        start_y = incoming_bounce.pos.y + random.gauss(0, 0.05)
        start_z = table.TABLE_HEIGHT + random.uniform(0.25, 0.50)

        # Calculate vz to land on opponent's side (analytical, ignoring drag/Magnus)
        half_table = table.TABLE_LENGTH / 2
        target_x = target_dir * random.uniform(0.3, half_table - 0.1)
        dx = abs(target_x - start_x)
        t_land = dx / max(abs(vx), 1.0)
        target_land_z = table.TABLE_HEIGHT + table.BALL_RADIUS
        vz = (target_land_z - start_z + 0.5 * table.GRAVITY * t_land ** 2) / t_land

        # Ensure net clearance (ball must pass above net at x=0)
        net_top = table.TABLE_HEIGHT + table.NET_HEIGHT
        dist_to_net = abs(start_x)
        if dist_to_net > 0.05:
            t_net = dist_to_net / max(abs(vx), 1.0)
            z_at_net = start_z + vz * t_net - 0.5 * table.GRAVITY * t_net ** 2
            net_margin = 0.05  # 5cm safety margin
            if z_at_net < net_top + net_margin:
                vz_min = (net_top + net_margin - start_z + 0.5 * table.GRAVITY * t_net ** 2) / t_net
                vz = max(vz, vz_min)

        # Lateral aim: slightly random
        vy = random.gauss(0, 0.3 + (1 - self.consistency) * 1.0)

        # Spin in real rad/s, based on shot type and ability
        spin_min, spin_max = _SHOT_SPIN.get(shot_type, (100, 300))
        base_spin = random.uniform(spin_min, spin_max)
        spin_y = base_spin * self.spin_ability * (1 if target_dir > 0 else -1)

        # Sidespin occasionally
        spin_x = 0.0
        if random.random() < 0.15:
            spin_x = random.gauss(0, 100) * self.spin_ability

        # Consistency check: bad shots go off-target
        if random.random() > self.consistency:
            vx *= random.uniform(0.7, 1.4)
            vy += random.gauss(0, 1.5)
            vz += random.gauss(0, 0.5)

        return BallState(
            pos=Vec3(start_x, start_y, start_z),
            vel=Vec3(vx, vy, vz),
            spin=Vec3(spin_x, spin_y, 0),
        )

    def generate_serve(self) -> BallState:
        """Generate a serve from this player's side.

        Uses analytical trajectory to ensure the ball bounces on server's half
        and clears the net. Serve speed is moderate (real serves rely on spin).

        ITTF rules:
        - Ball must bounce on server's side first, then cross net to receiver's side
        """
        my_half = -1 if self.side == 1 else 1
        target_dir = -my_half

        # Serve position: behind the table on player's side
        start_x = my_half * (table.TABLE_LENGTH / 2 + 0.1)
        start_y = random.gauss(0, 0.15)
        start_z = table.TABLE_HEIGHT + random.uniform(0.30, 0.50)

        # Serve speed: 3.8-5.2 m/s (realistic: serves rely on spin, not raw speed)
        base_speed = random.uniform(3.8, 5.2) * (0.9 + self.power * 0.1)
        vx = base_speed * target_dir

        # Target bounce: 40-65% from server's end line toward net
        # (not too close to net — ball needs room to arc over it)
        half_table = table.TABLE_LENGTH / 2
        bounce_frac = random.uniform(0.40, 0.65)
        bounce_x = my_half * (half_table - bounce_frac * half_table)

        # Calculate vz analytically to land at bounce_x
        dx = abs(bounce_x - start_x)
        t_bounce = dx / max(abs(vx), 1.0)
        target_z = table.TABLE_HEIGHT + table.BALL_RADIUS
        vz = (target_z - start_z + 0.5 * table.GRAVITY * t_bounce ** 2) / t_bounce

        # Small noise for variety
        vz += random.gauss(0, 0.15)
        vy = random.gauss(0, 0.3)

        # Serve spin (real values: ~195 rad/s average for pros)
        spin_y = random.uniform(100, 250) * self.spin_ability * target_dir
        if random.random() < 0.3:  # Sometimes backspin serve
            spin_y = -spin_y * 0.5
        spin_x = random.gauss(0, 60) * self.spin_ability

        # Serve consistency — occasional bad serve
        if random.random() > self.consistency * 1.1:
            vz += random.gauss(0, 0.5)
            vy += random.gauss(0, 0.6)

        return BallState(
            pos=Vec3(start_x, start_y, start_z),
            vel=Vec3(vx, vy, vz),
            spin=Vec3(spin_x, spin_y, 0),
        )
