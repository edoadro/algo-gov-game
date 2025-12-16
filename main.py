"""
Mars Colony Manager - Main Game Loop
A retro-styled resource management game
"""
import sys
import json
import os
import pygame
import threading
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT, FPS,
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT,
    FONT_TITLE, FONT_NORMAL, FONT_SMALL,
    GameState
)
from ui_manager import draw_text, draw_multiline_text, draw_text_box, draw_menu_options, draw_text_right, measure_multiline_text
from game_state import Game


def load_game_data(filepath):
    """Load game data from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find {filepath}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}")
        sys.exit(1)


class MarsColonyGame:
    """Main game application class"""

    def __init__(self):
        """Initialize pygame and game components"""
        pygame.init()
        # Create the actual display window (resizable)
        self.display_window = pygame.display.set_mode(
            (INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT), 
            pygame.RESIZABLE
        )
        # Create the virtual surface for fixed-resolution rendering
        self.screen = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        
        pygame.display.set_caption("Mars Colony Manager")
        self.clock = pygame.time.Clock()

        # Load fonts
        # Use system monospace font for better symbol support (arrows) and retro look
        # pygame.font.SysFont(name, size) - name can be a comma-separated list of preferences
        font_prefs = 'couriernew,courier,monospace'
        self.font_title = pygame.font.SysFont(font_prefs, FONT_TITLE, bold=True)
        self.font_normal = pygame.font.SysFont(font_prefs, FONT_NORMAL, bold=True)
        self.font_small = pygame.font.SysFont(font_prefs, FONT_SMALL, bold=True)

        # Load game data and initialize game state
        game_data = load_game_data('gamedata.json')
        self.game = Game(game_data)

        # Load background images
        self.default_bg = None
        default_bg_path = game_data.get('config', {}).get('default_background')
        if default_bg_path:
            self.default_bg = self.load_and_scale_image(default_bg_path)
            
        # Load thinking background
        self.thinking_bg = None
        thinking_images = game_data.get('config', {}).get('thinking_images', [])
        if thinking_images:
            import random
            thinking_path = random.choice(thinking_images)
            self.thinking_bg = self.load_and_scale_image(thinking_path)
        
        # Cache event images
        self.event_images = {}
        for event in self.game.events:
            if event.get('image'):
                img = self.load_and_scale_image(event['image'])
                if img:
                    self.event_images[event['id']] = img

        # UI state for menu navigation
        self.menu_options = []  # List of text strings for current menu
        self.selected_option_index = 0  # Track which option is selected with keyboard
        
        # AI Threading state
        self.ai_decision_data = None
        self.ai_thread = None
        self.game_session_id = 0

    def _draw_nav_hint(self, bottom_pane_rect):
        """Draw navigation hint in the bottom right of the given rectangle."""
        bottom_x, bottom_y, bottom_w, bottom_h = bottom_pane_rect
        hint_text = "Use ↑ ↓ to select, ENTER to confirm"
        
        # Position slightly above the very bottom and with some padding from the right
        # bottom_x + bottom_w is the right edge of the inner box
        # bottom_y + bottom_h is the bottom edge of the inner box
        draw_text_right(
            self.screen,
            hint_text,
            self.font_small,
            COLOR_ACCENT,
            bottom_x + bottom_w - 10, # 10 pixels padding from right
            bottom_y + bottom_h - self.font_small.get_height() - 5 # 5 pixels padding from bottom
        )

    def load_and_scale_image(self, path):
        """Load an image and scale it to screen dimensions"""
        try:
            # Normalize path for OS (handles / vs \ on Windows)
            norm_path = os.path.normpath(path)
            img = pygame.image.load(norm_path)
            # Scale to fit the top-right pane (790x500)
            return pygame.transform.scale(img, (790, 500))
        except (pygame.error, FileNotFoundError):
            print(f"Warning: Could not load image at {path}")
            return None

    def start_ai_thread(self):
        """Start a background thread to get AI decision"""
        self.ai_decision_data = None
        event = self.game.get_current_event()
        if not event:
            return

        # Ensure client exists
        if not hasattr(self, 'llm_client'):
            from llm_client import LLMClient
            self.llm_client = LLMClient()

        current_session_id = self.game_session_id

        def target():
            try:
                # Returns dict {'choice': int, 'reason': str}
                result = self.llm_client.get_ai_decision(event, self.game.stats)
                self.ai_decision_data = {'result': result, 'session_id': current_session_id}
            except Exception as e:
                print(f"AI Error: {e}")
                self.ai_decision_data = {'result': {'choice': 0, 'reason': "Error in AI processing."}, 'session_id': current_session_id}

        self.ai_thread = threading.Thread(target=target, daemon=True)
        self.ai_thread.start()

    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            elif event.type == pygame.VIDEORESIZE:
                # Update display window size
                self.display_window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)

            if event.type == pygame.KEYDOWN:
                # F11 for Fullscreen toggle
                if event.key == pygame.K_F11:
                    is_fullscreen = self.display_window.get_flags() & pygame.FULLSCREEN
                    if is_fullscreen:
                        self.display_window = pygame.display.set_mode((INITIAL_WINDOW_WIDTH, INITIAL_WINDOW_HEIGHT), pygame.RESIZABLE)
                    else:
                        # Switch to fullscreen using current desktop resolution
                        self.display_window = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)

                # Any key press on start screen
                if self.game.current_state == GameState.START_SCREEN:
                    self.game.start_game()
                    self.selected_option_index = 0

                # Arrow key navigation
                elif event.key == pygame.K_UP:
                    if len(self.menu_options) > 0:
                        self.selected_option_index = (self.selected_option_index - 1) % len(self.menu_options)

                elif event.key == pygame.K_DOWN:
                    if len(self.menu_options) > 0:
                        self.selected_option_index = (self.selected_option_index + 1) % len(self.menu_options)

                # Enter or Space to confirm selection
                elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if len(self.menu_options) > 0:
                        self.handle_menu_selection(self.selected_option_index)
                        self.selected_option_index = 0  # Reset for next screen

        return True

    def handle_menu_selection(self, option_index):
        """Handle menu option selection based on current state"""
        if self.game.current_state == GameState.MODE_SELECT:
            # Only one option: Start Simulation
            if option_index == 0:
                self.game.start_simultaneous_mode()
                self.ai_decision_data = None # Clear stale data
                self.game_session_id += 1 # Invalidate old threads
                # self.game.gameplay_mode = 'ai_vs_human'
                # self.game.initialize_seed()
                # self.game.start_ai_phase()
                # AI thread starts in AI_EVENT_DISPLAY now

        elif self.game.current_state == GameState.AI_THINKING:
            # Only option: "See Decision" (when ready)
            if option_index == 0 and self.ai_decision_data is not None:
                self.process_ai_decision()

        elif self.game.current_state == GameState.AI_EVENT_DISPLAY:
            if self.game.selected_option is None:
                # Initial view: Player clicks "Let AI Decide"
                self.start_ai_thread()
                self.game.current_state = GameState.AI_THINKING
            else:
                # After choice: Player clicks "Next" to see result or Game Over
                if self.game.outcome_data['success']:
                    self.game.current_state = GameState.AI_RESULT_DISPLAY
                else:
                    # AI failed
                    self.game.ai_game_over_handler()

        elif self.game.current_state == GameState.AI_RESULT_DISPLAY:
            # Only option: "Next" (index 0)
            self.game.ai_advance_to_next_event()
            if self.game.current_state == GameState.VICTORY:
                # AI completed, start player phase
                self.game.start_player_phase()

        elif self.game.current_state == GameState.SIMULTANEOUS_EVENT_DISPLAY:
            # Player selects option (0, 1, 2)
            # Only allow if AI has finished thinking (optional, but requested "sees ai choice")
            if self.game.simultaneous_data['ai_choice'] is not None:
                if self.game.player_game_over:
                    # Player is eliminated, button is "Continue Watching"
                    if option_index == 0:
                        self.game.skip_simultaneous_player_turn()
                else:
                    self.game.process_simultaneous_player_decision(option_index)

        elif self.game.current_state == GameState.SIMULTANEOUS_RESULT_DISPLAY:
            # Next button
            self.game.advance_simultaneous_next_event()

        elif self.game.current_state == GameState.PLAYER_EVENT_DISPLAY:
            # Player selects from 3 options (0, 1, 2)
            self.game.player_select_option(option_index)

        elif self.game.current_state == GameState.EVENT_DISPLAY:
            # Select from 3 options (0, 1, 2)
            self.game.select_option(option_index)

        elif self.game.current_state == GameState.RESULT_DISPLAY:
            # Only option: "Next" (index 0)
            if self.game.current_phase == 'player':
                self.game.player_advance_to_next_event()
            else:
                self.game.advance_to_next_event()

        elif self.game.current_state == GameState.COMPARISON:
            # Only option: "Play Again" (index 0)
            self.game.restart_game()
            self.game.current_state = GameState.MODE_SELECT

        elif self.game.current_state == GameState.GAME_OVER:
            # Only option: "Restart" or continue (index 0)
            if self.game.current_phase == 'ai':
                # AI failed, proceed to player phase
                self.game.ai_game_over_handler()
                self.game.start_player_phase()
            elif self.game.current_phase == 'player':
                # Player failed, go to comparison
                self.game.current_state = GameState.COMPARISON
            else:
                # Regular restart
                self.game.restart_game()

        elif self.game.current_state == GameState.VICTORY:
            # Only option: "Continue" or "Restart" (index 0)
            if self.game.current_phase == 'ai':
                # AI won, start player phase
                self.game.start_player_phase()
            elif self.game.current_phase == 'player':
                # Player won, show comparison
                self.game.current_state = GameState.COMPARISON
            else:
                # Regular restart
                self.game.restart_game()

    def render(self):
        """Render the current game state"""
        # 1. Render everything to the fixed-resolution virtual screen
        self.screen.fill(COLOR_BG)

        # Draw background
        bg_drawn = False
        
        # If in simultaneous mode, do not draw default backgrounds, as each panel draws its own
        if self.game.current_state in [GameState.SIMULTANEOUS_EVENT_DISPLAY, GameState.SIMULTANEOUS_RESULT_DISPLAY]:
            bg_drawn = True

        # Check for AI thinking specific background
        if self.game.current_state == GameState.AI_THINKING and self.thinking_bg:
            self.screen.blit(self.thinking_bg, (930, 20))
            bg_drawn = True
        
        # Check for event specific background
        elif self.game.current_state in [GameState.EVENT_DISPLAY, GameState.PLAYER_EVENT_DISPLAY, GameState.AI_EVENT_DISPLAY]:
            event = self.game.get_current_event()
            if event and event['id'] in self.event_images:
                self.screen.blit(self.event_images[event['id']], (930, 20))
                bg_drawn = True
        
        # Fallback to default background if no event bg or not in event state
        if not bg_drawn and self.default_bg:
            self.screen.blit(self.default_bg, (930, 20))

        if self.game.current_state == GameState.START_SCREEN:
            self.render_start_screen()

        elif self.game.current_state == GameState.MODE_SELECT:
            self.render_mode_select()

        elif self.game.current_state == GameState.AI_THINKING:
            self.render_ai_thinking()

        elif self.game.current_state == GameState.AI_EVENT_DISPLAY:
            self.render_ai_event_display()

        elif self.game.current_state == GameState.AI_RESULT_DISPLAY:
            self.render_result_display()

        elif self.game.current_state == GameState.SIMULTANEOUS_EVENT_DISPLAY:
            self.render_simultaneous_event()

        elif self.game.current_state == GameState.SIMULTANEOUS_RESULT_DISPLAY:
            self.render_simultaneous_result()

        elif self.game.current_state == GameState.PLAYER_EVENT_DISPLAY:
            self.render_player_event_display()

        elif self.game.current_state == GameState.EVENT_DISPLAY:
            self.render_event_display()

        elif self.game.current_state == GameState.RESULT_DISPLAY:
            self.render_result_display()

        elif self.game.current_state == GameState.COMPARISON:
            self.render_comparison()

        elif self.game.current_state == GameState.GAME_OVER:
            self.render_game_over()

        elif self.game.current_state == GameState.VICTORY:
            self.render_victory()

        # 2. Scale and blit the virtual screen to the actual display window
        window_w, window_h = self.display_window.get_size()
        screen_w, screen_h = self.screen.get_size()

        scale = min(window_w / screen_w, window_h / screen_h)
        new_w = int(screen_w * scale)
        new_h = int(screen_h * scale)

        # Use smoothscale for better quality
        scaled_surface = pygame.transform.smoothscale(self.screen, (new_w, new_h))
        
        # Center the scaled surface
        x_offset = (window_w - new_w) // 2
        y_offset = (window_h - new_h) // 2

        self.display_window.fill((0, 0, 0))  # Black bars for letterboxing
        self.display_window.blit(scaled_surface, (x_offset, y_offset))

        pygame.display.flip()

    def render_start_screen(self):
        """Render the start screen"""
        # Left Pane: Title
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)
        
        # Title Text
        draw_text(self.screen, "MARS", self.font_title, COLOR_TEXT, left_x + left_w // 2, left_y + 150, center=True)
        draw_text(self.screen, "COLONY", self.font_title, COLOR_TEXT, left_x + left_w // 2, left_y + 200, center=True)
        draw_text(self.screen, "MANAGER", self.font_title, COLOR_TEXT, left_x + left_w // 2, left_y + 250, center=True)

        # Bottom Right Pane: Prompt
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)
        
        draw_text(
            self.screen,
            "Press Any Key to Begin",
            self.font_normal,
            COLOR_ACCENT,
            bottom_x + bottom_w // 2,
            bottom_y + bottom_h // 2,
            center=True
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_mode_select(self):
        """Render intro and explanation screen"""
        # Get text from config
        intro_title = self.game.config.get('intro_title', 'INTRODUCTION')
        intro_text = self.game.config.get('intro_text', 'Welcome to Mars Colony Manager.')
        explanation_text = self.game.config.get('game_explanation', 'Compare your choices with AI.')

        # Left Pane: Intro
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)
        
        draw_text(self.screen, intro_title, self.font_title, COLOR_TEXT, left_x, left_y)
        
        draw_multiline_text(
            self.screen,
            intro_text,
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 60,
            left_w
        )

        # Bottom Right Pane: Explanation and Start
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Explanation text above the button
        draw_multiline_text(
            self.screen,
            explanation_text,
            self.font_normal,
            COLOR_TEXT,
            bottom_x,
            bottom_y,
            bottom_w
        )

        # Menu options
        self.menu_options = ["Start Simulation"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y + 100, # Push button down
            bottom_w
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_ai_thinking(self):
        """Show AI is making a decision"""
        # Left Pane: Status
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)

        draw_text(
            self.screen,
            "AI PHASE",
            self.font_title,
            COLOR_ACCENT,
            left_x,
            left_y
        )
        
        draw_text(
            self.screen,
            "STATUS:",
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 50
        )

        if self.ai_decision_data is None:
            # Still thinking
            draw_multiline_text(
                self.screen,
                "Analyzing colony status...",
                self.font_normal,
                COLOR_TEXT,
                left_x,
                left_y + 90,
                left_w
            )
            self.menu_options = []
        else:
            # Decision ready
            draw_multiline_text(
                self.screen,
                "Strategy formulated.",
                self.font_normal,
                COLOR_TEXT,
                left_x,
                left_y + 90,
                left_w
            )
            
            # Bottom Right Pane: Action
            bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)
            
            self.menu_options = ["See Decision"]
            draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                bottom_x,
                bottom_y,
                bottom_w
            )
            self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_ai_event_display(self):
        """Show event and AI's choice"""
        event = self.game.get_current_event()
        if not event:
            return

        # Left Pane: Event Info
        left_x, left_y, left_w, left_h = draw_text_box(self.screen, 20, 20, 890, 860)

        draw_text(
            self.screen,
            "AI PHASE",
            self.font_small,
            COLOR_ACCENT,
            left_x,
            left_y
        )

        draw_multiline_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            left_x,
            left_y + 30,
            left_w
        )

        draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 100,
            left_w
        )
        
        # Show AI Choice and Reasoning in Left Pane (Bottom Aligned)
        if self.game.selected_option is not None:
            ai_reason = self.game.get_ai_reason_for_current_event()
            
            # Prepare text
            choice_text = f"AI CHOICE: {event['options'][self.game.selected_option]['text']}"
            reason_text = ai_reason if ai_reason else "No rationale provided."

            # Measure heights
            choice_h = measure_multiline_text(choice_text, self.font_title, left_w)
            reason_h = measure_multiline_text(reason_text, self.font_small, left_w)
            
            spacing = 10
            total_h = choice_h + spacing + reason_h
            
            # Start Y position (bottom of box minus total height minus padding)
            start_y = (left_y + left_h) - total_h - 20 

            # Draw Choice (Big Font)
            draw_multiline_text(
                self.screen,
                choice_text,
                self.font_title,
                COLOR_ACCENT,
                left_x,
                start_y,
                left_w
            )

            # Draw Reasoning (Small Font)
            draw_multiline_text(
                self.screen,
                reason_text,
                self.font_small,
                COLOR_TEXT,
                left_x,
                start_y + choice_h + spacing,
                left_w
            )
        
        # Bottom Right Pane: Action
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        if self.game.selected_option is None:
            # Initial state: Prompt user to trigger AI
            self.menu_options = ["Let AI Decide"]
            draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                bottom_x,
                bottom_y,
                bottom_w
            )
        else:
            # AI has chosen: Show Next button only (Choice is now in left pane)
            # But we need to communicate flow. Maybe just "Next".
            
            # Next menu option
            self.menu_options = ["Next"]
            draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                bottom_x,
                bottom_y,
                bottom_w
            )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_event_display(self):
        """Render event with options"""
        event = self.game.get_current_event()
        if not event:
            return

        # Left Pane: Description
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)

        # Stats display (in left pane top)
        stats_text = f"Population: {self.game.stats['pop']} | Quality of Life: {self.game.stats['qol']}"
        draw_text(self.screen, stats_text, self.font_small, COLOR_ACCENT, left_x, left_y)

        draw_multiline_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            left_x,
            left_y + 40,
            left_w
        )

        draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 110,
            left_w
        )

        # Bottom Right Pane: Options
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Menu options
        self.menu_options = [option['text'] for option in event['options']]
        menu_height = draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y,
            bottom_w,
            line_spacing=40
        )
        
        # Show details for selected option
        if 0 <= self.selected_option_index < len(event['options']):
            details = event['options'][self.selected_option_index].get('details', '')
            if details:
                draw_multiline_text(
                    self.screen,
                    details,
                    self.font_small,
                    COLOR_ACCENT,
                    bottom_x,
                    bottom_y + menu_height + 20,
                    bottom_w
                )

        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_player_event_display(self):
        """Render event with AI's choice highlighted"""
        event = self.game.get_current_event()
        if not event:
            return

        # Left Pane: Description
        left_x, left_y, left_w, left_h = draw_text_box(self.screen, 20, 20, 890, 860)

        # Phase indicator
        draw_text(
            self.screen,
            "YOUR TURN",
            self.font_small,
            COLOR_ACCENT,
            left_x,
            left_y
        )

        # Stats display
        stats_text = f"Population: {self.game.stats['pop']} | Quality of Life: {self.game.stats['qol']}"
        draw_text(self.screen, stats_text, self.font_small, COLOR_ACCENT, left_x, left_y + 25)

        draw_multiline_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            left_x,
            left_y + 60,
            left_w
        )

        draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 130,
            left_w
        )
        
        # Show AI Choice and Reasoning in Left Pane (Bottom Aligned)
        ai_choice_index = self.game.get_ai_choice_for_current_event()
        if ai_choice_index is not None:
            ai_reason = self.game.get_ai_reason_for_current_event()
            
            # Prepare text
            choice_text = f"AI CHOICE: {event['options'][ai_choice_index]['text']}"
            reason_text = ai_reason if ai_reason else "No rationale provided."

            # Measure heights
            choice_h = measure_multiline_text(choice_text, self.font_title, left_w)
            reason_h = measure_multiline_text(reason_text, self.font_small, left_w)
            
            spacing = 10
            total_h = choice_h + spacing + reason_h
            
            # Start Y position (bottom of box minus total height minus padding)
            start_y = (left_y + left_h) - total_h - 20 

            # Draw Choice (Big Font)
            draw_multiline_text(
                self.screen,
                choice_text,
                self.font_title,
                COLOR_ACCENT,
                left_x,
                start_y,
                left_w
            )

            # Draw Reasoning (Small Font)
            draw_multiline_text(
                self.screen,
                reason_text,
                self.font_small,
                COLOR_TEXT,
                left_x,
                start_y + choice_h + spacing,
                left_w
            )
        
        # Bottom Right Pane: Options
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)
        
        current_y = bottom_y

        # Menu options with AI choice marked
        self.menu_options = []
        for i, option in enumerate(event['options']):
            if i == ai_choice_index:
                self.menu_options.append(f"{option['text']} (AI)")
            else:
                self.menu_options.append(option['text'])

        menu_height = draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            current_y,
            bottom_w,
            line_spacing=35
        )

        # Show details for selected option
        if 0 <= self.selected_option_index < len(event['options']):
            details = event['options'][self.selected_option_index].get('details', '')
            if details:
                draw_multiline_text(
                    self.screen,
                    details,
                    self.font_small,
                    COLOR_ACCENT,
                    bottom_x,
                    current_y + menu_height + 20,
                    bottom_w
                )

        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_comparison(self):
        """Show AI vs Player comparison"""
        comparison = self.game.calculate_comparison_data()

        # Left Pane: Results Table
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)

        draw_text(
            self.screen,
            "RESULTS",
            self.font_title,
            COLOR_ACCENT,
            left_x,
            left_y
        )

        # AI Results
        current_y = left_y + 60
        draw_text(self.screen, "AI PLAYER", self.font_normal, COLOR_TEXT, left_x, current_y)
        
        if comparison['ai']['completed']:
            ai_stats = comparison['ai']['stats']
            draw_text(self.screen, f"Population: {ai_stats['pop']}", self.font_small, COLOR_TEXT, left_x, current_y + 30)
            draw_text(self.screen, f"Quality of Life: {ai_stats['qol']}", self.font_small, COLOR_TEXT, left_x, current_y + 50)
            total_ai = ai_stats['pop'] + ai_stats['qol']
            draw_text(self.screen, f"TOTAL: {total_ai}", self.font_normal, COLOR_ACCENT, left_x, current_y + 80)
        else:
            draw_text(self.screen, "GAME OVER", self.font_small, COLOR_TEXT, left_x, current_y + 30)

        # Player Results
        current_y += 140
        draw_text(self.screen, "YOU", self.font_normal, COLOR_TEXT, left_x, current_y)

        if comparison['player']['completed']:
            player_stats = comparison['player']['stats']
            draw_text(self.screen, f"Population: {player_stats['pop']}", self.font_small, COLOR_TEXT, left_x, current_y + 30)
            draw_text(self.screen, f"Quality of Life: {player_stats['qol']}", self.font_small, COLOR_TEXT, left_x, current_y + 50)
            total_player = player_stats['pop'] + player_stats['qol']
            draw_text(self.screen, f"TOTAL: {total_player}", self.font_normal, COLOR_ACCENT, left_x, current_y + 80)
        else:
            draw_text(self.screen, "GAME OVER", self.font_small, COLOR_TEXT, left_x, current_y + 30)


        # Winner announcement
        winner_text = {
            'player': "YOU WIN!",
            'ai': "AI WINS!",
            'tie': "IT'S A TIE!"
        }[comparison['winner']]

        draw_text(
            self.screen,
            winner_text,
            self.font_title,
            COLOR_ACCENT,
            left_x,
            current_y + 140
        )

        # Bottom Right Pane: Menu
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Menu option
        self.menu_options = ["Play Again"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y,
            bottom_w
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_result_display(self):
        """Render success result"""
        if not self.game.outcome_data:
            return

        # Left Pane: Outcome Message & Stats
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)
        
        # Success message
        draw_text(
            self.screen,
            "SUCCESS!",
            self.font_title,
            COLOR_ACCENT,
            left_x,
            left_y
        )

        # Outcome message
        text_height = draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 50,
            left_w
        )

        current_y = left_y + 50 + text_height + 30

        # Only show stat changes if it's NOT the AI phase
        if self.game.current_phase != 'ai':
            # Stats changes
            old_stats = self.game.outcome_data['old_stats']
            new_stats = self.game.outcome_data['new_stats']

            pop_text = f"Population: {old_stats['pop']} -> {new_stats['pop']}"
            qol_text = f"Quality of Life: {old_stats['qol']} -> {new_stats['qol']}"

            draw_text(self.screen, pop_text, self.font_normal, COLOR_TEXT, left_x, current_y)
            draw_text(self.screen, qol_text, self.font_normal, COLOR_TEXT, left_x, current_y + 30)

        # Bottom Right Pane: Menu
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Menu option
        self.menu_options = ["Next"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y,
            bottom_w
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_game_over(self):
        """Render game over screen"""
        if not self.game.outcome_data:
            return

        # Left Pane: Fail Message
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)

        # Game over title
        draw_text(
            self.screen,
            "GAME OVER",
            self.font_title,
            COLOR_TEXT,
            left_x,
            left_y
        )
        
        draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 50,
            left_w
        )

        # Draw result image if available
        result_image_path = self.game.outcome_data.get('result_image')
        if result_image_path:
            img = self.load_and_scale_image(result_image_path)
            if img:
                 # Position image in left pane
                 # Scale image to fit width (approx 850)
                 # Re-scale logic: load_and_scale_image scales to 790x500 by default (for right pane).
                 # We want it in left pane (890 wide).
                 # Let's just re-scale it or use it as is?
                 # load_and_scale_image returns 790x500.
                 # Left pane is 890 wide. 790 fits.
                 self.screen.blit(img, (left_x + 50, left_y + 300))

        # Bottom Right Pane: Menu
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Determine button text based on context
        if self.game.current_phase == 'ai':
            menu_text = "Continue"
        elif self.game.current_phase == 'player':
            menu_text = "See Results"
        else:
            menu_text = "Restart"

        # Menu option
        self.menu_options = [menu_text]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y,
            bottom_w
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_victory(self):
        """Render victory screen"""
        # Left Pane: Victory Info
        left_x, left_y, left_w, _ = draw_text_box(self.screen, 20, 20, 890, 860)

        # Victory title
        draw_text(
            self.screen,
            "SURVIVED!",
            self.font_title,
            COLOR_ACCENT,
            left_x,
            left_y
        )

        # Final stats
        draw_text(
            self.screen,
            "Final Stats:",
            self.font_normal,
            COLOR_TEXT,
            left_x,
            left_y + 50
        )

        pop_text = f"Population: {self.game.stats['pop']}"
        qol_text = f"Quality of Life: {self.game.stats['qol']}"

        draw_text(self.screen, pop_text, self.font_normal, COLOR_TEXT, left_x, left_y + 90)
        draw_text(self.screen, qol_text, self.font_normal, COLOR_TEXT, left_x, left_y + 120)

        # Bottom Right Pane: Menu
        bottom_x, bottom_y, bottom_w, bottom_h = draw_text_box(self.screen, 930, 540, 790, 340)

        # Determine button text based on context
        if self.game.current_phase == 'ai':
            menu_text = "Continue"
        elif self.game.current_phase == 'player':
            menu_text = "See Results"
        else:
            menu_text = "Restart"

        # Menu option
        self.menu_options = [menu_text]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            bottom_x,
            bottom_y,
            bottom_w
        )
        self._draw_nav_hint((bottom_x, bottom_y, bottom_w, bottom_h))

    def render_simultaneous_event(self):
        """Render split-screen simultaneous event"""
        event = self.game.get_current_event()
        if not event:
            return

        # --- AI Logic Check ---
        # If AI hasn't chosen yet
        if self.game.simultaneous_data['ai_choice'] is None:
            # Check if AI is already eliminated
            if self.game.ai_game_over:
                 self.game.simultaneous_data['ai_choice'] = -1
                 self.game.simultaneous_data['ai_reason'] = "Eliminated."
                 self.game.simultaneous_data['ai_outcome'] = {'success': False, 'message': "ELIMINATED", 'old_stats': self.game.ai_stats, 'new_stats': self.game.ai_stats}
            else:
                # Normal AI processing
                # Check if we have a result from the thread
                if self.ai_decision_data and self.ai_decision_data.get('session_id') == self.game_session_id:
                    # Process it
                    result = self.ai_decision_data['result']
                    choice = result['choice']
                    reason = result['reason']
                    self.game.process_simultaneous_ai_decision(choice, reason)
                    self.ai_decision_data = None # Clear for next time
                # If no result and no thread, start it
                elif not (self.ai_thread and self.ai_thread.is_alive()):
                    self.start_ai_thread()

        # --- Layout ---
        # 3 Columns: AI (Left), Text (Center), Player (Right)
        
        # Dimensions
        col_w = 580 # Wider AI/Player columns
        center_w = 520 # Wider center column
        col_h = 860
        margin = 20
        
        ai_x = margin
        center_x = ai_x + col_w + margin
        player_x = center_x + center_w + margin
        
        y = margin

        # --- Center Panel: Event Text ---
        # Using draw_text_box for style
        cx, cy, cw, ch = draw_text_box(self.screen, center_x, y, center_w, col_h)
        
        draw_text(self.screen, "EVENT DATA", self.font_small, COLOR_ACCENT, cx, cy)
        
        draw_multiline_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            cx,
            cy + 40,
            cw
        )

        draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            cx,
            cy + 120,
            cw
        )

        # --- AI Panel (Left) ---
        ax, ay, aw, ah = draw_text_box(self.screen, ai_x, y, col_w, col_h)
        
        draw_text(self.screen, "AI PLAYER", self.font_title, COLOR_ACCENT, ax + aw // 2, ay, center=True)
        
        # Stats
        stats = self.game.ai_stats
        draw_text(self.screen, f"Population: {stats['pop']} | Quality of Life: {stats['qol']}", self.font_normal, COLOR_TEXT, ax + aw // 2, ay + 40, center=True)
        
        # Image
        if event['id'] in self.event_images:
            # Scale image to fit width (440 approx)
            img = self.event_images[event['id']]
            scaled_img = pygame.transform.scale(img, (aw, 280)) # fit width
            self.screen.blit(scaled_img, (ai_x + 15, ay + 80)) # Adjust for padding
            
        # Decision Status
        status_y = ay + 380
        
        # Determine if we should reveal the outcome (only after player chooses or if player is out)
        # Actually, "player choice" happens instantly when clicking button. 
        # But here we are in EVENT_DISPLAY. 
        # The flow is: 
        # 1. EVENT_DISPLAY (Thinking -> AI Choice Locked).
        # 2. Player clicks option -> Game state updates to RESULT_DISPLAY.
        # So in EVENT_DISPLAY, we only show "AI CHOSE: Option X". We should NOT show "ELIMINATED" yet?
        # BUT: The user asked "users sees ai choice and can change for its runtime".
        # If AI failed, does the user SEE that it failed? 
        # User said: "show failure of ai after player choice only".
        # So here, we should just show the CHOICE.
        
        if self.game.simultaneous_data['ai_choice'] is None:
            draw_text(self.screen, "THINKING...", self.font_title, COLOR_ACCENT, ax + aw//2, status_y, center=True)
        else:
            # AI has chosen. Even if eliminated internally, we masquerade it as just a choice here.
            choice_idx = self.game.simultaneous_data['ai_choice']
            # If AI is eliminated, we might have set choice to -1. Handle that.
            if choice_idx == -1:
                 # It was eliminated previously? Or just now?
                 # If just now (in this turn), we should show the choice that KILLED it?
                 # Ah, my previous logic set choice=-1 if ai_game_over.
                 # We need to know WHAT it chose to die.
                 # Let's rely on the fact that if it died THIS turn, we might want to show the choice.
                 # But wait, if ai_game_over is True, I forced choice to -1 in the logic above.
                 # I should fix that logic to preserve the fatal choice if possible, or just say "Eliminated" if it was a previous turn.
                 pass
            
            # Revised logic:
            # If AI is ELIMINATED from a *previous* turn, show ELIMINATED.
            # If AI is ELIMINATED *this* turn, show the fatal choice (and reveal death in Result screen).
            
            # How to know if it was previous? 
            # We can check if ai_choice is -1 (which I set for 'already eliminated').
            
            if choice_idx == -1:
                draw_text(self.screen, "ELIMINATED", self.font_title, COLOR_TEXT, ax + aw//2, status_y, center=True)
                if self.game.ai_elimination_image:
                     img = self.load_and_scale_image(self.game.ai_elimination_image)
                     if img:
                         scaled_img = pygame.transform.scale(img, (aw, 280))
                         self.screen.blit(scaled_img, (ai_x + 15, ay + 80))
            else:
                # Show Choice (Normal or Fatal)
                choice_text = event['options'][choice_idx]['text']
                reason = self.game.simultaneous_data['ai_reason']
                
                draw_text(self.screen, "AI CHOSE:", self.font_small, COLOR_ACCENT, ax, status_y)
                draw_multiline_text(self.screen, choice_text, self.font_title, COLOR_TEXT, ax, status_y + 25, aw)
                
                # Reason
                reason_y = status_y + 100
                draw_text(self.screen, "REASON:", self.font_small, COLOR_ACCENT, ax, reason_y)
                draw_multiline_text(self.screen, reason, self.font_small, COLOR_TEXT, ax, reason_y + 25, aw)


        # --- Player Panel (Right) ---
        px, py, pw, ph = draw_text_box(self.screen, player_x, y, col_w, col_h)
        
        draw_text(self.screen, "HUMAN PLAYER", self.font_title, COLOR_ACCENT, px + pw // 2, py, center=True)
        
        # Stats
        p_stats = self.game.stats
        draw_text(self.screen, f"Population: {p_stats['pop']} | Quality of Life: {p_stats['qol']}", self.font_normal, COLOR_TEXT, px + pw // 2, py + 40, center=True)

        # Image
        if event['id'] in self.event_images:
            img = self.event_images[event['id']]
            scaled_img = pygame.transform.scale(img, (pw, 280))
            self.screen.blit(scaled_img, (player_x + 15, py + 80))

        # Controls
        menu_y = py + 380
        
        if self.game.simultaneous_data['ai_choice'] is None:
             draw_text(self.screen, "WAITING FOR AI...", self.font_normal, COLOR_ACCENT, px + pw//2, menu_y, center=True)
             self.menu_options = []
        elif self.game.player_game_over:
             draw_text(self.screen, "ELIMINATED", self.font_title, COLOR_TEXT, px + pw//2, menu_y, center=True)
             
             # Draw elimination image if available
             if self.game.player_elimination_image:
                 img = self.load_and_scale_image(self.game.player_elimination_image)
                 if img:
                     # Scale to fit panel width (approx 440)
                     scaled_img = pygame.transform.scale(img, (pw, 280))
                     self.screen.blit(scaled_img, (player_x + 15, py + 80))
             
             # Continue button
             self.menu_options = ["Continue Watching"]
             draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                px,
                menu_y + 80,
                pw
             )
             self._draw_nav_hint((px, py, pw, ph))
        else:
             # Show Options
             self.menu_options = [opt['text'] for opt in event['options']]
             menu_height = draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                px, # x position for the menu block (left-aligned within the panel)
                menu_y,
                pw # max_width for word wrapping
             )
             
             # Show details for selected option
             if 0 <= self.selected_option_index < len(event['options']):
                 details = event['options'][self.selected_option_index].get('details', '')
                 if details:
                     draw_multiline_text(
                         self.screen,
                         details,
                         self.font_small,
                         COLOR_ACCENT,
                         px,
                         menu_y + menu_height + 20,
                         pw
                     )
             
             # Nav Hint
             self._draw_nav_hint((px, py, pw, ph))

    def render_simultaneous_result(self):
        """Render results for simultaneous turn"""
        if not self.game.simultaneous_data['player_outcome']:
            return

        # Reuse similar layout
        # 3 Columns: AI (Left), Center (Summary?), Player (Right)
        
        col_w = 580
        center_w = 520
        col_h = 860
        margin = 20
        
        ai_x = margin
        center_x = ai_x + col_w + margin
        player_x = center_x + center_w + margin
        y = margin
        
        # --- AI Result ---
        ax, ay, aw, ah = draw_text_box(self.screen, ai_x, y, col_w, col_h)
        ai_out = self.game.simultaneous_data['ai_outcome']
        
        draw_text(self.screen, "AI RESULT", self.font_title, COLOR_ACCENT, ax + aw // 2, ay, center=True)
        
        if self.game.ai_game_over:
            # Show Eliminated View
            draw_text(self.screen, "ELIMINATED", self.font_title, COLOR_TEXT, ax + aw//2, ay + 60, center=True)
            if self.game.ai_elimination_image:
                 img = self.load_and_scale_image(self.game.ai_elimination_image)
                 if img:
                     scaled_img = pygame.transform.scale(img, (aw, 280))
                     self.screen.blit(scaled_img, (ai_x + 15, ay + 120))
        else:
            # Normal Result View
            status_text = "SUCCESS" if ai_out['success'] else "FAILURE"
            color = COLOR_ACCENT if ai_out['success'] else COLOR_TEXT
            draw_text(self.screen, status_text, self.font_title, color, ax + aw//2, ay + 60, center=True)
            
            draw_multiline_text(self.screen, ai_out['message'], self.font_normal, COLOR_TEXT, ax, ay + 120, aw)
            
            # Stats Delta
            old = ai_out['old_stats']
            new = ai_out['new_stats']
            draw_text(self.screen, f"Population: {old['pop']} -> {new['pop']}", self.font_normal, COLOR_TEXT, ax, ay + 300)
            draw_text(self.screen, f"Quality of Life: {old['qol']} -> {new['qol']}", self.font_normal, COLOR_TEXT, ax, ay + 340)


        # --- Player Result ---
        px, py, pw, ph = draw_text_box(self.screen, player_x, y, col_w, col_h)
        p_out = self.game.simultaneous_data['player_outcome']
        
        draw_text(self.screen, "YOUR RESULT", self.font_title, COLOR_ACCENT, px + pw // 2, py, center=True)
        
        if self.game.player_game_over:
            # Show Eliminated View
            draw_text(self.screen, "ELIMINATED", self.font_title, COLOR_TEXT, px + pw//2, py + 60, center=True)
            if self.game.player_elimination_image:
                 img = self.load_and_scale_image(self.game.player_elimination_image)
                 if img:
                     scaled_img = pygame.transform.scale(img, (pw, 280))
                     self.screen.blit(scaled_img, (player_x + 15, py + 120))
        else:
            status_text = "SUCCESS" if p_out['success'] else "FAILURE"
            color = COLOR_ACCENT if p_out['success'] else COLOR_TEXT
            draw_text(self.screen, status_text, self.font_title, color, px + pw//2, py + 60, center=True)
            
            draw_multiline_text(self.screen, p_out['message'], self.font_normal, COLOR_TEXT, px, py + 120, pw)

            # Stats Delta
            old = p_out['old_stats']
            new = p_out['new_stats']
            draw_text(self.screen, f"Population: {old['pop']} -> {new['pop']}", self.font_normal, COLOR_TEXT, px, py + 300)
            draw_text(self.screen, f"Quality of Life: {old['qol']} -> {new['qol']}", self.font_normal, COLOR_TEXT, px, py + 340)

        # --- Center Control ---
        cx, cy, cw, ch = draw_text_box(self.screen, center_x, y, center_w, col_h)
        
        draw_text(self.screen, "ROUND COMPLETE", self.font_title, COLOR_ACCENT, cx, cy, center=True)
        
        # Next Button
        self.menu_options = ["Next Event"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            cx,
            cy + 400,
            cw
        )
        self._draw_nav_hint((cx, cy, cw, ch))

    def run(self):
        """Main game loop"""
        running = True

        while running:
            running = self.handle_events()
            self.render()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()

    def process_ai_decision(self):
        """Process the AI's decision using the result from the thread"""
        if self.ai_decision_data is None:
            return

        event = self.game.get_current_event()
        if not event:
            return

        # Use the result from the thread
        result = self.ai_decision_data
        option_index = result.get('choice', 0)
        reason = result.get('reason', "No reason recorded.")

        # Store which option AI chose (for display)
        self.game.selected_option = option_index

        # Process outcome
        option = event['options'][option_index]
        self.game.old_stats = self.game.stats.copy()
        self.game.process_outcome(option)

        # Record decision
        self.game.record_ai_decision(option_index, self.game.outcome_data['success'], reason=reason)

        # Always show AI's choice to player (go back to event display with choice revealed)
        # Even if failed, we show choice first, then Next leads to Game Over
        self.game.current_state = GameState.AI_EVENT_DISPLAY


def main():
    """Entry point"""
    game = MarsColonyGame()
    game.run()


if __name__ == "__main__":
    main()