"""Core data types for the TT Referee simulation."""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Vec3:
    """3D vector for position, velocity, and spin."""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: "Vec3") -> "Vec3":
        return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> "Vec3":
        return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> "Vec3":
        return self.__mul__(scalar)

    def magnitude(self) -> float:
        return (self.x**2 + self.y**2 + self.z**2) ** 0.5

    def cross(self, other: "Vec3") -> "Vec3":
        return Vec3(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def copy(self) -> "Vec3":
        return Vec3(self.x, self.y, self.z)


@dataclass
class BallState:
    """Full state of the ball at a point in time."""
    pos: Vec3 = field(default_factory=Vec3)
    vel: Vec3 = field(default_factory=Vec3)
    spin: Vec3 = field(default_factory=Vec3)
    alive: bool = True
    t: float = 0.0

    def copy(self) -> "BallState":
        return BallState(
            pos=self.pos.copy(),
            vel=self.vel.copy(),
            spin=self.spin.copy(),
            alive=self.alive,
            t=self.t,
        )


@dataclass
class BounceEvent:
    """A detected bounce on the table surface."""
    pos: Vec3
    t: float
    side: str  # "left" or "right"
    is_edge: bool = False


@dataclass
class NetEvent:
    """A net interaction event."""
    pos: Vec3
    t: float
    clipped: bool = False  # True if ball just clipped the top


@dataclass
class OutEvent:
    """Ball went out of bounds."""
    pos: Vec3
    t: float


@dataclass
class CameraFrame:
    """A single frame captured by a virtual camera."""
    frame_num: int
    t: float
    pos_detected: Optional[Vec3]
    confidence: float
    blur_px: float
    detected: bool = True


@dataclass
class RefereeDecision:
    """A scoring decision made by the referee engine."""
    type: str  # "bounce", "net", "out", "point"
    side: str  # "left" or "right"
    confidence: float
    frames_used: int


@dataclass
class Match:
    """Current match state."""
    p1_score: int = 0
    p2_score: int = 0
    server: int = 1  # 1 or 2
    serve_count: int = 0
    history: list = field(default_factory=list)
    deuce: bool = False
    winner: Optional[int] = None
