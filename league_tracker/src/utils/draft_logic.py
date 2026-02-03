"""
Draft Mode Logic Module
Handles the different draft modes: Normal, Fearless, and Ironman
"""
from ..database import db, DraftSession, DraftGame, DraftStep


class DraftOrderGenerator:
    """Generates ban/pick order based on draft mode and game number."""
    
    @staticmethod
    def generate_ban_order(bans_per_team, game_number):
        """Generate ban order for a game.
        
        Format: 3 bans per team in phase 1 (Blue starts), 2 bans per team in phase 2 (Red starts)
        Total: 5 bans per team, 10 bans total
        """
        order = []
        
        # Phase 1: First 3 bans per team (Blue starts)
        # Blue, Red, Blue, Red, Blue, Red
        for i in range(3):
            order.append(('blue', 'ban', i + 1))
            order.append(('red', 'ban', i + 1))
        
        # Phase 2: Last 2 bans per team (Red starts to balance)
        # Red, Blue, Red, Blue
        for i in range(2):
            phase2_num = i + 4  # Continue numbering: 4, 5
            order.append(('red', 'ban', phase2_num))
            order.append(('blue', 'ban', phase2_num))
        
        return order
    
    @staticmethod
    def generate_pick_order(picks_per_team, game_number, draft_mode='normal'):
        """Generate pick order for a game.
        
        Format: 3 picks per team in phase 1 (Blue starts), 2 picks per team in phase 2 (Red starts)
        Total: 5 picks per team, 10 picks total
        """
        order = []
        
        # Phase 1: First 3 picks per team (Blue starts)
        # Blue, Red, Red, Blue, Blue, Red
        order.append(('blue', 'pick', 1))  # Blue pick 1
        order.append(('red', 'pick', 1))   # Red pick 1
        order.append(('red', 'pick', 2))   # Red pick 2
        order.append(('blue', 'pick', 2))  # Blue pick 2
        order.append(('blue', 'pick', 3))  # Blue pick 3
        order.append(('red', 'pick', 3))   # Red pick 3
        
        # Phase 2: Last 2 picks per team (Red starts to balance)
        # Red, Blue, Blue, Red (Red ends with last pick)
        order.append(('red', 'pick', 4))   # Red pick 4
        order.append(('blue', 'pick', 4))  # Blue pick 4
        order.append(('blue', 'pick', 5))  # Blue pick 5
        order.append(('red', 'pick', 5))   # Red pick 5 (last)
        
        return order
    
    @staticmethod
    def get_full_draft_order(bans_per_team, picks_per_team, game_number, draft_mode='normal'):
        """Get the complete draft order (bans + picks)."""
        ban_order = DraftOrderGenerator.generate_ban_order(bans_per_team, game_number)
        pick_order = DraftOrderGenerator.generate_pick_order(
            picks_per_team, 
            game_number, 
            draft_mode
        )
        
        # Interleave: all bans first, then all picks
        return ban_order + pick_order


