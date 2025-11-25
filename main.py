"""
Mars Colony Manager - Main Game Loop
A retro-styled resource management game
"""
import sys
import json
import pygame
import threading
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT,
    FONT_TITLE, FONT_NORMAL, FONT_SMALL,
    GameState
)
from ui_manager import draw_text, draw_multiline_text, draw_text_box, draw_menu_options
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
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Mars Colony Manager")
        self.clock = pygame.time.Clock()

        # Load fonts
        self.font_title = pygame.font.Font(None, FONT_TITLE)
        self.font_normal = pygame.font.Font(None, FONT_NORMAL)
        self.font_small = pygame.font.Font(None, FONT_SMALL)

        # Load game data and initialize game state
        game_data = load_game_data('gamedata.json')
        self.game = Game(game_data)

        # Load background images
        self.default_bg = None
        default_bg_path = game_data.get('config', {}).get('default_background')
        if default_bg_path:
            self.default_bg = self.load_and_scale_image(default_bg_path)
        
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
        self.ai_decision_index = None
        self.ai_thread = None

    def load_and_scale_image(self, path):
        """Load an image and scale it to screen dimensions"""
        try:
            img = pygame.image.load(path)
            return pygame.transform.scale(img, (SCREEN_WIDTH, SCREEN_HEIGHT))
        except (pygame.error, FileNotFoundError):
            print(f"Warning: Could not load image at {path}")
            return None

    def start_ai_thread(self):
        """Start a background thread to get AI decision"""
        self.ai_decision_index = None
        event = self.game.get_current_event()
        if not event:
            return

        # Ensure client exists
        if not hasattr(self, 'llm_client'):
            from llm_client import LLMClient
            self.llm_client = LLMClient(provider='gemini')

        def target():
            try:
                self.ai_decision_index = self.llm_client.get_ai_decision(event, self.game.stats)
            except Exception as e:
                print(f"AI Error: {e}")
                self.ai_decision_index = 0 # Fallback

        self.ai_thread = threading.Thread(target=target, daemon=True)
        self.ai_thread.start()

    def handle_events(self):
        """Handle pygame events"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
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
            # Only one option: AI vs Human
            if option_index == 0:
                self.game.gameplay_mode = 'ai_vs_human'
                self.game.initialize_seed()
                self.game.start_ai_phase()
                # Start AI thinking process in background
                self.start_ai_thread()

        elif self.game.current_state == GameState.AI_THINKING:
            # Only option: "See Decision" (when ready)
            if option_index == 0 and self.ai_decision_index is not None:
                self.process_ai_decision()

        elif self.game.current_state == GameState.AI_EVENT_DISPLAY:
            # Only option: "Next" (index 0)
            self.game.current_state = GameState.AI_RESULT_DISPLAY

        elif self.game.current_state == GameState.AI_RESULT_DISPLAY:
            # Only option: "Next" (index 0)
            self.game.ai_advance_to_next_event()
            if self.game.current_state == GameState.AI_THINKING:
                self.start_ai_thread()
            elif self.game.current_state == GameState.VICTORY:
                # AI completed, start player phase
                self.game.start_player_phase()

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
        # Draw background
        bg_drawn = False
        
        # Check for event specific background
        if self.game.current_state in [GameState.EVENT_DISPLAY, GameState.PLAYER_EVENT_DISPLAY, GameState.AI_EVENT_DISPLAY, GameState.AI_THINKING]:
            event = self.game.get_current_event()
            if event and event['id'] in self.event_images:
                self.screen.blit(self.event_images[event['id']], (0, 0))
                bg_drawn = True
        
        # Fallback to default background if no event bg or not in event state
        if not bg_drawn and self.default_bg:
            self.screen.blit(self.default_bg, (0, 0))
            bg_drawn = True
            
        # Fallback to solid color if no images available
        if not bg_drawn:
            self.screen.fill(COLOR_BG)

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

        pygame.display.flip()

    def render_start_screen(self):
        """Render the start screen"""
        # Title
        draw_text(
            self.screen,
            "MARS COLONY MANAGER",
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 2 - 50,
            center=True
        )

        # Subtitle
        draw_text(
            self.screen,
            "Press Any Key to Begin",
            self.font_normal,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 2 + 50,
            center=True
        )

    def render_mode_select(self):
        """Render mode selection screen"""
        # Title
        draw_text(
            self.screen,
            "SELECT GAME MODE",
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            100,
            center=True
        )

        # Description text in middle
        desc_text = "Watch AI play, then compete with same challenges"
        draw_text(
            self.screen,
            desc_text,
            self.font_small,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            200,
            center=True
        )

        # Text box at bottom with menu
        box_height = 150
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, _, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        # Menu options
        self.menu_options = ["AI vs Human"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            content_y
        )

    def render_ai_thinking(self):
        """Show AI is making a decision"""
        # Title
        draw_text(
            self.screen,
            "AI PHASE",
            self.font_small,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            30,
            center=True
        )
        
        draw_text(
            self.screen,
            "AI IS THINKING...",
            self.font_title,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            150,
            center=True
        )

        # Text box at bottom
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, _, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        if self.ai_decision_index is None:
            # Still thinking
            draw_text(
                self.screen,
                "Analyzing colony status and event parameters...",
                self.font_normal,
                COLOR_TEXT,
                content_x,
                content_y
            )
            self.menu_options = []
        else:
            # Decision ready
            draw_text(
                self.screen,
                "Analysis complete. Strategy formulated.",
                self.font_normal,
                COLOR_TEXT,
                content_x,
                content_y
            )
            
            self.menu_options = ["See Decision"]
            draw_menu_options(
                self.screen,
                self.menu_options,
                self.selected_option_index,
                self.font_normal,
                content_x,
                content_y + 50
            )

    def render_ai_event_display(self):
        """Show event and AI's choice"""
        event = self.game.get_current_event()
        if not event:
            return

        # Event title and phase indicator
        draw_text(
            self.screen,
            "AI PHASE",
            self.font_small,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            30,
            center=True
        )

        draw_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            70,
            center=True
        )

        # Text box at bottom showing AI's choice and description
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, content_width, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        # Event description inside box
        text_height = draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            content_x,
            content_y,
            content_width
        )
        
        current_y = content_y + text_height + 20

        # Show AI's selected option with marker
        ai_choice_text = f"AI chose: {event['options'][self.game.selected_option]['text']}"
        draw_text(
            self.screen,
            ai_choice_text,
            self.font_normal,
            COLOR_ACCENT,
            content_x,
            current_y
        )
        
        current_y += 40

        # Next menu option
        self.menu_options = ["Next"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            current_y + 10
        )

    def render_event_display(self):
        """Render event with options"""
        event = self.game.get_current_event()
        if not event:
            return

        # Stats display (top-right)
        stats_text = f"POP: {self.game.stats['pop']} | QOL: {self.game.stats['qol']}"
        draw_text(self.screen, stats_text, self.font_small, COLOR_ACCENT, SCREEN_WIDTH - 200, 20)

        # Event title
        draw_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            80,
            center=True
        )

        # Text box at bottom with options and description
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, content_width, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        # Event description inside box
        text_height = draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            content_x,
            content_y,
            content_width
        )

        # Menu options below description
        self.menu_options = [option['text'] for option in event['options']]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            content_y + text_height + 20,
            line_spacing=40
        )

    def render_player_event_display(self):
        """Render event with AI's choice highlighted"""
        event = self.game.get_current_event()
        if not event:
            return

        # Phase indicator
        draw_text(
            self.screen,
            "YOUR TURN",
            self.font_small,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            30,
            center=True
        )

        # Stats display (top-right)
        stats_text = f"POP: {self.game.stats['pop']} | QOL: {self.game.stats['qol']}"
        draw_text(self.screen, stats_text, self.font_small, COLOR_ACCENT, SCREEN_WIDTH - 200, 20)

        # Event title
        draw_text(
            self.screen,
            event['title'],
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            70,
            center=True
        )

        # Text box at bottom with options
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, content_width, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        # Event description inside box
        text_height = draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            content_x,
            content_y,
            content_width
        )
        
        current_y = content_y + text_height + 20

        # AI's choice indicator
        ai_choice_index = self.game.get_ai_choice_for_current_event()
        if ai_choice_index is not None:
            ai_text = f"AI chose option {ai_choice_index + 1}"
            draw_text(
                self.screen,
                ai_text,
                self.font_small,
                COLOR_ACCENT,
                content_x,
                current_y
            )
            current_y += 30

        # Menu options with AI choice marked
        self.menu_options = []
        for i, option in enumerate(event['options']):
            if i == ai_choice_index:
                self.menu_options.append(f"{option['text']} (AI)")
            else:
                self.menu_options.append(option['text'])

        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            current_y,
            line_spacing=40
        )

    def render_comparison(self):
        """Show AI vs Player comparison"""
        comparison = self.game.calculate_comparison_data()

        # Title
        draw_text(
            self.screen,
            "FINAL RESULTS",
            self.font_title,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            50,
            center=True
        )

        # AI Results (left column)
        ai_x = 150
        draw_text(self.screen, "AI PLAYER", self.font_normal, COLOR_TEXT, ai_x, 120)

        if comparison['ai']['completed']:
            ai_stats = comparison['ai']['stats']
            draw_text(self.screen, f"POP: {ai_stats['pop']}", self.font_small, COLOR_TEXT, ai_x, 160)
            draw_text(self.screen, f"QOL: {ai_stats['qol']}", self.font_small, COLOR_TEXT, ai_x, 190)
            total_ai = ai_stats['pop'] + ai_stats['qol']
            draw_text(self.screen, f"TOTAL: {total_ai}", self.font_normal, COLOR_ACCENT, ai_x, 230)
        else:
            draw_text(self.screen, "GAME OVER", self.font_small, COLOR_TEXT, ai_x, 160)

        # Player Results (right column)
        player_x = 450
        draw_text(self.screen, "YOU", self.font_normal, COLOR_TEXT, player_x, 120)

        player_stats = comparison['player']['stats']
        draw_text(self.screen, f"POP: {player_stats['pop']}", self.font_small, COLOR_TEXT, player_x, 160)
        draw_text(self.screen, f"QOL: {player_stats['qol']}", self.font_small, COLOR_TEXT, player_x, 190)
        total_player = player_stats['pop'] + player_stats['qol']
        draw_text(self.screen, f"TOTAL: {total_player}", self.font_normal, COLOR_ACCENT, player_x, 230)

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
            SCREEN_WIDTH // 2,
            320,
            center=True
        )

        # Text box at bottom with menu
        box_height = 120
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, _, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

        # Menu option
        self.menu_options = ["Play Again"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            content_y
        )

    def render_result_display(self):
        """Render success result"""
        if not self.game.outcome_data:
            return

        # Success message
        draw_text(
            self.screen,
            "SUCCESS!",
            self.font_title,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            100,
            center=True
        )

        # Text box at bottom with menu
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, content_width, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )
        
        # Outcome message inside box
        text_height = draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            content_x,
            content_y,
            content_width
        )

        current_y = content_y + text_height + 20

        # Only show stat changes if it's NOT the AI phase
        if self.game.current_phase != 'ai':
            # Stats changes inside box
            old_stats = self.game.outcome_data['old_stats']
            new_stats = self.game.outcome_data['new_stats']

            pop_text = f"POP: {old_stats['pop']} -> {new_stats['pop']}"
            qol_text = f"QOL: {old_stats['qol']} -> {new_stats['qol']}"

            draw_text(self.screen, pop_text, self.font_normal, COLOR_TEXT, content_x, current_y)
            draw_text(self.screen, qol_text, self.font_normal, COLOR_TEXT, content_x, current_y + 30)
            
            button_y_offset = 80
        else:
            # Hide stats for AI to prevent player cheating
            draw_text(self.screen, "Stats updated (Hidden)", self.font_small, COLOR_ACCENT, content_x, current_y)
            button_y_offset = 40

        # Menu option
        self.menu_options = ["Next"]
        draw_menu_options(
            self.screen,
            self.menu_options,
            self.selected_option_index,
            self.font_normal,
            content_x,
            current_y + button_y_offset
        )

    def render_game_over(self):
        """Render game over screen"""
        if not self.game.outcome_data:
            return

        # Game over title
        draw_text(
            self.screen,
            "GAME OVER",
            self.font_title,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            100,
            center=True
        )

        # Text box at bottom with menu
        box_height = 240
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, content_width, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )
        
        # Fail message inside box
        text_height = draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            content_x,
            content_y,
            content_width
        )

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
            content_x,
            content_y + text_height + 30
        )

    def render_victory(self):
        """Render victory screen"""
        # Victory title
        draw_text(
            self.screen,
            "COLONY SURVIVED!",
            self.font_title,
            COLOR_ACCENT,
            SCREEN_WIDTH // 2,
            150,
            center=True
        )

        # Final stats
        stats_y = 250
        draw_text(
            self.screen,
            "Final Stats:",
            self.font_normal,
            COLOR_TEXT,
            SCREEN_WIDTH // 2,
            stats_y,
            center=True
        )

        pop_text = f"Population: {self.game.stats['pop']}"
        qol_text = f"Quality of Life: {self.game.stats['qol']}"

        draw_text(self.screen, pop_text, self.font_normal, COLOR_TEXT, SCREEN_WIDTH // 2, stats_y + 50, center=True)
        draw_text(self.screen, qol_text, self.font_normal, COLOR_TEXT, SCREEN_WIDTH // 2, stats_y + 90, center=True)

        # Text box at bottom with menu
        box_height = 120
        box_y = SCREEN_HEIGHT - box_height - 20
        content_x, content_y, _, _ = draw_text_box(
            self.screen,
            20,
            box_y,
            SCREEN_WIDTH - 40,
            box_height
        )

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
            content_x,
            content_y
        )

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
        if self.ai_decision_index is None:
            return

        event = self.game.get_current_event()
        if not event:
            return

        # Use the result from the thread
        option_index = self.ai_decision_index

        # Store which option AI chose (for display)
        self.game.selected_option = option_index

        # Process outcome
        option = event['options'][option_index]
        self.game.old_stats = self.game.stats.copy()
        self.game.process_outcome(option)

        # Record decision
        self.game.record_ai_decision(option_index, self.game.outcome_data['success'])

        # Check if AI failed
        if self.game.current_state == GameState.GAME_OVER:
            # AI failed this event
            self.game.ai_game_over_handler()
        else:
            # Show AI's choice to player
            self.game.current_state = GameState.AI_EVENT_DISPLAY


def main():
    """Entry point"""
    game = MarsColonyGame()
    game.run()


if __name__ == "__main__":
    main()
