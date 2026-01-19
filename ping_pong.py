import pygame
import sys
import random
import math # Used for the pulsing animation

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
BG_COLOR = pygame.Color('grey12')
LIGHT_GREY = (200, 200, 200)
ACCENT_COLOR = pygame.Color('#45B3E7')
BALL_RADIUS = 15
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 140
WINNING_SCORE = 5

# --- Initialization ---
pygame.init()
clock = pygame.time.Clock()
pygame.mixer.init()

# --- Screen Setup ---
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption('AI Ping Pong')
# NEW: Create a separate surface for all drawing. This allows us to apply screen shake.
display_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))

# --- Game Objects ---
# Create Rects for the ball and paddles for drawing and collision
ball = pygame.Rect(SCREEN_WIDTH / 2 - BALL_RADIUS, SCREEN_HEIGHT / 2 - BALL_RADIUS, BALL_RADIUS * 2, BALL_RADIUS * 2)
player = pygame.Rect(SCREEN_WIDTH - 20 - PADDLE_WIDTH, SCREEN_HEIGHT / 2 - PADDLE_HEIGHT / 2, PADDLE_WIDTH, PADDLE_HEIGHT)
opponent = pygame.Rect(10, SCREEN_HEIGHT / 2 - PADDLE_HEIGHT / 2, PADDLE_WIDTH, PADDLE_HEIGHT)

# --- Game Variables ---
ball_speed_x = 0
ball_speed_y = 0
player_speed = 0
opponent_player_speed = 0
base_ball_speed = 7

# --- NEW: Animation Variables ---
ball_animation_timer = 0 # Controls the ball squash animation
screen_flash_timer = 0 # Controls the screen flash on score
pulse_timer = 0 # Controls the menu text pulse
particles = [] # List to store particles for hit animation
ball_trail = [] # NEW: List to store ball positions for trail effect
player_flash_timer = 0 # NEW: Timer for player paddle flash
opponent_flash_timer = 0 # NEW: Timer for opponent paddle flash
screen_shake_timer = 0 # NEW: Timer for screen shake effect
render_offset = [0, 0] # NEW: X/Y offset for screen shake

# --- AI and Game Mode Variables ---
opponent_speed = 7
difficulty_levels = ["Easy", "Medium", "Hard"]
current_difficulty_index = 1
game_modes = ["Player vs AI", "Player vs Player"]
current_mode_index = 0
ball_speed_levels = ["Slow", "Normal", "Fast"]
current_ball_speed_index = 1

# --- Menu Navigation ---
menu_selection_index = 0 # 0: Mode, 1: Difficulty, 2: Speed

# --- Text Variables ---
player_score = 0
opponent_score = 0
player_1_name = ""
player_2_name = ""
active_input_name = ""
game_font = pygame.font.Font("freesansbold.ttf", 32)
title_font = pygame.font.Font("freesansbold.ttf", 70)
small_font = pygame.font.Font("freesansbold.ttf", 28)
hint_font = pygame.font.Font("freesansbold.ttf", 20)

# --- Sound Loading ---
# Try to load sound files. If they fail, create dummy objects to prevent crashing.
try:
    pong_sound = pygame.mixer.Sound("pong.ogg")
    score_sound = pygame.mixer.Sound("score.ogg")
except pygame.error:
    print("Warning: Sound files 'pong.ogg' or 'score.ogg' not found.")
    class DummySound:
        def play(self): pass
    pong_sound = DummySound()
    score_sound = DummySound()

# --- Game State Management ---
game_state = "start_menu" # Controls which screen is active
winner_text = ""

# --- Function Definitions ---

# NEW: Particle effect functions
def spawn_particles(position):
    """Create a burst of particles at a given position."""
    for _ in range(10): # Spawn 10 particles
        particles.append({
            'pos': list(position), # [x, y]
            'vel': [random.uniform(-3, 3), random.uniform(-3, 3)], # Random velocity
            'life': random.randint(10, 20) # Lifetime in frames
        })

def update_and_draw_particles():
    """Update positions, decrease life, and draw all active particles."""
    for i in range(len(particles) - 1, -1, -1): # Iterate backwards for safe removal
        particle = particles[i]
        particle['pos'][0] += particle['vel'][0]
        particle['pos'][1] += particle['vel'][1]
        particle['life'] -= 1
        
        if particle['life'] <= 0:
            particles.pop(i)
        else:
            # Draw the particle (size shrinks as life decreases)
            size = particle['life'] * 0.5 
            pygame.draw.rect(display_surface, LIGHT_GREY, (particle['pos'][0] - size/2, particle['pos'][1] - size/2, size, size))