class DraftModeValidator:
    """Validates draft actions based on the current draft mode."""
    
    def __init__(self, session, game, team_color):
        self.session = session
        self.game = game
        self.team_color = team_color
    
    def can_pick_champion(self, champion_id, player_id=None, position=None):
        """Check if a champion can be picked based on draft mode rules."""
        draft_mode = self.session.draft_mode
        
        if draft_mode == 'normal':
            return self._can_pick_normal(champion_id)
        elif draft_mode == 'fearless':
            return self._can_pick_fearless(champion_id)
        elif draft_mode == 'ironman':
            return self._can_pick_ironman(champion_id, player_id, position)
        
        return False
    
    def can_ban_champion(self, champion_id):
        """Check if a champion can be banned."""
        # In normal mode, all champions can be banned
        # In fearless mode, consider unavailable champions from previous games
        draft_mode = self.session.draft_mode
        
        if draft_mode == 'fearless':
            unavailable = self.game.unavailable_champions or []
            return champion_id not in unavailable
        elif draft_mode == 'ironman':
            # Ironman also respects fearless rules
            unavailable = self.game.unavailable_champions or []
            return champion_id not in unavailable
        
        return True
    
    def _can_pick_normal(self, champion_id):
        """Normal mode: can pick any champion not already picked."""
        picks_blue = self.game.picks_blue or []
        picks_red = self.game.picks_red or []
        bans_blue = self.game.bans_blue or []
        bans_red = self.game.bans_red or []
        
        # Check if champion_id is already taken (in bans or picks)
        all_taken = picks_blue + picks_red + bans_blue + bans_red
        return champion_id not in all_taken
    
    def _can_pick_fearless(self, champion_id):
        """Fearless mode: cannot pick champions used in previous games."""
        # First check current game
        if not self._can_pick_normal(champion_id):
            return False
        
        # Then check unavailable from previous games
        unavailable = self.game.unavailable_champions or []
        return champion_id not in unavailable
    
    def _can_pick_ironman(self, champion_id, player_id, position):
        """Ironman mode: each player must pick a champion they can play."""
        # First check fearless rules
        if not self._can_pick_fearless(champion_id):
            return False
        
        # Ironman specific: validate player can play the champion
        # This would typically check player champion mastery history
        # For now, we'll allow any champion but log the assignment
        return True
    
    def get_available_champions(self, player_id=None, position=None):
        """Get list of available champions for current draft state."""
        draft_mode = self.session.draft_mode
        
        if draft_mode == 'normal':
            return self._get_available_normal()
        elif draft_mode == 'fearless':
            return self._get_available_fearless()
        elif draft_mode == 'ironman':
            return self._get_available_ironman(player_id, position)
        
        return []
    
    def _get_available_normal(self):
        """Get available champions for normal mode."""
        from .champions import get_all_champions, CHAMPIONS
        
        picks_blue = set(self.game.picks_blue or [])
        picks_red = set(self.game.picks_red or [])
        bans_blue = set(self.game.bans_blue or [])
        bans_red = set(self.game.bans_red or [])
        
        taken = picks_blue | picks_red | bans_blue | bans_red
        
        return [c for c in get_all_champions() if c['id'] not in taken]
    
    def _get_available_fearless(self):
        """Get available champions for fearless mode."""
        available = self._get_available_normal()
        unavailable = set(self.game.unavailable_champions or [])
        
        return [c for c in available if c['id'] not in unavailable]
    
    def _get_available_ironman(self, player_id, position):
        """Get available champions for ironman mode."""
        from .champions import get_all_champions, get_position_champions
        
        available = self._get_available_fearless()
        
        # Filter by position if specified
        if position:
            position_champions = {c['id'] for c in get_position_champions(position)}
            available = [c for c in available if c['id'] in position_champions]
        
        return available


