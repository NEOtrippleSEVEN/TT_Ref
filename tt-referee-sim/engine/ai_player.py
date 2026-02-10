"""AI player engine — two players with different playstyles for simulated matches."""

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
        # Faster ball is harder to reach
        speed = ball_vel.magnitude()
        difficulty = min(1.0, speed / 35.0)  # 35 m/s is near max TT speed
        reach_prob = self.speed * (1.0 - difficulty * 0.5)
        # Ball far from center is harder
        if self.side == 1:
            off_center = abs(ball_pos.y) / (table.TABLE_WIDTH / 2)
        else:
            off_center = abs(ball_pos.y) / (table.TABLE_WIDTH / 2)
        reach_prob -= off_center * 0.15
        reach_prob = max(0.1, min(0.99, reach_prob))
        return random.random() < reach_prob

    def calculate_return(self, incoming_bounce: BounceEvent) -> BallState:
        """Calculate a return shot from an incoming bounce on this player's side.

        Returns a BallState ready for physics.simulate().
        """
        my_half = -1 if self.side == 1 else 1
        target_dir = -my_half  # Hit toward opposite side

        # Pick shot type based on playstyle + randomness
        shot_type = random.choice(self.preferred_shots)

        # Base velocities scaled by power
        speed_map = {
            "slow_rally": (8, 0.5),
            "medium_rally": (13, 1.0),
            "fast_topspin": (20, 1.5),
            "smash": (26, 3.5),
            "backspin_chop": (9, 0.8),
        }
        base_vx, base_vz_down = speed_map.get(shot_type, (12, 1.0))

        # Scale by power with randomness
        power_noise = random.gauss(1.0, 0.08)
        vx = base_vx * self.power * power_noise * target_dir

        # Vertical: slight downward angle, adjusted by power
        vz = -base_vz_down * random.uniform(0.7, 1.3)

        # Lateral aim: slightly random
        vy = random.gauss(0, 0.3 + (1 - self.consistency) * 1.0)

        # Spin based on shot type and ability
        spin_x = 0.0
        spin_y = 0.0
        if shot_type in ("medium_rally", "fast_topspin"):
            spin_y = random.uniform(15, 55) * self.spin_ability * target_dir
        elif shot_type == "backspin_chop":
            spin_y = -random.uniform(10, 30) * self.spin_ability * target_dir
        elif shot_type == "smash":
            spin_y = random.uniform(5, 20) * self.spin_ability * target_dir

        # Sidespin sometimes
        if random.random() < 0.15:
            spin_x = random.gauss(0, 10) * self.spin_ability

        # Start position: near the bounce point, slightly behind
        start_x = incoming_bounce.pos.x + my_half * random.uniform(0.1, 0.3)
        # Clamp to player's side
        if self.side == 1:
            start_x = min(start_x, -0.2)
        else:
            start_x = max(start_x, 0.2)

        start_y = incoming_bounce.pos.y + random.gauss(0, 0.05)
        start_z = table.TABLE_HEIGHT + random.uniform(0.25, 0.50)

        # Consistency check: bad shots go off-target
        if random.random() > self.consistency:
            # Mis-hit: add error to velocity
            vx *= random.uniform(0.7, 1.4)
            vy += random.gauss(0, 1.5)
            vz += random.gauss(0, 1.0)

        return BallState(
            pos=Vec3(start_x, start_y, start_z),
            vel=Vec3(vx, vy, vz),
            spin=Vec3(spin_x, spin_y, 0),
        )

    def generate_serve(self) -> BallState:
        """Generate a serve from this player's side."""
        my_half = -1 if self.side == 1 else 1
        target_dir = -my_half

        # Serve position: behind the table on player's side
        start_x = my_half * (table.TABLE_LENGTH / 2 + 0.1)
        start_y = random.gauss(0, 0.15)
        start_z = table.TABLE_HEIGHT + random.uniform(0.30, 0.50)

        # Serve speed: moderate, with variety
        base_speed = random.uniform(7, 14) * (0.7 + self.power * 0.3)
        vx = base_speed * target_dir
        vz = random.uniform(-1.5, -0.3)
        vy = random.gauss(0, 0.4)

        # Serve spin
        spin_y = random.uniform(5, 35) * self.spin_ability * target_dir
        if random.random() < 0.3:  # Sometimes backspin serve
            spin_y = -spin_y * 0.5
        spin_x = random.gauss(0, 5) * self.spin_ability

        # Serve consistency
        if random.random() > self.consistency * 1.1:
            vz += random.gauss(0, 0.8)
            vy += random.gauss(0, 0.8)

        return BallState(
            pos=Vec3(start_x, start_y, start_z),
            vel=Vec3(vx, vy, vz),
            spin=Vec3(spin_x, spin_y, 0),
        )
