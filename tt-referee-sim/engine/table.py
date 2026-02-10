"""Official table tennis table dimensions and physical constants."""

import math

# Table dimensions (meters) — ITTF standard
TABLE_LENGTH = 2.74
TABLE_WIDTH = 1.525
TABLE_HEIGHT = 0.76

# Net
NET_HEIGHT = 0.1525
NET_OVERHANG = 0.1525  # net extends past table edge

# Ball
BALL_RADIUS = 0.02  # 40mm diameter
BALL_MASS = 0.0027  # 2.7 grams
BALL_AREA = math.pi * BALL_RADIUS**2

# Physics
RESTITUTION = 0.89
DRAG_COEFFICIENT = 0.4
GRAVITY = 9.81

# Air
AIR_DENSITY = 1.225  # kg/m^3

# Magnus effect lift coefficient
MAGNUS_CL = 0.5
MAGNUS_BOOST = 3.0  # Moderate amplification so spin visibly affects trajectories

# Collision thresholds
EDGE_THRESHOLD = 0.03  # 3cm from edge = edge hit
OUT_OF_BOUNDS_MARGIN = 1.5  # meters past table before considered gone
