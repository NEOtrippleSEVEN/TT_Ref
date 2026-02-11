"""Official table tennis table dimensions and physical constants.

All values in SI units (meters, seconds, kg, radians).
Spin rates use rad/s — professional players generate 100-150 rps (628-942 rad/s).
"""

import math

# Table dimensions (meters) — ITTF standard
TABLE_LENGTH = 2.74
TABLE_WIDTH = 1.525
TABLE_HEIGHT = 0.76

# Net
NET_HEIGHT = 0.1525  # 15.25 cm above table surface
NET_OVERHANG = 0.1525  # net extends past table edge on each side

# Ball — ITTF standard (40mm plastic ball, since 2000)
BALL_RADIUS = 0.02  # 40mm diameter
BALL_MASS = 0.0027  # 2.7 grams
BALL_AREA = math.pi * BALL_RADIUS**2

# Bounce physics
RESTITUTION = 0.89  # COR for ITTF ball on table surface (0.87-0.89 range)
BALL_TABLE_FRICTION = 0.25  # spin-to-velocity conversion factor on bounce
SPIN_DECAY_ON_BOUNCE = 0.78  # spin retains ~78% after bounce (~22% loss, per research)

# Aerodynamics
DRAG_COEFFICIENT = 0.4  # smooth sphere at TT Reynolds numbers
GRAVITY = 9.81
AIR_DENSITY = 1.225  # kg/m^3 at sea level

# Magnus effect
# With real spin values (100-900 rad/s), the volumetric formula
# (4/3)*pi*r^3 * rho * Cl * |spin x vel| already produces ~100 m/s^2 at pro levels.
# MAGNUS_BOOST scales it down so heavy topspin dips at ~2x gravity (physically correct).
MAGNUS_CL = 0.5
MAGNUS_BOOST = 0.20

# Collision thresholds
EDGE_THRESHOLD = 0.03  # 3cm from edge = edge hit
OUT_OF_BOUNDS_MARGIN = 1.5  # meters past table before considered gone
