import cv2
import time
import random
import os
import numpy as np
import pygame

try:
    from mediapipe.python.solutions import hands as mp_hands
    from mediapipe.python.solutions import drawing_utils as mp_draw
    from mediapipe.python.solutions import drawing_styles as mp_styles
except Exception:
    import mediapipe as mp
    mp_hands = mp.solutions.hands
    mp_draw = mp.solutions.drawing_utils
    mp_styles = mp.solutions.drawing_styles


# ================== SETUP ==================
WIDTH, HEIGHT = 1280, 720
ASSETS        = "assets"
WINDOW_NAME   = "Rock Paper Scissors AI"
CHOICES       = ["Rock", "Paper", "Scissors"]
WIN_SCORE     = 3

# IMPORTANT FIX
pygame.init()
pygame.mixer.init()

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption(WINDOW_NAME)

# ─────────── Colour Palette ───────────
BG_DARK      = (8, 10, 20)
BG_CARD      = (20, 25, 45)
NEON_CYAN    = (0, 230, 255)
NEON_PINK    = (255, 20, 147)
NEON_GREEN   = (57, 255, 20)
NEON_ORANGE  = (255, 140, 0)
NEON_PURPLE  = (180, 0, 255)
GOLD         = (255, 215, 0)
WHITE        = (255, 255, 255)
GREY_LIGHT   = (160, 170, 200)
GREY_MID     = (80, 90, 120)
RED_NEON     = (255, 50, 50)

CHOICE_COLORS = {
    "Rock": NEON_ORANGE,
    "Paper": NEON_CYAN,
    "Scissors": NEON_GREEN,
}

# ─────────── Sounds ───────────
def load_sound(name):
    path = os.path.join(ASSETS, name)
    try:
        return pygame.mixer.Sound(path)
    except Exception:
        return None

SND_WIN   = load_sound("win.wav")
SND_LOSE  = load_sound("lose.wav")
SND_DRAW  = load_sound("draw.wav")
SND_START = load_sound("start.wav")

def play(snd):
    if snd:
        snd.play()

bg_music_path = os.path.join(ASSETS, "bg_music.mp3")
if os.path.exists(bg_music_path):
    pygame.mixer.music.load(bg_music_path)
    pygame.mixer.music.set_volume(0.25)
    pygame.mixer.music.play(-1)

# ─────────── Assets ───────────
def load_choice_img(name, size=(210, 210)):
    path = os.path.join(ASSETS, f"{name.lower()}.png")
    if os.path.exists(path):
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.smoothscale(img, size)

    surf = pygame.Surface(size, pygame.SRCALPHA)
    pygame.draw.rect(
        surf,
        CHOICE_COLORS.get(name, WHITE),
        surf.get_rect(),
        border_radius=18
    )
    return surf

CHOICE_IMGS = {c: load_choice_img(c) for c in CHOICES}

# ─────────── Fonts ───────────
def font(size, bold=False):
    return pygame.font.SysFont("Segoe UI", size, bold=bold)

F_HUGE   = font(90, bold=True)
F_BIG    = font(60, bold=True)
F_MED    = font(38, bold=True)
F_SMALL  = font(26)
F_TINY   = font(20)

# ─────────── Drawing Helpers ───────────
def draw_text(surf, text, f, color, cx, cy, anchor="center"):
    s = f.render(str(text), True, color)
    r = s.get_rect()
    if anchor == "center":
        r.center = (cx, cy)
    elif anchor == "midleft":
        r.midleft = (cx, cy)
    surf.blit(s, r)
    return r

def glow_rect(surf, color, rect, radius=14, alpha=80, layers=4):
    for i in range(layers, 0, -1):
        g = pygame.Surface((rect[2] + i * 10, rect[3] + i * 10), pygame.SRCALPHA)
        a = max(10, alpha - i * 18)
        pygame.draw.rect(g, (*color, a), g.get_rect(), border_radius=radius + i * 3)
        surf.blit(g, (rect[0] - i * 5, rect[1] - i * 5))
    pygame.draw.rect(surf, color, rect, 2, border_radius=radius)

def glow_circle(surf, color, center, radius, width=2, layers=3):
    for i in range(layers, 0, -1):
        g = pygame.Surface((radius * 2 + i * 16, radius * 2 + i * 16), pygame.SRCALPHA)
        pygame.draw.circle(
            g,
            (*color, max(15, 60 - i * 18)),
            (radius + i * 8, radius + i * 8),
            radius + i * 4
        )
        surf.blit(g, (center[0] - radius - i * 8, center[1] - radius - i * 8))
    pygame.draw.circle(surf, color, center, radius, width)

