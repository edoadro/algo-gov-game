# Mars Colony Manager

A retro-styled text-based resource management game with GameBoy aesthetics, built with Python and Pygame.

## Overview

Manage a Mars colony through critical events. Each event presents 3 choices with different risk levels and rewards. Make the right decisions to survive!

## Features

- **Retro GameBoy aesthetic** with classic green color palette
- **Data-driven design** - all game content in `gamedata.json`
- **State machine architecture** for clean game flow
- **Risk vs reward** gameplay with probability-based outcomes

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install pygame-ce
# Or fallback to: pip install pygame
```

## Running the Game

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python3 main.py
```

## How to Play

1. **Start Screen**: Press any key to begin
2. **Event Screen**: Read the event and click one of the 3 options
3. **Outcome**: See if your choice succeeded or failed
   - **Success**: View stat changes and continue
   - **Failure**: Game over with explanation
4. **Victory**: Complete all events to win

## MVP Status

Current version includes:
- ✅ 1 event (Water Crisis) with 3 choices
- ✅ Full state machine (start, event, result, game over, victory)
- ✅ RNG-based success/failure system
- ✅ Text-only retro interface
- ✅ GameBoy color palette

## File Structure

```
algo-gov-game/
├── main.py              # Entry point and game loop
├── settings.py          # Constants and configuration
├── game_state.py        # State machine and game logic
├── ui_manager.py        # UI helpers and Button class
├── gamedata.json        # Game content and probabilities
├── assets/              # Assets directory (fonts, images, sounds)
└── .venv/               # Virtual environment
```

## Expanding the Game

To add more events, edit `gamedata.json` and add new event objects following this structure:

```json
{
  "id": 2,
  "title": "Event Title",
  "description": "Event description text",
  "options": [
    {
      "id": 1,
      "text": "Option text",
      "chance_success": 0.7,
      "success_reward": {"pop": 5, "qol": 10},
      "success_msg": "Success message",
      "fail_msg": "Failure message (game over)"
    }
  ]
}
```

## Technical Details

- **Python 3.10+** required
- **pygame-ce** (Community Edition) or pygame
- 800x600 window resolution
- 60 FPS target
- Clean separation: game logic, UI rendering, and data

## Future Enhancements

- Custom retro fonts
- Sound effects
- Background images
- Multiple events (10+ for full experience)
- ASCII art decorations
- Score-based win conditions
