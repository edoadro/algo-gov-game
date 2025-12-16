"""
Game settings and constants for Mars Colony Manager
Retro GameBoy aesthetic configuration
"""
from enum import Enum

# Screen settings (Internal Resolution)
SCREEN_WIDTH = 1740
SCREEN_HEIGHT = 900

# Initial Window Size (75% of internal resolution)
INITIAL_WINDOW_WIDTH = int(SCREEN_WIDTH * 0.75)
INITIAL_WINDOW_HEIGHT = int(SCREEN_HEIGHT * 0.75)

FPS = 60

# GameBoy retro colors (classic green palette)
COLOR_BG = (15, 56, 15)           # Dark green background
COLOR_TEXT = (155, 188, 15)        # Light green text
COLOR_ACCENT = (139, 172, 15)      # Medium green accent
COLOR_BUTTON = (48, 98, 48)        # Button background
COLOR_BUTTON_HOVER = (139, 172, 15) # Button hover

# Font sizes (Reduced for smaller overall scale)
FONT_TITLE = 29
FONT_NORMAL = 22
FONT_SMALL = 17


class GameState(Enum):
    """Game state machine states"""
    START_SCREEN = 1           # Title + "Press Any Key"
    MODE_SELECT = 2            # Choose AI vs Human mode
    AI_THINKING = 3            # "AI is thinking..." display
    AI_EVENT_DISPLAY = 4       # Show event + AI's choice
    AI_RESULT_DISPLAY = 5      # Show AI's outcome
    PLAYER_EVENT_DISPLAY = 6   # Show event + AI suggestion + 3 buttons
    EVENT_DISPLAY = 7          # Show event + 3 option buttons (original)
    PROCESSING = 8             # RNG roll + stat update
    RESULT_DISPLAY = 9         # Show success msg + new stats + Next button
    GAME_OVER = 10             # Show fail_msg + Restart button
    VICTORY = 11               # All events completed
    COMPARISON = 12            # AI vs Player comparison screen
    SIMULTANEOUS_EVENT_DISPLAY = 13 # Split screen AI/Human event
    SIMULTANEOUS_RESULT_DISPLAY = 14 # Split screen results
    API_KEY_INPUT = 15         # Prompt for Gemini API Key