def draw_neon_panel(surf, rect, color, radius=16):
    panel = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
    pygame.draw.rect(panel, (*BG_CARD, 210), panel.get_rect(), border_radius=radius)
    surf.blit(panel, (rect[0], rect[1]))
    glow_rect(surf, color, rect, radius)

def draw_progress_bar(surf, x, y, w, h, val, mx, color):
    bg = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.rect(bg, (*GREY_MID, 80), bg.get_rect(), border_radius=h // 2)
    surf.blit(bg, (x, y))

    if val > 0:
        fw = int(w * min(val / mx, 1))
        fg = pygame.Surface((fw, h), pygame.SRCALPHA)
        pygame.draw.rect(fg, (*color, 220), fg.get_rect(), border_radius=h // 2)
        surf.blit(fg, (x, y))

def scanlines(surf, alpha=18):
    for yy in range(0, HEIGHT, 4):
        s = pygame.Surface((WIDTH, 1), pygame.SRCALPHA)
        s.fill((0, 0, 0, alpha))
        surf.blit(s, (0, yy))

def draw_grid(surf):
    for xx in range(0, WIDTH, 80):
        pygame.draw.line(surf, (*NEON_CYAN, 8), (xx, 0), (xx, HEIGHT))
    for yy in range(0, HEIGHT, 80):
        pygame.draw.line(surf, (*NEON_CYAN, 8), (0, yy), (WIDTH, yy))

# ─────────── Particle System ───────────
class Particle:
    def __init__(self, x, y, color):
        self.x = x + random.randint(-30, 30)
        self.y = y + random.randint(-30, 30)
        self.vx = random.uniform(-4, 4)
        self.vy = random.uniform(-6, -1)
        self.life = random.randint(30, 70)
        self.max_life = self.life
        self.r = random.randint(2, 6)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += 0.15
        self.life -= 1

    def draw(self, surf):
        ratio = self.life / self.max_life
        a = int(255 * ratio)
        s = pygame.Surface((self.r * 2 + 2, self.r * 2 + 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (*self.color, a), (self.r + 1, self.r + 1), self.r)
        surf.blit(s, (int(self.x) - self.r - 1, int(self.y) - self.r - 1))

particles = []

def burst(x, y, color, n=40):
    for _ in range(n):
        particles.append(Particle(x, y, color))

def update_particles(surf):
    for p in particles[:]:
        p.update()
        p.draw(surf)
        if p.life <= 0:
            particles.remove(p)


# ─────────── MediaPipe Setup ───────────

hands_detector = mp_hands.Hands(
    static_image_mode=False,
    max_num_hands=1,
    min_detection_confidence=0.75,
    min_tracking_confidence=0.6
)


def fingers_up(lm):
    status = []
    status.append(lm[4][0] > lm[3][0])
    for t, p in zip([8, 12, 16, 20], [6, 10, 14, 18]):
        status.append(lm[t][1] < lm[p][1])
    return status

def classify_gesture(lm):
    up = fingers_up(lm)

    if not any(up[1:]):
        return "Rock"
    if all(up[1:]):
        return "Paper"
    if up[1] and up[2] and not up[3] and not up[4]:
        return "Scissors"

    return None

def get_landmarks(frame):
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = hands_detector.process(rgb)

    if res.multi_hand_landmarks:
        lm_list = []
        for lm in res.multi_hand_landmarks[0].landmark:
            h, w = frame.shape[:2]
            lm_list.append((int(lm.x * w), int(lm.y * h)))
        return lm_list, res.multi_hand_landmarks[0]

    return None, None

# ─────────── Game Logic ───────────
def determine_winner(player, ai):
    if player == ai:
        return "Draw"

    wins = {
        ("Rock", "Scissors"),
        ("Scissors", "Paper"),
        ("Paper", "Rock")
    }

    return "Player" if (player, ai) in wins else "AI"

def ai_choose(player_history):
    if len(player_history) >= 4 and random.random() < 0.55:
        freq = {c: player_history.count(c) for c in CHOICES}
        predicted = max(freq, key=freq.get)
        counter = {
            "Rock": "Paper",
            "Paper": "Scissors",
            "Scissors": "Rock"
        }
        return counter[predicted]

    return random.choice(CHOICES)

STATE_MENU      = "MENU"
STATE_COUNTDOWN = "COUNTDOWN"
STATE_DETECT    = "DETECT"
STATE_REVEAL    = "REVEAL"
STATE_RESULT    = "RESULT"
STATE_GAMEOVER  = "GAMEOVER"

# ─────────── Main App ───────────
class RockPaperScissorsAI:
    def __init__(self):
        self.screen = screen
        self.clock = pygame.time.Clock()

        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

        self.reset_game()

        self.state = STATE_MENU
        self.menu_tick = 0
        self.result_timer = 0
        self.reveal_timer = 0
        self.reveal_frames = 40

    def reset_game(self):
        self.player_score = 0
        self.ai_score = 0
        self.round_num = 0
        self.player_choice = None
        self.ai_choice = None
        self.winner = None
        self.player_history = []
        self.countdown = 3
        self.cd_start = 0
        self.detect_start = 0
        self.detected_buf = []
        self.final_gesture = None

    def grab_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return None, None, None

        frame = cv2.flip(frame, 1)
        lm_list, lm_raw = get_landmarks(frame)
        gesture = classify_gesture(lm_list) if lm_list else None

        if lm_raw:
            mp_draw.draw_landmarks(
                frame,
                lm_raw,
                mp_hands.HAND_CONNECTIONS,
                mp_styles.get_default_hand_landmarks_style(),
                mp_styles.get_default_hand_connections_style()
            )

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        surf = pygame.surfarray.make_surface(np.rot90(rgb))
        return surf, gesture, lm_list

    def draw_camera(self, x, y, w, h, surf, gesture, lm_list):
        cam_rect = (x, y, w, h)

        if surf:
            scaled = pygame.transform.smoothscale(surf, (w, h))
            self.screen.blit(scaled, (x, y))
        else:
            pygame.draw.rect(self.screen, BG_CARD, cam_rect)

        border_col = CHOICE_COLORS.get(gesture, GREY_MID) if gesture else GREY_MID
        glow_rect(self.screen, border_col, cam_rect, radius=12)

        if gesture:
            bw, bh = 160, 40
            bx = x + w // 2 - bw // 2
            by = y + h - 10
            draw_neon_panel(self.screen, (bx, by, bw, bh), CHOICE_COLORS[gesture], radius=10)
            draw_text(self.screen, gesture.upper(), F_SMALL, CHOICE_COLORS[gesture], bx + bw // 2, by + bh // 2)

    def draw_scoreboard(self):
        px, py, pw, ph = WIDTH // 2 - 200, 10, 400, 80
        draw_neon_panel(self.screen, (px, py, pw, ph), NEON_PURPLE, radius=14)

        draw_text(self.screen, str(self.player_score), F_BIG, NEON_CYAN, px + 80, py + 40)
        draw_text(self.screen, "VS", F_MED, GREY_LIGHT, px + 200, py + 42)
        draw_text(self.screen, str(self.ai_score), F_BIG, NEON_PINK, px + 320, py + 40)

        draw_text(self.screen, "YOU", F_TINY, NEON_CYAN, px + 80, py + 68)
        draw_text(self.screen, "AI", F_TINY, NEON_PINK, px + 320, py + 68)

        draw_progress_bar(self.screen, px + 20, py + 55, 140, 8, self.player_score, WIN_SCORE, NEON_CYAN)
        draw_progress_bar(self.screen, px + 240, py + 55, 140, 8, self.ai_score, WIN_SCORE, NEON_PINK)

        draw_text(self.screen, f"Round {self.round_num}", F_TINY, GREY_LIGHT, WIDTH // 2, py + 10)

    def draw_menu(self):
        self.menu_tick += 1
        t = self.menu_tick

        draw_grid(self.screen)

        for i, (rx, ry, col) in enumerate([
            (200, 200, NEON_CYAN),
            (900, 500, NEON_PINK),
            (640, 100, NEON_GREEN)
        ]):
            r = 60 + int(10 * np.sin(t * 0.03 + i))
            glow_circle(self.screen, col, (rx, ry), r)

        y0 = 220 + int(8 * np.sin(t * 0.04))

        draw_text(self.screen, "ROCK", F_HUGE, NEON_ORANGE, WIDTH // 2 - 240, y0)
        draw_text(self.screen, "PAPER", F_HUGE, NEON_CYAN, WIDTH // 2, y0)
        draw_text(self.screen, "SCISSORS", F_HUGE, NEON_GREEN, WIDTH // 2 + 260, y0)

        draw_text(self.screen, "A R T I F I C I A L   I N T E L L I G E N C E",
                  F_SMALL, NEON_PURPLE, WIDTH // 2, y0 + 75)

        draw_text(self.screen, f"First to {WIN_SCORE} wins the match",
                  F_MED, GOLD, WIDTH // 2, y0 + 130)

        for i, c in enumerate(CHOICES):
            xi = WIDTH // 2 - 280 + i * 280
            img = CHOICE_IMGS[c]
            r = img.get_rect(center=(xi, 490))
            self.screen.blit(img, r)
            glow_circle(self.screen, CHOICE_COLORS[c], (xi, 490), 118, width=3)
            draw_text(self.screen, c.upper(), F_SMALL, CHOICE_COLORS[c], xi, 600)

        bw, bh = 340, 64
        bx, by = WIDTH // 2 - bw // 2, 640
        draw_neon_panel(self.screen, (bx, by, bw, bh), NEON_GREEN, radius=32)
        draw_text(self.screen, "PRESS SPACE TO START", F_MED, NEON_GREEN, WIDTH // 2, by + 32)

    def draw_countdown(self, cam_surf, gesture, lm_list):
        self.draw_camera(340, 150, 600, 450, cam_surf, gesture, lm_list)

        elapsed = time.time() - self.cd_start
        remaining = self.countdown - int(elapsed)

        if remaining <= 0:
            self.state = STATE_DETECT
            self.detect_start = time.time()
            return

        f_dyn = font(170, bold=True)
        col = [NEON_GREEN, NEON_ORANGE, NEON_PINK][max(0, remaining - 1)]

        draw_text(self.screen, str(remaining), f_dyn, col, WIDTH // 2, 90)
        draw_text(self.screen, "GET READY!", F_MED, WHITE, WIDTH // 2, 620)

        self.draw_scoreboard()

    def draw_detect(self, cam_surf, gesture, lm_list):
        elapsed = time.time() - self.detect_start
        window = 1.8

        self.draw_camera(340, 150, 600, 450, cam_surf, gesture, lm_list)

        if gesture:
            self.detected_buf.append(gesture)

        prog = min(elapsed / window, 1.0)
        draw_progress_bar(self.screen, 440, 100, 400, 20, prog, 1, NEON_CYAN)

        draw_text(self.screen, "SHOW YOUR MOVE!", F_MED, WHITE, WIDTH // 2, 620)
        self.draw_scoreboard()

        if elapsed >= window:
            if self.detected_buf:
                freq = {c: self.detected_buf.count(c) for c in CHOICES}
                self.final_gesture = max(freq, key=freq.get)
            else:
                self.final_gesture = random.choice(CHOICES)

            self.player_choice = self.final_gesture
            self.ai_choice = ai_choose(self.player_history)
            self.player_history.append(self.player_choice)
            self.winner = determine_winner(self.player_choice, self.ai_choice)
            self.round_num += 1
            self.reveal_timer = 0
            self.state = STATE_REVEAL

    def draw_choice_card(self, x, y, choice, label, color, t):
        w, h = 240, 300
        draw_neon_panel(self.screen, (x, y, w, h), color, radius=18)

        img = CHOICE_IMGS[choice]
        ir = img.get_rect(center=(x + w // 2, y + h // 2 - 20))
        self.screen.blit(img, ir)

        draw_text(self.screen, choice.upper(), F_MED, color, x + w // 2, y + h - 30)
        draw_text(self.screen, label, F_TINY, WHITE, x + w // 2, y - 22)

    def draw_reveal(self, cam_surf, gesture, lm_list):
        self.reveal_timer += 1
        t = self.reveal_timer

        self.draw_choice_card(100, 180, self.player_choice, "YOU", NEON_CYAN, t)
        draw_text(self.screen, "VS", F_HUGE, WHITE, WIDTH // 2, HEIGHT // 2)

        if t > 20:
            self.draw_choice_card(WIDTH - 340, 180, self.ai_choice, "AI", NEON_PINK, t)
        else:
            fake = CHOICES[t % 3]
            self.draw_choice_card(WIDTH - 340, 180, fake, "AI", GREY_MID, t)

        if t > self.reveal_frames:
            if self.winner == "Player":
                self.player_score += 1
                play(SND_WIN)
                burst(300, 400, NEON_CYAN)
            elif self.winner == "AI":
                self.ai_score += 1
                play(SND_LOSE)
                burst(980, 400, NEON_PINK)
            else:
                play(SND_DRAW)
                burst(WIDTH // 2, 400, GOLD)

            if self.player_score >= WIN_SCORE or self.ai_score >= WIN_SCORE:
                self.state = STATE_GAMEOVER
            else:
                self.result_timer = time.time()
                self.state = STATE_RESULT

    def draw_result(self, cam_surf, gesture, lm_list):
        self.draw_choice_card(100, 180, self.player_choice, "YOU", NEON_CYAN, 99)
        self.draw_choice_card(WIDTH - 340, 180, self.ai_choice, "AI", NEON_PINK, 99)

        draw_text(self.screen, "VS", F_HUGE, WHITE, WIDTH // 2, HEIGHT // 2)

        if self.winner == "Player":
            msg, col = "YOU WIN!", NEON_GREEN
        elif self.winner == "AI":
            msg, col = "AI WINS!", NEON_PINK
        else:
            msg, col = "DRAW!", GOLD

        bw, bh = 480, 70
        bx = WIDTH // 2 - bw // 2
        by = HEIGHT - 110

        draw_neon_panel(self.screen, (bx, by, bw, bh), col, radius=22)
        draw_text(self.screen, msg, F_BIG, col, WIDTH // 2, by + 35)

        self.draw_scoreboard()
        update_particles(self.screen)

        if time.time() - self.result_timer > 2.5:
            self.detected_buf = []
            self.final_gesture = None
            self.state = STATE_COUNTDOWN
            self.cd_start = time.time()

    def draw_gameover(self):
        self.menu_tick += 1
        t = self.menu_tick

        draw_grid(self.screen)

        if self.player_score >= WIN_SCORE:
            title, col, sub = "VICTORY!", NEON_GREEN, "You outsmarted the AI!"
        else:
            title, col, sub = "DEFEATED!", NEON_PINK, "The AI learned from you..."

        y0 = 240 + int(6 * np.sin(t * 0.05))

        draw_text(self.screen, title, F_HUGE, col, WIDTH // 2, y0)
        draw_text(self.screen, sub, F_MED, WHITE, WIDTH // 2, y0 + 85)

        draw_text(self.screen, f"Final Score {self.player_score} - {self.ai_score}",
                  F_BIG, GOLD, WIDTH // 2, y0 + 170)

        draw_text(self.screen, f"{self.round_num} rounds played",
                  F_SMALL, GREY_LIGHT, WIDTH // 2, y0 + 235)

        play_rect = (WIDTH // 2 - 320, y0 + 300, 300, 58)
        quit_rect = (WIDTH // 2 + 40, y0 + 300, 200, 58)

        draw_neon_panel(self.screen, play_rect, NEON_GREEN, radius=28)
        draw_text(self.screen, "PLAY AGAIN", F_MED, NEON_GREEN,
                  play_rect[0] + 150, play_rect[1] + 29)

        draw_neon_panel(self.screen, quit_rect, RED_NEON, radius=28)
        draw_text(self.screen, "QUIT", F_MED, RED_NEON,
                  quit_rect[0] + 100, quit_rect[1] + 29)

        update_particles(self.screen)

        return play_rect, quit_rect

    def run(self):
        play_rect = quit_rect = None
        running = True

        while running:
            self.screen.fill(BG_DARK)

            cam_surf, gesture, lm_list = self.grab_frame()

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False

                if ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False

                    if ev.key == pygame.K_SPACE and self.state == STATE_MENU:
                        self.reset_game()
                        self.state = STATE_COUNTDOWN
                        self.cd_start = time.time()
                        play(SND_START)

                if ev.type == pygame.MOUSEBUTTONDOWN and self.state == STATE_GAMEOVER:
                    mx, my = ev.pos

                    if play_rect and pygame.Rect(play_rect).collidepoint(mx, my):
                        self.reset_game()
                        self.state = STATE_COUNTDOWN
                        self.cd_start = time.time()
                        play(SND_START)

                    if quit_rect and pygame.Rect(quit_rect).collidepoint(mx, my):
                        running = False

            if self.state == STATE_MENU:
                self.draw_menu()

            elif self.state == STATE_COUNTDOWN:
                draw_grid(self.screen)
                self.draw_countdown(cam_surf, gesture, lm_list)

            elif self.state == STATE_DETECT:
                draw_grid(self.screen)
                self.draw_detect(cam_surf, gesture, lm_list)

            elif self.state == STATE_REVEAL:
                draw_grid(self.screen)
                self.draw_scoreboard()
                self.draw_reveal(cam_surf, gesture, lm_list)
                update_particles(self.screen)

            elif self.state == STATE_RESULT:
                draw_grid(self.screen)
                self.draw_result(cam_surf, gesture, lm_list)

            elif self.state == STATE_GAMEOVER:
                play_rect, quit_rect = self.draw_gameover()

            scanlines(self.screen)
            pygame.display.flip()
            self.clock.tick(60)

        self.cap.release()
        pygame.quit()

# ─────────── Entry Point ───────────
if __name__ == "__main__":
    game = RockPaperScissorsAI()
    game.run()