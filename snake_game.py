import os
import msvcrt
import random
import time
import sys

# Game constants
WIDTH = 20
HEIGHT = 20
SPEED = 0.2  # seconds between updates

# Direction constants
UP = (0, -1)
DOWN = (0, 1)
LEFT = (-1, 0)
RIGHT = (1, 0)

class SnakeGame:
    def __init__(self):
        self.reset_game()
        
    def reset_game(self):
        # Initialize snake (head is at index 0)
        self.snake = [(WIDTH // 2, HEIGHT // 2)]
        self.direction = RIGHT
        self.score = 0
        self.food = self.spawn_food()
        self.game_over = False
    
    def spawn_food(self):
        while True:
            food = (random.randint(0, WIDTH - 1), random.randint(0, HEIGHT - 1))
            if food not in self.snake:
                return food
    
    def update(self):
        if self.game_over:
            return
            
        # Calculate new head position
        head_x, head_y = self.snake[0]
        dir_x, dir_y = self.direction
        new_x = (head_x + dir_x) % WIDTH
        new_y = (head_y + dir_y) % HEIGHT
        new_head = (new_x, new_y)
        
        # Check collision with self
        if new_head in self.snake:
            self.game_over = True
            return
            
        # Check collision with walls
        if (new_x < 0 or new_x >= WIDTH or 
            new_y < 0 or new_y >= HEIGHT):
            self.game_over = True
            return
        
        # Add new head
        self.snake.insert(0, new_head)
        
        # Check if snake ate food
        if new_head == self.food:
            self.score += 1
            self.food = self.spawn_food()
        else:
            # Remove tail (snake didn't grow)
            self.snake.pop()
    
    def change_direction(self, new_direction):
        # Prevent 180-degree turns
        if ((new_direction == UP and self.direction == DOWN) or
            (new_direction == DOWN and self.direction == UP) or
            (new_direction == LEFT and self.direction == RIGHT) or
            (new_direction == RIGHT and self.direction == LEFT)):
            return
        
        self.direction = new_direction
    
    def draw(self):
        # Clear the screen
        os.system('cls')
        
        # Create empty board
        board = [[' ' for _ in range(WIDTH)] for _ in range(HEIGHT)]
        
        # Add snake to board
        for i, (x, y) in enumerate(self.snake):
            if i == 0:
                board[y][x] = 'O'  # Head
            else:
                board[y][x] = 'o'  # Body
        
        # Add food to board
        food_x, food_y = self.food
        board[food_y][food_x] = '*'
        
        # Draw the board with border
        print('┌' + '─' * WIDTH + '┐')
        for row in board:
            print('│' + ''.join(row) + '│')
        print('└' + '─' * WIDTH + '┘')
        
        # Draw score
        print(f"Score: {self.score}")
        
        if self.game_over:
            print("Game Over! Press 'r' to restart or 'q' to quit.")
        else:
            print("Use WASD or arrow keys to move, 'q' to quit")

def main():
    game = SnakeGame()
    last_update = time.time()
    
    while True:
        # Draw the current state
        game.draw()
        
        # Check for key presses
        if msvcrt.kbhit():
            key = msvcrt.getch()
            
            # Check key value and handle accordingly
            if key == b'q':  # Quit game
                return
            elif key == b'r' and game.game_over:  # Restart game
                game.reset_game()
            elif key == b'w' or key == b'H':  # Up (w or up arrow)
                game.change_direction(UP)
            elif key == b's' or key == b'P':  # Down (s or down arrow)
                game.change_direction(DOWN)
            elif key == b'a' or key == b'K':  # Left (a or left arrow)
                game.change_direction(LEFT)
            elif key == b'd' or key == b'M':  # Right (d or right arrow)
                game.change_direction(RIGHT)
            elif key == b'\xe0':  # Arrow keys prefix
                # This handles arrow keys which produce two bytes
                arrow_key = msvcrt.getch()
                if arrow_key == b'H':  # Up arrow
                    game.change_direction(UP)
                elif arrow_key == b'P':  # Down arrow
                    game.change_direction(DOWN)
                elif arrow_key == b'K':  # Left arrow
                    game.change_direction(LEFT)
                elif arrow_key == b'M':  # Right arrow
                    game.change_direction(RIGHT)
        
        # Update game state at fixed intervals
        current_time = time.time()
        if current_time - last_update >= SPEED and not game.game_over:
            game.update()
            last_update = current_time
        
        # Sleep to reduce CPU usage
        time.sleep(0.05)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")

