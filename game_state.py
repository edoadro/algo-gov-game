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

        # Gameplay mode tracking
        self.gameplay_mode = None  # 'ai_vs_human' or None (for future single-player)
        self.current_phase = None  # 'ai' or 'player'

        # AI playthrough data
        self.ai_decisions = []  # List of {event_index, option_index, success, stats_before, stats_after}
        self.ai_final_stats = None  # {'pop': X, 'qol': Y} or None if AI failed
        self.ai_game_over = False

        # RNG seed management
        self.game_seed = None

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

        # Reset AI vs Human mode data
        self.gameplay_mode = None
        self.current_phase = None
        self.ai_decisions = []
        self.ai_final_stats = None
        self.ai_game_over = False
        self.game_seed = None

    def get_current_event(self):
        """Get the current event data"""
        if self.current_event_index < len(self.events):
            return self.events[self.current_event_index]
        return None

    def start_game(self):
        """Transition from start screen to mode select"""
        self.current_state = GameState.MODE_SELECT

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

    def initialize_seed(self):
        """Generate and store a fixed seed for this game session"""
        self.game_seed = random.randint(0, 999999)
        random.seed(self.game_seed)

    def reset_seed_for_player(self):
        """Reset RNG to same seed for player phase"""
        random.seed(self.game_seed)

    def start_ai_phase(self):
        """Begin AI playthrough"""
        self.current_phase = 'ai'
        self.current_state = GameState.AI_EVENT_DISPLAY
        self.current_event_index = 0
        self.stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }
        self.ai_decisions = []
        self.ai_game_over = False

    def record_ai_decision(self, option_index, success):
        """Store AI's decision and outcome"""
        self.ai_decisions.append({
            'event_index': self.current_event_index,
            'option_index': option_index,
            'success': success,
            'stats_before': self.old_stats.copy(),
            'stats_after': self.stats.copy() if success else None
        })

    def ai_advance_to_next_event(self):
        """AI phase progression"""
        self.current_event_index += 1
        self.selected_option = None  # Reset selection for next event

        if self.current_event_index >= len(self.events):
            # AI completed all events successfully
            self.ai_final_stats = self.stats.copy()
            self.current_state = GameState.VICTORY
        else:
            # Continue to next event
            self.current_state = GameState.AI_EVENT_DISPLAY

    def ai_game_over_handler(self):
        """Handle AI failing an event"""
        self.ai_game_over = True
        self.ai_final_stats = None
        # Transition to victory state which will trigger player phase
        self.current_state = GameState.VICTORY

    def start_player_phase(self):
        """Begin player playthrough with AI context"""
        self.current_phase = 'player'
        self.current_state = GameState.PLAYER_EVENT_DISPLAY
        self.current_event_index = 0

        # Reset stats
        self.stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }

        # Reset seed for fair comparison
        self.reset_seed_for_player()

    def get_ai_choice_for_current_event(self):
        """Get what AI chose for current event (if it got there)"""
        for decision in self.ai_decisions:
            if decision['event_index'] == self.current_event_index:
                return decision['option_index']
        return None

    def player_select_option(self, option_index):
        """Player makes a choice (possibly overriding AI)"""
        event = self.get_current_event()
        if not event:
            return

        option = event['options'][option_index]
        self.selected_option = option
        self.old_stats = self.stats.copy()

        # Process with same RNG sequence as AI used
        self.process_outcome(option)

    def player_advance_to_next_event(self):
        """Player phase progression"""
        self.current_event_index += 1

        if self.current_event_index >= len(self.events):
            # Player completed all events
            self.current_state = GameState.COMPARISON
        else:
            self.current_state = GameState.PLAYER_EVENT_DISPLAY

    def calculate_comparison_data(self):
        """Prepare data for comparison screen"""
        return {
            'ai': {
                'completed': not self.ai_game_over,
                'stats': self.ai_final_stats,
            },
            'player': {
                'stats': self.stats.copy(),
            },
            'winner': self.determine_winner()
        }

    def determine_winner(self):
        """Determine winner based on total score"""
        # If AI failed, player wins automatically
        if self.ai_game_over:
            return 'player'

        # Compare scores (pop + qol)
        ai_total = self.ai_final_stats['pop'] + self.ai_final_stats['qol']
        player_total = self.stats['pop'] + self.stats['qol']

        if player_total > ai_total:
            return 'player'
        elif ai_total > player_total:
            return 'ai'
        else:
            return 'tie'