def ball_animation():
    """Handles ball movement, wall collisions, scoring, and paddle collisions."""
    global ball_speed_x, ball_speed_y, player_score, opponent_score, screen_flash_timer
    global ball_animation_timer, screen_shake_timer, player_flash_timer, opponent_flash_timer
    
    ball.x += ball_speed_x
    ball.y += ball_speed_y

    # Ball bounces off top and bottom walls
    if ball.top <= 0 or ball.bottom >= SCREEN_HEIGHT:
        ball_speed_y *= -1
        pong_sound.play()

    # Opponent scores
    if ball.right >= SCREEN_WIDTH:
        opponent_score += 1
        score_sound.play()
        screen_flash_timer = 15 # Trigger screen flash
        check_for_winner()
        ball_restart()

    # Player scores
    if ball.left <= 0:
        player_score += 1
        score_sound.play()
        screen_flash_timer = 15 # Trigger screen flash
        check_for_winner()
        ball_restart()

    # Ball bounces off paddles (AABB Collision)
    if ball.colliderect(player):
        ball_speed_x *= -1
        pong_sound.play()
        ball_animation_timer = 10 # Trigger ball squash animation
        spawn_particles(ball.center) # Trigger particle burst
        screen_shake_timer = 8 # NEW: Trigger screen shake
        player_flash_timer = 10 # NEW: Trigger player paddle flash
        
    if ball.colliderect(opponent):
        ball_speed_x *= -1
        pong_sound.play()
        ball_animation_timer = 10 
        spawn_particles(ball.center)
        screen_shake_timer = 8 # NEW: Trigger screen shake
        opponent_flash_timer = 10 # NEW: Trigger opponent paddle flash

def player_animation():
    """Moves the player's paddle and keeps it within the screen boundaries."""
    player.y += player_speed
    if player.top <= 0:
        player.top = 0
    if player.bottom >= SCREEN_HEIGHT:
        player.bottom = SCREEN_HEIGHT

def opponent_player_animation():
    """Moves the second player's paddle and keeps it within the screen boundaries."""
    opponent.y += opponent_player_speed
    if opponent.top <= 0:
        opponent.top = 0
    if opponent.bottom >= SCREEN_HEIGHT:
        opponent.bottom = SCREEN_HEIGHT

def opponent_ai():
    """Implements the Reactive AI Algorithm."""
    if ball_speed_x < 0:
        if opponent.centery < ball.centery:
            opponent.y += opponent_speed
        if opponent.centery > ball.centery:
            opponent.y -= opponent_speed

    if opponent.top <= 0:
        opponent.top = 0
    if opponent.bottom >= SCREEN_HEIGHT:
        opponent.bottom = SCREEN_HEIGHT

def ball_restart():
    """Resets the ball to the center and stops it, waiting for a serve."""
    global ball_speed_x, ball_speed_y
    ball.center = (SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)
    ball_speed_y = 0
    ball_speed_x = 0

def check_for_winner():
    """Checks if a player's score has reached the winning score."""
    global game_state, winner_text
    player_1_wins = player_score >= WINNING_SCORE
    player_2_wins = opponent_score >= WINNING_SCORE
    
    if player_1_wins:
        winner_name = player_1_name if game_modes[current_mode_index] == "Player vs Player" else "You"
        winner_text = f"{winner_name} Won!"
        game_state = "game_over" 
    elif player_2_wins:
        winner_name = player_2_name if game_modes[current_mode_index] == "Player vs Player" else "AI"
        winner_text = f"{winner_name} Won!"
        game_state = "game_over"

def set_difficulty():
    """Sets the AI's speed based on the menu selection."""
    global opponent_speed
    difficulty = difficulty_levels[current_difficulty_index]
    if difficulty == "Easy":
        opponent_speed = 5.5
    elif difficulty == "Medium":
        opponent_speed = 5.9
    elif difficulty == "Hard":
        opponent_speed = 7

def set_ball_speed():
    """Sets the ball's base speed based on the menu selection."""
    global base_ball_speed
    speed_level = ball_speed_levels[current_ball_speed_index]
    if speed_level == "Slow":
        base_ball_speed = 5
    elif speed_level == "Normal":
        base_ball_speed = 7
    elif speed_level == "Fast":
        base_ball_speed = 10

