"""
Game state machine and core game logic
"""
import random
from settings import GameState


class Game:
    """Main game class managing state and stats"""

    def __init__(self, game_data):
        """
        Initialize game with data from JSON

        Args:
            game_data: Dictionary loaded from gamedata.json
        """
        self.game_data = game_data
        self.config = game_data['config']
        self.events = game_data['events']

        # Game state
        self.current_state = GameState.START_SCREEN
        self.current_event_index = 0

        # Player stats
        self.stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }

        # Temporary data for state transitions
        self.selected_option = None
        self.outcome_data = None
        self.old_stats = None

    def reset(self):
        """Reset game to initial state"""
        self.current_state = GameState.START_SCREEN
        self.current_event_index = 0
        self.stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }
        self.selected_option = None
        self.outcome_data = None
        self.old_stats = None

    def get_current_event(self):
        """Get the current event data"""
        if self.current_event_index < len(self.events):
            return self.events[self.current_event_index]
        return None

    def start_game(self):
        """Transition from start screen to first event"""
        self.current_state = GameState.EVENT_DISPLAY

    def select_option(self, option_index):
        """
        Player selects an option, process the outcome

        Args:
            option_index: Index of the selected option (0, 1, or 2)
        """
        event = self.get_current_event()
        if not event:
            return

        option = event['options'][option_index]
        self.selected_option = option

        # Save stats before modification
        self.old_stats = self.stats.copy()

        # Process outcome with RNG
        self.process_outcome(option)

    def process_outcome(self, option_data):
        """
        Roll RNG and determine success or failure

        Args:
            option_data: The selected option dictionary
        """
        roll = random.random()  # 0.0 to 1.0

        if roll <= option_data['chance_success']:
            # SUCCESS PATH
            # Apply rewards
            self.stats['pop'] += option_data['success_reward']['pop']
            self.stats['qol'] += option_data['success_reward']['qol']

            # Store outcome for display
            self.outcome_data = {
                'success': True,
                'message': option_data['success_msg'],
                'old_stats': self.old_stats,
                'new_stats': self.stats.copy()
            }

            # Transition to result display
            self.current_state = GameState.RESULT_DISPLAY
        else:
            # FAIL PATH
            # Store outcome for display
            self.outcome_data = {
                'success': False,
                'message': option_data['fail_msg']
            }

            # Immediate game over, no stat update
            self.current_state = GameState.GAME_OVER

    def advance_to_next_event(self):
        """Move to next event or victory screen"""
        self.current_event_index += 1

        if self.current_event_index >= len(self.events):
            # No more events, player wins
            self.current_state = GameState.VICTORY
        else:
            # More events available
            self.current_state = GameState.EVENT_DISPLAY

    def restart_game(self):
        """Restart from game over or victory"""
        self.reset()
