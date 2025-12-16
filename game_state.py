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
        
        # AI stats (for simultaneous mode)
        self.ai_stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }

        # Temporary data for state transitions
        self.selected_option = None
        self.outcome_data = None
        self.old_stats = None
        
        # Simultaneous mode state
        self.simultaneous_data = {
            'ai_choice': None,
            'ai_reason': None,
            'player_choice': None,
            'ai_outcome': None,
            'player_outcome': None
        }

        # Gameplay mode tracking
        self.gameplay_mode = None  # 'ai_vs_human' or None (for future single-player)
        self.current_phase = None  # 'ai' or 'player'

        # AI playthrough data
        self.ai_decisions = []  # List of {event_index, option_index, success, stats_before, stats_after}
        self.ai_final_stats = None  # {'pop': X, 'qol': Y} or None if AI failed
        self.ai_game_over = False
        self.player_game_over = False
        
        self.ai_elimination_image = None
        self.player_elimination_image = None

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
        self.ai_stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }
        self.selected_option = None
        self.outcome_data = None
        self.old_stats = None
        
        self.simultaneous_data = {
            'ai_choice': None,
            'ai_reason': None,
            'player_choice': None,
            'ai_outcome': None,
            'player_outcome': None
        }

        # Reset AI vs Human mode data
        self.gameplay_mode = None
        self.current_phase = None
        self.ai_decisions = []
        self.ai_final_stats = None
        self.ai_game_over = False
        self.player_game_over = False
        self.ai_elimination_image = None
        self.player_elimination_image = None
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

    def get_deterministic_outcome(self, event_index, option_index, chance_success):
        """
        Get a deterministic success/fail result based on seed, event, and option.
        Ensures that if AI and Player pick the same option for the same event, 
        they get the same result.
        """
        # Create a unique seed for this specific choice point
        unique_seed = f"{self.game_seed}-{event_index}-{option_index}"
        
        # Use a localized Random instance to avoid affecting global RNG state
        rng = random.Random(unique_seed)
        roll = rng.random()
        
        return roll <= chance_success

    def process_outcome(self, option_data):
        """
        Roll RNG and determine success or failure

        Args:
            option_data: The selected option dictionary
        """
        # For standard mode, we need the option index.
        # But we only have option_data here. 
        # We need to find the index of this option in the current event.
        event = self.get_current_event()
        option_index = 0
        if event:
             for i, opt in enumerate(event['options']):
                 if opt == option_data:
                     option_index = i
                     break

        success = self.get_deterministic_outcome(self.current_event_index, option_index, option_data['chance_success'])

        if success:
            # SUCCESS PATH
            # Apply rewards
            self.stats['pop'] += option_data['success_reward']['pop']
            self.stats['qol'] += option_data['success_reward']['qol']

            # Store outcome for display
            self.outcome_data = {
                'success': True,
                'message': option_data['success_msg'],
                'old_stats': self.old_stats,
                'new_stats': self.stats.copy(),
                'result_image': None # Success doesn't have a specific image in spec, but could.
            }

            # Transition to result display
            self.current_state = GameState.RESULT_DISPLAY
        else:
            # FAIL PATH
            # Store outcome for display
            fail_image = option_data.get('fail_image', self.config.get('game_over_image'))
            
            self.outcome_data = {
                'success': False,
                'message': option_data['fail_msg'],
                'result_image': fail_image
            }

            # Immediate game over, no stat update
            if self.current_phase == 'player':
                self.player_game_over = True
            
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

    def record_ai_decision(self, option_index, success, reason=""):
        """Store AI's decision and outcome"""
        self.ai_decisions.append({
            'event_index': self.current_event_index,
            'option_index': option_index,
            'reason': reason,
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
        # Transition to GAME_OVER state to show failure screen
        self.current_state = GameState.GAME_OVER

    def start_player_phase(self):
        """Begin player playthrough with AI context"""
        self.current_phase = 'player'
        self.current_state = GameState.PLAYER_EVENT_DISPLAY
        self.current_event_index = 0
        self.player_game_over = False

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

    def get_ai_reason_for_current_event(self):
        """Get AI's reasoning for current event"""
        for decision in self.ai_decisions:
            if decision['event_index'] == self.current_event_index:
                return decision.get('reason', "")
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
                'completed': not self.player_game_over,
                'stats': self.stats.copy(),
            },
            'winner': self.determine_winner()
        }

    def determine_winner(self):
        """Determine winner based on survival and total score"""
        # 1. Survival Check
        # If Player died and AI survived -> AI Wins
        if self.player_game_over and not self.ai_game_over:
            return 'ai'
        
        # If Player survived and AI died -> Player Wins
        if not self.player_game_over and self.ai_game_over:
            return 'player'
            
        # If both died -> Tie
        if self.player_game_over and self.ai_game_over:
            return 'tie'

        # 2. Score Check (Both Survived)
        # Ensure stats are available (should be if no game over)
        if not self.ai_final_stats:
             # Fallback if something went wrong, though shouldn't happen here
             return 'player' 
             
        ai_total = self.ai_final_stats['pop'] * self.ai_final_stats['qol']
        player_total = self.stats['pop'] * self.stats['qol']

        if player_total > ai_total:
            return 'player'
        elif ai_total > player_total:
            return 'ai'
        else:
            return 'tie'

    def start_simultaneous_mode(self):
        """Start the simultaneous AI vs Human mode"""
        self.gameplay_mode = 'simultaneous'
        self.current_state = GameState.SIMULTANEOUS_EVENT_DISPLAY
        self.current_event_index = 0
        
        # Reset stats for both
        self.stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }
        self.ai_stats = {
            'pop': self.config['starting_pop'],
            'qol': self.config['starting_qol']
        }
        
        # Reset tracking
        self.simultaneous_data = {
            'ai_choice': None,
            'ai_reason': None,
            'player_choice': None,
            'ai_outcome': None,
            'player_outcome': None
        }
        self.ai_game_over = False
        self.player_game_over = False
        
        self.ai_decisions = []
        self.ai_final_stats = None
        self.ai_elimination_image = None
        self.player_elimination_image = None
        
        self.initialize_seed()

    def process_simultaneous_ai_decision(self, option_index, reason):
        """Process AI decision in simultaneous mode"""
        event = self.get_current_event()
        if not event: 
            return
            
        print(f"DEBUG: Processing AI Decision. Event: {event['title']}, Option: {option_index}")

        self.simultaneous_data['ai_choice'] = option_index
        self.simultaneous_data['ai_reason'] = reason
        
        # Process outcome for AI
        option = event['options'][option_index]
        
        # Use deterministic RNG
        success = self.get_deterministic_outcome(self.current_event_index, option_index, option['chance_success'])
        
        print(f"DEBUG: Outcome - Success: {success} (Chance: {option['chance_success']})")
        
        outcome = {
            'success': success,
            'option_index': option_index,
            'old_stats': self.ai_stats.copy()
        }
        
        if success:
            self.ai_stats['pop'] += option['success_reward']['pop']
            self.ai_stats['qol'] += option['success_reward']['qol']
            outcome['message'] = option['success_msg']
            outcome['result_image'] = None
        else:
            outcome['message'] = option['fail_msg']
            outcome['result_image'] = option.get('fail_image', self.config.get('game_over_image'))
            self.ai_game_over = True # Eliminated on RNG failure
            self.ai_elimination_image = outcome['result_image']
            print("DEBUG: AI Eliminated due to RNG Failure")
            
        # Check for population failure
        print(f"DEBUG: AI Stats: {self.ai_stats}")
        if self.ai_stats['pop'] <= 0:
            self.ai_game_over = True
            self.ai_elimination_image = self.config.get('game_over_image')
            print("DEBUG: AI Eliminated due to Low Population")
            if success: # If not already failed by RNG
                 outcome['message'] += " (Collapsed: Pop <= 0)"
                 outcome['result_image'] = self.config.get('game_over_image')
            
        outcome['new_stats'] = self.ai_stats.copy()
        self.simultaneous_data['ai_outcome'] = outcome

    def process_simultaneous_player_decision(self, option_index):
        """Process Player decision in simultaneous mode"""
        event = self.get_current_event()
        if not event:
            return

        self.simultaneous_data['player_choice'] = option_index
        
        # Process outcome for Player
        option = event['options'][option_index]
        
        # Use deterministic RNG
        success = self.get_deterministic_outcome(self.current_event_index, option_index, option['chance_success'])
        
        outcome = {
            'success': success,
            'option_index': option_index,
            'old_stats': self.stats.copy()
        }
        
        if success:
            self.stats['pop'] += option['success_reward']['pop']
            self.stats['qol'] += option['success_reward']['qol']
            outcome['message'] = option['success_msg']
            outcome['result_image'] = None
        else:
            outcome['message'] = option['fail_msg']
            outcome['result_image'] = option.get('fail_image', self.config.get('game_over_image'))
            self.player_game_over = True # Eliminated on RNG failure
            self.player_elimination_image = outcome['result_image']
            
        # Check for population failure
        if self.stats['pop'] <= 0:
            self.player_game_over = True
            self.player_elimination_image = self.config.get('game_over_image')
            if success:
                 outcome['message'] += " (Collapsed: Pop <= 0)"
                 outcome['result_image'] = self.config.get('game_over_image')
            
        outcome['new_stats'] = self.stats.copy()
        self.simultaneous_data['player_outcome'] = outcome
        
        # Both have decided, move to Result Display
        self.current_state = GameState.SIMULTANEOUS_RESULT_DISPLAY

    def skip_simultaneous_player_turn(self):
        """Skip player turn if eliminated"""
        self.simultaneous_data['player_choice'] = -1 # Dummy
        
        outcome = {
            'success': False,
            'option_index': -1,
            'old_stats': self.stats.copy(),
            'new_stats': self.stats.copy(),
            'message': "ELIMINATED"
        }
        self.simultaneous_data['player_outcome'] = outcome
        self.current_state = GameState.SIMULTANEOUS_RESULT_DISPLAY

    def advance_simultaneous_next_event(self):
        """Move to next event in simultaneous mode"""
        self.current_event_index += 1
        
        # Reset turn data
        self.simultaneous_data = {
            'ai_choice': None,
            'ai_reason': None,
            'player_choice': None,
            'ai_outcome': None,
            'player_outcome': None
        }

        if self.current_event_index >= len(self.events):
            # Game Over / Comparison
            # In simultaneous mode, we just show comparison at end
            # But we need to handle "Death" during game?
            # If one dies, do they stop? "Play at the same time" implies seeing who lasts longer.
            # Let's say if you die, you get GAME OVER text but maybe can watch AI?
            # For simplicity, if Player dies -> Game Over screen.
            # If AI dies -> AI stops gaining points.
            
            # Let's check death conditions here?
            # Actually, standard game over handles immediate transition.
            # For now, let's just go to Comparison if events done.
            self.ai_final_stats = self.ai_stats.copy()
            self.current_state = GameState.COMPARISON
        else:
            self.current_state = GameState.SIMULTANEOUS_EVENT_DISPLAY

