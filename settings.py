"""
Game settings and constants for Mars Colony Manager
Retro GameBoy aesthetic configuration
"""
from enum import Enum

# Screen settings
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# GameBoy retro colors (classic green palette)
COLOR_BG = (15, 56, 15)           # Dark green background
COLOR_TEXT = (155, 188, 15)        # Light green text
COLOR_ACCENT = (139, 172, 15)      # Medium green accent
COLOR_BUTTON = (48, 98, 48)        # Button background
COLOR_BUTTON_HOVER = (139, 172, 15) # Button hover

# Font sizes
FONT_TITLE = 32
FONT_NORMAL = 24
FONT_SMALL = 18


class GameState(Enum):
    """Game state machine states"""
    START_SCREEN = 1      # Title + "Press Any Key"
    EVENT_DISPLAY = 2     # Show event + 3 option buttons
    PROCESSING = 3        # RNG roll + stat update
    RESULT_DISPLAY = 4    # Show success msg + new stats + Next button
    GAME_OVER = 5         # Show fail_msg + Restart button
    VICTORY = 6           # All events completed