def reset_game():
    """Resets all game variables to start a new match."""
    global player_score, opponent_score, game_state, particles, ball_trail
    global player_flash_timer, opponent_flash_timer, screen_shake_timer
    player_score = 0
    opponent_score = 0
    particles = [] # Clear particles
    ball_trail = [] # NEW: Clear ball trail
    player_flash_timer = 0 # NEW: Reset flash timers
    opponent_flash_timer = 0
    screen_shake_timer = 0
    
    if game_modes[current_mode_index] == "Player vs AI":
        set_difficulty() 
    set_ball_speed() 
    ball_restart() 
    game_state = "playing"

def draw_back_hint():
    """Draws the 'ESC to Menu' hint."""
    back_text = hint_font.render("ESC to Menu", False, LIGHT_GREY)
    display_surface.blit(back_text, (20, SCREEN_HEIGHT - 40)) # UPDATED: Draw to display_surface

# --- Main Game Loop ---
while True:
    # --- Event Handling ---
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        # Universal ESCAPE key handler to return to menu
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if game_state in ["playing", "game_over", "enter_name_p1", "enter_name_p2"]:
                game_state = "start_menu"
                menu_selection_index = 0

        # --- State Machine Logic ---
        # 1. Handle events for the "playing" state
        if game_state == "playing":
            # Ball serve logic
            if ball_speed_x == 0 and ball_speed_y == 0:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                    ball_speed_y = -base_ball_speed
                    ball_speed_x = -base_ball_speed
            
            # Player 1 paddle movement (Arrow Keys)
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_DOWN: player_speed += 7
                if event.key == pygame.K_UP: player_speed -= 7
                # Player 2 paddle movement (W/S Keys)
                if game_modes[current_mode_index] == "Player vs Player":
                    if event.key == pygame.K_s: opponent_player_speed += 7
                    if event.key == pygame.K_w: opponent_player_speed -= 7
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_DOWN: player_speed -= 7
                if event.key == pygame.K_UP: player_speed += 7
                if game_modes[current_mode_index] == "Player vs Player":
                    if event.key == pygame.K_s: opponent_player_speed -= 7
                    if event.key == pygame.K_w: opponent_player_speed += 7
        
        # 2. Handle events for the "start_menu" state
        elif game_state == "start_menu":
            if event.type == pygame.KEYDOWN:
                # Start game or go to name entry
                if event.key == pygame.K_SPACE:
                    if game_modes[current_mode_index] == "Player vs Player":
                        game_state = "enter_name_p1"; active_input_name = ""; player_1_name = ""; player_2_name = ""
                    else: reset_game()
                # Menu navigation (UP/DOWN keys)
                if event.key == pygame.K_DOWN:
                    menu_selection_index = (menu_selection_index + 1) % 3
                    if menu_selection_index == 1 and game_modes[current_mode_index] == "Player vs Player":
                        menu_selection_index = (menu_selection_index + 1) % 3
                if event.key == pygame.K_UP:
                    menu_selection_index = (menu_selection_index - 1)
                    if menu_selection_index < 0: menu_selection_index = 2
                    if menu_selection_index == 1 and game_modes[current_mode_index] == "Player vs Player":
                        menu_selection_index = (menu_selection_index - 1)
                        if menu_selection_index < 0: menu_selection_index = 2
                # Change menu options (LEFT/RIGHT keys)
                if event.key == pygame.K_RIGHT:
                    if menu_selection_index == 0: current_mode_index = (current_mode_index + 1) % len(game_modes)
                    elif menu_selection_index == 1: current_difficulty_index = (current_difficulty_index + 1) % len(difficulty_levels)
                    elif menu_selection_index == 2: current_ball_speed_index = (current_ball_speed_index + 1) % len(ball_speed_levels)
                if event.key == pygame.K_LEFT:
                    if menu_selection_index == 0: current_mode_index = (current_mode_index - 1) % len(game_modes)
                    elif menu_selection_index == 1: current_difficulty_index = (current_difficulty_index - 1) % len(difficulty_levels)
                    elif menu_selection_index == 2: current_ball_speed_index = (current_ball_speed_index - 1) % len(ball_speed_levels)
        
        # 3. Handle events for the "enter_name" state
        elif game_state.startswith("enter_name"):
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN: # Press ENTER to confirm name
                    if game_state == "enter_name_p1" and active_input_name:
                        player_1_name = active_input_name; game_state = "enter_name_p2"; active_input_name = ""
                    elif game_state == "enter_name_p2" and active_input_name:
                        player_2_name = active_input_name; reset_game()
                elif event.key == pygame.K_BACKSPACE: # Press BACKSPACE to delete
                    active_input_name = active_input_name[:-1]
                else:
                    if len(active_input_name) < 10: # Limit name length
                        active_input_name += event.unicode # Add typed character

        # 4. Handle events for the "game_over" state
        elif game_state == "game_over":
             if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                 game_state = "start_menu"

    # --- Drawing ---
    display_surface.fill(BG_COLOR) # UPDATED: Clear the display surface

    # --- State-based Drawing ---
    # 1. Draw the "start_menu"
    if game_state == "start_menu":
        title_text = title_font.render("P I N G", False, ACCENT_COLOR); title_text_2 = title_font.render("P O N G", False, ACCENT_COLOR)
        display_surface.blit(title_text, (SCREEN_WIDTH/2 - title_text.get_width()/2, SCREEN_HEIGHT/2 - 200)); display_surface.blit(title_text_2, (SCREEN_WIDTH/2 - title_text_2.get_width()/2, SCREEN_HEIGHT/2 - 120))
        
        mode_color = ACCENT_COLOR if menu_selection_index == 0 else LIGHT_GREY; diff_color = ACCENT_COLOR if menu_selection_index == 1 else LIGHT_GREY; speed_color = ACCENT_COLOR if menu_selection_index == 2 else LIGHT_GREY
        
        mode_label = small_font.render("Mode:", False, mode_color); mode_value = small_font.render(f"< {game_modes[current_mode_index]} >", False, mode_color)
        display_surface.blit(mode_label, (SCREEN_WIDTH/2 - 150, SCREEN_HEIGHT/2 - 20)); display_surface.blit(mode_value, (SCREEN_WIDTH/2 + 30, SCREEN_HEIGHT/2 - 20))
        
        if game_modes[current_mode_index] == "Player vs AI":
            diff_label = small_font.render("Difficulty:", False, diff_color); diff_value = small_font.render(f"< {difficulty_levels[current_difficulty_index]} >", False, diff_color)
            display_surface.blit(diff_label, (SCREEN_WIDTH/2 - 150, SCREEN_HEIGHT/2 + 30)); display_surface.blit(diff_value, (SCREEN_WIDTH/2 + 30, SCREEN_HEIGHT/2 + 30))
        
        speed_label = small_font.render("Ball Speed:", False, speed_color); speed_value = small_font.render(f"< {ball_speed_levels[current_ball_speed_index]} >", False, speed_color)
        display_surface.blit(speed_label, (SCREEN_WIDTH/2 - 150, SCREEN_HEIGHT/2 + 80)); display_surface.blit(speed_value, (SCREEN_WIDTH/2 + 30, SCREEN_HEIGHT/2 + 80))
        
        # UPDATED: Pulsing/blinking text animation
        if pulse_timer % 60 < 40: # Blink on for 40 frames, off for 20
            prompt_text = game_font.render("Press SPACE to Start", False, LIGHT_GREY); 
            display_surface.blit(prompt_text, (SCREEN_WIDTH/2 - prompt_text.get_width()/2, SCREEN_HEIGHT/2 + 150))
    
    # 2. Draw the "enter_name" screen
    elif game_state.startswith("enter_name"):
        prompt = "Enter Player 1 Name:" if game_state == "enter_name_p1" else "Enter Player 2 Name:"
        prompt_text = game_font.render(prompt, False, LIGHT_GREY); display_surface.blit(prompt_text, (SCREEN_WIDTH/2 - prompt_text.get_width()/2, SCREEN_HEIGHT/2 - 100))
        input_box = pygame.Rect(SCREEN_WIDTH/2 - 150, SCREEN_HEIGHT/2 - 25, 300, 50); pygame.draw.rect(display_surface, ACCENT_COLOR, input_box, 2) 
        input_text = game_font.render(active_input_name, False, LIGHT_GREY); display_surface.blit(input_text, (input_box.x + 10, input_box.y + 10))
        continue_prompt = small_font.render("Press ENTER to continue", False, LIGHT_GREY); display_surface.blit(continue_prompt, (SCREEN_WIDTH/2 - continue_prompt.get_width()/2, SCREEN_HEIGHT/2 + 100))
        draw_back_hint()

    # 3. Draw the "game_over" screen
    elif game_state == "game_over":
        winner_render = title_font.render(winner_text, False, ACCENT_COLOR); prompt_text = game_font.render("Press SPACE to Return to Menu", False, LIGHT_GREY)
        display_surface.blit(winner_render, (SCREEN_WIDTH/2 - winner_render.get_width()/2, SCREEN_HEIGHT/2 - 100)); display_surface.blit(prompt_text, (SCREEN_WIDTH/2 - prompt_text.get_width()/2, SCREEN_HEIGHT/2 + 20))
        draw_back_hint()

    # 4. Draw the "playing" screen
    elif game_state == "playing":
        # Update game logic
        ball_animation()
        player_animation()
        if game_modes[current_mode_index] == "Player vs AI":
            opponent_ai()
        else:
            opponent_player_animation()
        
        # --- Draw game elements ---
        
        # NEW: Draw ball trail (draw first so it's behind the ball)
        for i, pos in enumerate(ball_trail):
            trail_radius = (i / len(ball_trail)) * (BALL_RADIUS * 0.5) # Trail particles shrink
            pygame.draw.circle(display_surface, ACCENT_COLOR, pos, trail_radius)

        # NEW: Draw paddles with flash effect
        player_color = LIGHT_GREY if player_flash_timer > 0 else ACCENT_COLOR
        opponent_color = LIGHT_GREY if opponent_flash_timer > 0 else ACCENT_COLOR
        if player_flash_timer > 0: player_flash_timer -= 1
        if opponent_flash_timer > 0: opponent_flash_timer -= 1
        
        pygame.draw.rect(display_surface, player_color, player)
        pygame.draw.rect(display_surface, opponent_color, opponent)
        
        # UPDATED: Draw ball with squash animation on hit
        if ball_animation_timer > 0:
            squash_rect = ball.copy()
            squash_rect.width = BALL_RADIUS * 2.5 # Make wider
            squash_rect.height = BALL_RADIUS * 1.5 # Make shorter
            squash_rect.center = ball.center # Keep it centered
            pygame.draw.ellipse(display_surface, LIGHT_GREY, squash_rect) # Draw squashed ball in white
            ball_animation_timer -= 1
        else:
            pygame.draw.ellipse(display_surface, ACCENT_COLOR, ball) # Draw normal ball
            
        pygame.draw.aaline(display_surface, LIGHT_GREY, (SCREEN_WIDTH / 2, 0), (SCREEN_WIDTH / 2, SCREEN_HEIGHT))
        
        # Draw player names in PvP
        if game_modes[current_mode_index] == "Player vs Player":
            p1_name_text = small_font.render(player_1_name, False, LIGHT_GREY)
            display_surface.blit(p1_name_text, (SCREEN_WIDTH * 0.75 - p1_name_text.get_width()/2, 20))
            p2_name_text = small_font.render(player_2_name, False, LIGHT_GREY)
            display_surface.blit(p2_name_text, (SCREEN_WIDTH * 0.25 - p2_name_text.get_width()/2, 20))
            
        # Draw scores
        player_text = game_font.render(f"{player_score}", False, LIGHT_GREY)
        display_surface.blit(player_text, (SCREEN_WIDTH/2 + 20, SCREEN_HEIGHT/2 - 16))
        opponent_text = game_font.render(f"{opponent_score}", False, LIGHT_GREY)
        display_surface.blit(opponent_text, (SCREEN_WIDTH/2 - 45, SCREEN_HEIGHT/2 - 16))
        
        # Draw serve prompt
        if ball_speed_x == 0 and ball_speed_y == 0:
            serve_text = small_font.render("Press SPACE to Serve", False, LIGHT_GREY)
            display_surface.blit(serve_text, (SCREEN_WIDTH/2 - serve_text.get_width()/2, SCREEN_HEIGHT/2 + 50))
        draw_back_hint()

        # UPDATED: Draw screen flash animation on score
        if screen_flash_timer > 0:
            flash_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
            flash_surface.set_alpha(100) # Semi-transparent
            flash_surface.fill((255, 255, 255)) # White
            display_surface.blit(flash_surface, (0, 0))
            screen_flash_timer -= 1
            
        # NEW: Update and draw all particles
        update_and_draw_particles()

        # NEW: Add ball trail logic
        ball_trail.append(ball.center)
        if len(ball_trail) > 10: # Limit trail length
            ball_trail.pop(0)

    # --- Final Screen Blit ---
    
    # NEW: Handle Screen Shake
    if screen_shake_timer > 0:
        render_offset = [random.randint(-4, 4), random.randint(-4, 4)] # Pick a random offset
        screen_shake_timer -= 1
    else:
        render_offset = [0, 0] # No offset

    # Clear the main screen
    screen.fill(BG_COLOR)
    # Draw our display surface (with all game elements) onto the main screen at the offset
    screen.blit(display_surface, render_offset)

    # Update the display
    pygame.display.flip()
    # Control the frame rate to 60 FPS
    clock.tick(60)
    
    # NEW: Increment the pulse timer every frame
    
    pulse_timer += 1