class DraftSessionManager:
    """Manages draft session operations."""
    
    @staticmethod
    def generate_game_links(session_id, game_number):
        """Generate unique web links for blue side, red side, and spectator."""
        import uuid
        # Use relative URL so it works with the current app domain
        base_url = "/game"
        
        # Generate unique tokens for each link
        blue_token = str(uuid.uuid4())[:8]
        red_token = str(uuid.uuid4())[:8]
        spectator_token = str(uuid.uuid4())[:8]
        
        blue_link = f"{base_url}/{session_id}/{game_number}/blue/{blue_token}"
        red_link = f"{base_url}/{session_id}/{game_number}/red/{red_token}"
        spectator_link = f"{base_url}/{session_id}/{game_number}/spectator/{spectator_token}"
        
        return {
            'blue_side_link': blue_link,
            'red_side_link': red_link,
            'spectator_link': spectator_link
        }
    
    @staticmethod
    def create_session(name, draft_mode, team_blue_id, team_red_id, 
                       bans_per_team=5, picks_per_team=5):
        """Create a new draft session."""
        from datetime import datetime
        
        # Find captains for each team
        from ..database import team_players
        blue_captain = None
        red_captain = None
        
        # Get blue team captain
        blue_assignment = db.session.query(team_players).filter(
            team_players.c.team_id == team_blue_id,
            team_players.c.is_captain == True
        ).first()
        if blue_assignment:
            blue_captain = blue_assignment.player_id
        
        # Get red team captain
        red_assignment = db.session.query(team_players).filter(
            team_players.c.team_id == team_red_id,
            team_players.c.is_captain == True
        ).first()
        if red_assignment:
            red_captain = red_assignment.player_id
        
        session = DraftSession(
            name=name,
            draft_mode=draft_mode,
            team_blue_id=team_blue_id,
            team_red_id=team_red_id,
            bans_per_team=bans_per_team,
            picks_per_team=picks_per_team,
            blue_captain_id=blue_captain,
            red_captain_id=red_captain,
            timer_started_at=None,  # Timer starts when both teams are ready
            timer_duration=30
        )
        db.session.add(session)
        db.session.flush()
        
        # Create first game with links
        DraftSessionManager._create_game(session.id, 1)
        
        db.session.commit()
        return session
    
    @staticmethod
    def _create_game(session_id, game_number):
        """Create a new draft game for a session."""
        # Generate unique links for this game
        links = DraftSessionManager.generate_game_links(session_id, game_number)
        
        game = DraftGame(
            session_id=session_id,
            game_number=game_number,
            bans_blue=[],
            bans_red=[],
            picks_blue=[],
            picks_red=[],
            unavailable_champions=[],
            ironman_assignments={},
            blue_side_link=links['blue_side_link'],
            red_side_link=links['red_side_link'],
            spectator_link=links['spectator_link'],
            blue_ready=False,
            red_ready=False,
            match_started=False,
            match_started_at=None,
            is_completed=False
        )
        db.session.add(game)
        db.session.flush()
        return game
    
    @staticmethod
    def is_team_captain(session_id, team_color, player_id):
        """Check if a player is the captain for their team."""
        session = DraftSession.query.get(session_id)
        if not session:
            return False
        
        if team_color == 'blue':
            return session.blue_captain_id == player_id
        elif team_color == 'red':
            return session.red_captain_id == player_id
        return False
    
    @staticmethod
    def can_player_act(session_id, team_color):
        """Check if the current team can act (only captain can act)."""
        session = DraftSession.query.get(session_id)
        if not session:
            return False
        
        # For now, allow any player on the team to act (captain system can be enhanced)
        # In a full implementation, we'd track which player is logged in
        return True
    
    @staticmethod
    def execute_action(session_id, action_type, champion_id, team_color, 
                       player_id=None, position=None):
        """Execute a ban or pick action."""
        from datetime import datetime
        
        # Use a new query to get fresh data
        session = db.session.get(DraftSession, session_id)
        if not session:
            raise ValueError("Draft session not found")
        
        game = db.session.query(DraftGame).filter_by(
            session_id=session_id,
            game_number=session.current_game_number
        ).first()
        if not game:
            raise ValueError("Current game not found")
        
        # Check if match has started (both teams ready)
        if not game.match_started:
            raise ValueError("Match has not started yet - waiting for both teams to be ready")
        
        # Refresh to ensure we have latest data
        db.session.refresh(game)
        
        # Validate action
        validator = DraftModeValidator(session, game, team_color)
        
        if action_type == 'ban':
            if not validator.can_ban_champion(champion_id):
                raise ValueError("Champion cannot be banned - already banned or picked")
        elif action_type == 'pick':
            if not validator.can_pick_champion(champion_id, player_id, position):
                raise ValueError("Champion cannot be picked - already picked or banned")
        
        # Record the step
        step = DraftStep(
            session_id=session_id,
            game_number=session.current_game_number,
            step_number=session.step_number,
            step_type=action_type,
            team=team_color,
            champion_id=champion_id,
            position=position,
            player_id=player_id
        )
        db.session.add(step)
        
        # Update game state - create new lists to ensure changes are detected
        if team_color == 'blue':
            if action_type == 'ban':
                current_bans = list(game.bans_blue) if game.bans_blue else []
                current_bans.append(champion_id)
                game.bans_blue = current_bans
            else:
                current_picks = list(game.picks_blue) if game.picks_blue else []
                current_picks.append({'champion_id': champion_id})
                game.picks_blue = current_picks
        else:
            if action_type == 'ban':
                current_bans = list(game.bans_red) if game.bans_red else []
                current_bans.append(champion_id)
                game.bans_red = current_bans
            else:
                current_picks = list(game.picks_red) if game.picks_red else []
                current_picks.append({'champion_id': champion_id})
                game.picks_red = current_picks
        
        # Update session state
        DraftSessionManager._advance_session_state(session, game)
        
        db.session.commit()
        
        return {
            'step': step.to_dict(),
            'session': session.to_dict(),
            'game': game.to_dict()
        }
    
    @staticmethod
    def set_team_ready(session_id, game_number, team_color):
        """Set a team as ready for the match to begin."""
        from datetime import datetime
        
        session = DraftSession.query.get(session_id)
        if not session:
            raise ValueError("Draft session not found")
        
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=game_number
        ).first()
        if not game:
            raise ValueError("Game not found")
        
        # Set the ready status
        if team_color == 'blue':
            game.blue_ready = True
        elif team_color == 'red':
            game.red_ready = True
        else:
            raise ValueError("Invalid team color")
        
        # Check if both teams are ready
        if game.blue_ready and game.red_ready and not game.match_started:
            game.match_started = True
            game.match_started_at = datetime.utcnow()
            # Start the draft timer
            session.timer_started_at = datetime.utcnow()
        
        db.session.commit()
        return game
    
    @staticmethod
    def _advance_session_state(session, game):
        """Advance the draft session to the next step."""
        from datetime import datetime
        
        # Don't advance if match hasn't started yet
        if not game.match_started:
            return
        
        ban_order = DraftOrderGenerator.generate_ban_order(session.bans_per_team, session.current_game_number)
        pick_order = DraftOrderGenerator.generate_pick_order(
            session.picks_per_team, 
            session.current_game_number, 
            session.draft_mode
        )
        
        full_order = ban_order + pick_order
        
        # Current step should be session.step_number
        current_step_num = session.step_number
        
        if current_step_num >= len(full_order):
            # Draft complete for this game
            game.is_completed = True
            
            # Check if there are more games in the series
            if session.current_game_number < 3:  # Best of 3
                session.current_game_number += 1
                session.step_number = 1
                session.current_phase = 'bans'
                session.current_team_turn = 'blue'
                session.timer_started_at = None  # Reset timer - will start when both teams ready
                
                # Create new game with links
                DraftSessionManager._create_game(session.id, session.current_game_number)
            else:
                # Series complete
                session.is_active = False
                session.completed_at = db.func.current_timestamp()
                session.timer_started_at = None
        else:
            # Advance to next step
            session.step_number += 1
            next_step = full_order[current_step_num]
            session.current_team_turn = next_step[0]
            
            # Update phase if we've moved to picks
            if len(ban_order) == current_step_num:
                session.current_phase = 'picks'
            
            # Reset timer for next turn
            session.timer_started_at = datetime.utcnow()
    
    @staticmethod
    def get_session_state(session_id):
        """Get the current state of a draft session."""
        session = DraftSession.query.get(session_id)
        if not session:
            return None
        
        # Refresh session from database to ensure we have latest data
        db.session.refresh(session)
        
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=session.current_game_number
        ).first()
        
        # Refresh game from database to ensure we have latest data
        if game:
            db.session.refresh(game)
        
        steps = DraftStep.query.filter_by(
            session_id=session_id,
            game_number=session.current_game_number
        ).order_by(DraftStep.step_number).all()
        
        return {
            'session': session.to_dict(),
            'game': game.to_dict() if game else None,
            'steps': [s.to_dict() for s in steps],
            'ban_order': DraftOrderGenerator.generate_ban_order(session.bans_per_team, session.current_game_number),
            'pick_order': DraftOrderGenerator.generate_pick_order(
                session.picks_per_team, 
                session.current_game_number, 
                session.draft_mode
            )
        }
    
    @staticmethod
    def reset_game(session_id, game_number):
        """Reset a game to start fresh."""
        session = DraftSession.query.get(session_id)
        game = DraftGame.query.filter_by(
            session_id=session_id,
            game_number=game_number
        ).first()
        
        if game:
            # Delete all steps for this game
            DraftStep.query.filter_by(
                session_id=session_id,
                game_number=game_number
            ).delete()
            
            # Reset game state
            game.bans_blue = []
            game.bans_red = []
            game.picks_blue = []
            game.picks_red = []
            game.ironman_assignments = {}
            game.is_completed = False
            
            # Reset session state
            session.step_number = 1
            session.current_phase = 'bans'
            session.current_team_turn = 'blue'
            
            db.session.commit()
        
        return game
    
    @staticmethod
    def get_series_history(session_id):
        """Get the complete history of all games in a series."""
        games = DraftGame.query.filter_by(
            session_id=session_id
        ).order_by(DraftGame.game_number).all()
        
        history = []
        for game in games:
            steps = DraftStep.query.filter_by(
                session_id=session_id,
                game_number=game.game_number
            ).order_by(DraftStep.step_number).all()
            
            history.append({
                'game_number': game.game_number,
                'is_completed': game.is_completed,
                'bans_blue': game.bans_blue,
                'bans_red': game.bans_red,
                'picks_blue': game.picks_blue,
                'picks_red': game.picks_red,
                'steps': [s.to_dict() for s in steps]
            })
        
        return history
