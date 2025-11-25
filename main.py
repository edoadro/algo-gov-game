"""
Mars Colony Manager - Main Game Loop
A retro-styled resource management game
"""
import sys
import json
import pygame
from settings import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    COLOR_BG, COLOR_TEXT, COLOR_ACCENT,
    FONT_TITLE, FONT_NORMAL, FONT_SMALL,
    GameState
)
from ui_manager import draw_text, draw_multiline_text, Button
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

        # UI elements (created dynamically based on state)
        self.buttons = []

    def handle_events(self):
        """Handle pygame events"""
        mouse_clicked = False
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouse_clicked = True

            # Any key press on start screen
            if event.type == pygame.KEYDOWN and self.game.current_state == GameState.START_SCREEN:
                self.game.start_game()

        # Update button hover states
        for button in self.buttons:
            button.update(mouse_pos)

            # Check for button clicks
            if button.is_clicked(mouse_pos, mouse_clicked):
                self.handle_button_click(button)

        return True

    def handle_button_click(self, button):
        """Handle button click based on current state"""
        if self.game.current_state == GameState.EVENT_DISPLAY:
            # Option buttons (0, 1, 2)
            if hasattr(button, 'option_index'):
                self.game.select_option(button.option_index)

        elif self.game.current_state == GameState.RESULT_DISPLAY:
            # Next button
            self.game.advance_to_next_event()

        elif self.game.current_state == GameState.GAME_OVER:
            # Restart button
            self.game.restart_game()

        elif self.game.current_state == GameState.VICTORY:
            # Restart button
            self.game.restart_game()

    def render(self):
        """Render the current game state"""
        self.screen.fill(COLOR_BG)

        if self.game.current_state == GameState.START_SCREEN:
            self.render_start_screen()

        elif self.game.current_state == GameState.EVENT_DISPLAY:
            self.render_event_display()

        elif self.game.current_state == GameState.RESULT_DISPLAY:
            self.render_result_display()

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

        self.buttons = []

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

        # Event description
        desc_y = 150
        draw_multiline_text(
            self.screen,
            event['description'],
            self.font_normal,
            COLOR_TEXT,
            100,
            desc_y,
            SCREEN_WIDTH - 200
        )

        # Create option buttons
        self.buttons = []
        button_width = 500
        button_height = 50
        button_x = (SCREEN_WIDTH - button_width) // 2
        button_y_start = 300

        for i, option in enumerate(event['options']):
            btn = Button(
                button_x,
                button_y_start + i * 70,
                button_width,
                button_height,
                option['text'],
                self.font_normal
            )
            btn.option_index = i  # Store which option this is
            self.buttons.append(btn)

        # Draw all buttons
        for button in self.buttons:
            button.draw(self.screen)

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

        # Outcome message
        draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            100,
            200,
            SCREEN_WIDTH - 200
        )

        # Stats changes
        old_stats = self.game.outcome_data['old_stats']
        new_stats = self.game.outcome_data['new_stats']

        stats_y = 300
        pop_text = f"POP: {old_stats['pop']} -> {new_stats['pop']}"
        qol_text = f"QOL: {old_stats['qol']} -> {new_stats['qol']}"

        draw_text(self.screen, pop_text, self.font_normal, COLOR_TEXT, SCREEN_WIDTH // 2, stats_y, center=True)
        draw_text(self.screen, qol_text, self.font_normal, COLOR_TEXT, SCREEN_WIDTH // 2, stats_y + 40, center=True)

        # Next button
        self.buttons = []
        next_btn = Button(
            SCREEN_WIDTH // 2 - 100,
            450,
            200,
            50,
            "Next",
            self.font_normal
        )
        self.buttons.append(next_btn)
        next_btn.draw(self.screen)

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

        # Fail message
        draw_multiline_text(
            self.screen,
            self.game.outcome_data['message'],
            self.font_normal,
            COLOR_TEXT,
            100,
            250,
            SCREEN_WIDTH - 200
        )

        # Restart button
        self.buttons = []
        restart_btn = Button(
            SCREEN_WIDTH // 2 - 100,
            450,
            200,
            50,
            "Restart",
            self.font_normal
        )
        self.buttons.append(restart_btn)
        restart_btn.draw(self.screen)

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

        # Restart button
        self.buttons = []
        restart_btn = Button(
            SCREEN_WIDTH // 2 - 100,
            450,
            200,
            50,
            "Restart",
            self.font_normal
        )
        self.buttons.append(restart_btn)
        restart_btn.draw(self.screen)

    def run(self):
        """Main game loop"""
        running = True

        while running:
            running = self.handle_events()
            self.render()
            self.clock.tick(FPS)

        pygame.quit()
        sys.exit()


def main():
    """Entry point"""
    game = MarsColonyGame()
    game.run()


if __name__ == "__main__":
    main()
