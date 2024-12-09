import pygame, sys, random, mysql.connector
from mysql.connector import Error

# Kết nối tới MySQL
def get_db_connection():
    try:
        connection = mysql.connector.connect(
            host="localhost",
            user="root",
            passwd="12345a.",
            database="gamedatabase"
        )
        print("Kết nối tới MySQL thành công")
        return connection
    except Error as e:
        print(f"Lỗi kết nối MySQL: {e}")
        return None

# Lấy điểm cao từ cơ sở dữ liệu
def get_high_score(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT player_name, MAX(score) FROM high_scores GROUP BY player_name ORDER BY MAX(score) DESC LIMIT 1")
    result = cursor.fetchone()
    return result if result else ("", 0)

# Lưu điểm vào cơ sở dữ liệu
def save_score(connection, name, score):
    cursor = connection.cursor()
    
    cursor.execute("SELECT score FROM high_scores WHERE player_name = %s", (name,))
    result = cursor.fetchone()
    
    if result:
        current_high_score = result[0]
        if score > current_high_score:
            update_query = "UPDATE high_scores SET score = %s WHERE player_name = %s"
            cursor.execute(update_query, (score, name))
    else:
        insert_query = "INSERT INTO high_scores (player_name, score) VALUES (%s, %s)"
        cursor.execute(insert_query, (name, score))
    
    connection.commit()

# Lấy tất cả điểm số từ cơ sở dữ liệu
def get_all_scores(connection):
    cursor = connection.cursor()
    cursor.execute("SELECT player_name, score FROM high_scores ORDER BY score DESC")
    results = cursor.fetchall()
    return results

db_connection = get_db_connection()

if db_connection:
    high_score_name, high_score = get_high_score(db_connection)
else:
    high_score_name, high_score = ("", 0)

pygame.init()
screen = pygame.display.set_mode((432, 768))
clock = pygame.time.Clock()
game_font = pygame.font.Font('04B_19.ttf', 35)

WHITE = (255, 255, 255)

gravity = 0.15
bird_movement = 0
game_active = False
score = 0
name_input_active = True
player_name = ""

bg = pygame.image.load('assets/background-night.png').convert()
bg = pygame.transform.scale2x(bg)

floor = pygame.image.load('assets/floor.png').convert()
floor = pygame.transform.scale2x(floor)
floor_x_pos = 0

bird_downflap = pygame.transform.scale2x(pygame.image.load('assets/yellowbird-downflap.png').convert_alpha())
bird_midflap = pygame.transform.scale2x(pygame.image.load('assets/yellowbird-midflap.png').convert_alpha())
bird_upflap = pygame.transform.scale2x(pygame.image.load('assets/yellowbird-upflap.png').convert_alpha())
bird_frames = [bird_downflap, bird_midflap, bird_upflap]
bird_index = 0
bird = bird_frames[bird_index]
bird_rect = bird.get_rect(center=(100, 384))

pipe_surface = pygame.image.load('assets/pipe-green.png').convert()
pipe_surface = pygame.transform.scale2x(pipe_surface)
pipe_list = []
MAX_PIPES = 4

game_over_surface = pygame.transform.scale2x(pygame.image.load('assets/message.png').convert_alpha())
game_over_rect = game_over_surface.get_rect(center=(216, 384))

spawnpipe = pygame.USEREVENT
pygame.time.set_timer(spawnpipe, 3000)

birdflap = pygame.USEREVENT + 1
pygame.time.set_timer(birdflap, 200)

flap_sound = pygame.mixer.Sound('sound/sfx_wing.wav')
hit_sound = pygame.mixer.Sound('sound/sfx_hit.wav')
score_sound = pygame.mixer.Sound('sound/sfx_point.wav')
score_sound_countdown = 100

def draw_floor():
    screen.blit(floor, (floor_x_pos, 650))
    screen.blit(floor, (floor_x_pos + 432, 650))

def create_pipe():
    
    # Định nghĩa kích thước màn hình
    SCREEN_HEIGHT = 768
    SCREEN_WIDTH = 432
    
    # Định nghĩa kích thước ống
    PIPE_WIDTH = pipe_surface.get_width()
    PIPE_HEIGHT = pipe_surface.get_height()
    
    # Định nghĩa khoảng trống giữa các ống (có thể điều chỉnh)
    GAP_SIZE = random.randint(150, 250)
    
    # Vị trí ngẫu nhiên cho khoảng trống
    gap_y = random.randint(200, SCREEN_HEIGHT - 200 - GAP_SIZE)
    
    # Tạo ống dưới
    bottom_pipe = pipe_surface.get_rect(midtop=(SCREEN_WIDTH + PIPE_WIDTH, gap_y + GAP_SIZE))
    
    # Tạo ống trên
    top_pipe = pipe_surface.get_rect(midbottom=(SCREEN_WIDTH + PIPE_WIDTH, gap_y))
    
    return bottom_pipe, top_pipe

def move_pipe(pipes):
    for pipe in pipes:
        pipe.centerx -= 3
    return [pipe for pipe in pipes if pipe.right > -50]

def draw_pipe(pipes):
    for pipe in pipes:
        if pipe.bottom >= 600:
            screen.blit(pipe_surface, pipe)
        else:
            flip_pipe = pygame.transform.flip(pipe_surface, False, True)
            screen.blit(flip_pipe, pipe)

def check_collision(pipes):
    for pipe in pipes:
        if bird_rect.colliderect(pipe):
            hit_sound.play()
            return False
    if bird_rect.top <= -75 or bird_rect.bottom >= 650:
        hit_sound.play()
        return False
    return True

def rotate_bird(bird):
    new_bird = pygame.transform.rotozoom(bird, -bird_movement * 3, 1)
    return new_bird

def bird_animation():
    new_bird = bird_frames[bird_index]
    new_bird_rect = new_bird.get_rect(center=(100, bird_rect.centery))
    return new_bird, new_bird_rect

def update_score(score, high_score):
    if score > high_score:
        high_score = score
    return high_score

def score_display(game_state):
    if game_state == 'main game':
        score_surface = game_font.render(str(int(score)), True, WHITE)
        score_rect = score_surface.get_rect(center=(216, 100))
        screen.blit(score_surface, score_rect)
    if game_state == 'game_over':
        score_surface = game_font.render(f'Score: {int(score)} ({player_name})', True, WHITE)
        score_rect = score_surface.get_rect(center=(216, 100))
        screen.blit(score_surface, score_rect)
        high_score_surface = game_font.render(f'High score: {int(high_score)} ({high_score_name})', True, WHITE)
        high_score_rect = high_score_surface.get_rect(center=(216, 630))
        screen.blit(high_score_surface, high_score_rect)

while True:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            if db_connection:
                db_connection.close()
            pygame.quit()
            sys.exit()
        
        if name_input_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif event.key == pygame.K_RETURN:
                    if player_name.strip() != "":
                        name_input_active = False
                        game_active = True
                else:
                    player_name += event.unicode

        elif game_active:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    bird_movement = 0
                    bird_movement = -4.5
                    flap_sound.play()
            if event.type == spawnpipe:
                if len(pipe_list) < MAX_PIPES * 2:
                    pipe_list.extend(create_pipe())
            if event.type == birdflap:
                if bird_index < 2:
                    bird_index += 1
                else:
                    bird_index = 0
                bird, bird_rect = bird_animation()

        else:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                game_active = True
                pipe_list.clear()
                bird_rect.center = (100, 384)
                bird_movement = 0
                score = 0

    screen.blit(bg, (0, 0))


    if name_input_active:
        name_surface = game_font.render('Enter your name:', True, WHITE)
        name_rect = name_surface.get_rect(center=(216, 200))
        screen.blit(name_surface, name_rect)

        name_input_surface = game_font.render(player_name, True, WHITE)
        name_input_rect = name_input_surface.get_rect(center=(216, 300))
        screen.blit(name_input_surface, name_input_rect)

    elif game_active:
        bird_movement += gravity
        rotated_bird = rotate_bird(bird)
        bird_rect.centery += bird_movement
        screen.blit(rotated_bird, bird_rect)
        game_active = check_collision(pipe_list)

        pipe_list = move_pipe(pipe_list)
        draw_pipe(pipe_list)

        score += 0.01
        score_display('main game')
        score_sound_countdown -= 1
        if score_sound_countdown <= 0:
            score_sound.play()
            score_sound_countdown = 100
    else:
        screen.blit(game_over_surface, game_over_rect)
        
        high_score = update_score(score, high_score)
        
        if db_connection and player_name.strip():
            save_score(db_connection, player_name, score)
        
        score_display('game_over')
        high_score_surface = game_font.render(f'High score: {int(high_score)} ({high_score_name})', True, WHITE)
        high_score_rect = high_score_surface.get_rect(center=(216, 630))
        screen.blit(high_score_surface, high_score_rect)

    floor_x_pos -= 3
    draw_floor()
    if floor_x_pos <= -432:
        floor_x_pos = 0

  

    pygame.display.update()
    clock.tick(120)