# Mars Colony Manager

A retro-styled text-based resource management game with GameBoy aesthetics, built with Python and Pygame.

## Overview

Manage a Mars colony through critical events. Each event presents 3 choices with different risk levels and rewards. Make the right decisions to survive!

## Features

- **AI vs Human mode** - watch AI play, then compete with same challenges
- **Retro GameBoy aesthetic** with classic green color palette
- **Data-driven design** - all game content in `gamedata.json`
- **State machine architecture** for clean game flow
- **Risk vs reward** gameplay with probability-based outcomes
- **LLM integration** - uses Gemini 2.5 Flash (default) or Groq via official SDKs (extensible for other providers)

## Installation

1. Create and activate virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
# If using Groq, also install the groq library:
# pip install groq
```

3. Setup API key (optional - game works without it using random AI):
```bash
cp .env.example .env
# Edit .env and add your API key(s)
# Set LLM_PROVIDER to 'groq' to use Groq, otherwise it defaults to 'gemini'.
# Example .env content:
# GEMINI_API_KEY=your_gemini_api_key_here
# GROQ_API_KEY=your_groq_api_key_here
# LLM_PROVIDER=gemini # or groq
```

## Running the Game

```bash
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
python3 main.py
```

## Controls

**Keyboard Only:**
- **Arrow Keys (Up/Down)**: Navigate between options
- **Enter or Space**: Select highlighted option
- **Any Key**: Start game from title screen

## How to Play

### AI vs Human Mode

1. **Start Screen**: Press any key to begin
2. **Mode Select**: Use arrow keys to select "AI vs Human", press Enter
3. **AI Phase**: Watch AI make decisions through all events
   - Press Enter on "Next" button to see each AI choice and outcome
4. **Player Phase**: Your turn with the same challenges
   - See what AI chose for each event (marked with "(AI)")
   - Use arrow keys to navigate, Enter to confirm AI's choice or select a different option
5. **Comparison**: See who performed better - you or the AI!

## Current Status

Current version includes:
- ✅ AI vs Human mode with full gameplay loop
- ✅ Gemini 2.5 Flash integration via official SDK (with fallback to random)
- ✅ 1 event (Water Crisis) with 3 choices - scalable for more events
- ✅ Full state machine (start, mode select, AI phase, player phase, comparison)
- ✅ Fixed RNG seed for fair AI vs player comparison
- ✅ Text-only retro interface
- ✅ GameBoy color palette

## File Structure

```
algo-gov-game/
├── main.py              # Entry point and game loop
├── settings.py          # Constants and configuration
├── game_state.py        # State machine and game logic
├── ui_manager.py        # UI helpers and Button class
├── llm_client.py        # LLM API integration (Gemini SDK, extensible)
├── gamedata.json        # Game content and probabilities
├── .env.example         # Environment template
├── requirements.txt     # Python dependencies
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
- **pygame-ce** (Community Edition) recommended
- **python-dotenv** for environment configuration
- **google-generativeai** official SDK for Gemini API
- 800x600 window resolution
- 60 FPS target
- Clean separation: game logic, UI rendering, LLM client, and data

## Future Enhancements

- Custom retro fonts
- Sound effects
- Background images
- Multiple events (10+ for full experience)
- ASCII art decorations
- Score-based win conditions
