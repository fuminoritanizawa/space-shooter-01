import pygame
import random
import sys
import math

pygame.init()

WIDTH, HEIGHT = 800, 600
FPS = 60

BLACK        = (0,   0,   0)
WHITE        = (255, 255, 255)
CYAN         = (0,   255, 255)
DARK_CYAN    = (0,   120, 140)
RED          = (255, 50,  50)
ORANGE       = (255, 140, 0)
YELLOW       = (255, 255, 0)
GREEN        = (0,   230, 80)
GRAY         = (120, 120, 120)
DARK_GRAY    = (40,  40,  50)
PURPLE       = (180, 0,   255)
PINK         = (255, 100, 200)
BLUE         = (50,  100, 255)
SHIELD_COLOR = (0,   200, 255)
NEON_PINK    = (255, 20,  180)
ENEMY_BULLET_COLOR  = (255, 80, 0)    # bright orange — easy to see
ENEMY_BULLET_GLOW   = (255, 180, 60)  # inner glow

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Space Shooter")
clock    = pygame.time.Clock()
font     = pygame.font.SysFont("monospace", 22)
big_font = pygame.font.SysFont("monospace", 52)
med_font = pygame.font.SysFont("monospace", 32)

# Pre-bake a reusable glow surface factory
_glow_cache = {}
def glow_circle(radius, color, alpha=90):
    key = (radius, color, alpha)
    if key not in _glow_cache:
        s = pygame.Surface((radius*2, radius*2), pygame.SRCALPHA)
        for r in range(radius, 0, -1):
            a = int(alpha * (1 - r/radius))
            pygame.draw.circle(s, (*color, a), (radius, radius), r)
        _glow_cache[key] = s
    return _glow_cache[key]


# ---------------------------------------------------------------------------
# Background gradient
# ---------------------------------------------------------------------------

_bg_surf = None
def get_background():
    global _bg_surf
    if _bg_surf is None:
        _bg_surf = pygame.Surface((WIDTH, HEIGHT))
        for y in range(HEIGHT):
            t = y / HEIGHT
            r = int(0  + 5  * t)
            g = int(0  + 0  * t)
            b = int(15 + 25 * t)
            pygame.draw.line(_bg_surf, (r, g, b), (0, y), (WIDTH, y))
    return _bg_surf


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def draw_glow(surface, pos, radius, color, alpha=80):
    g = glow_circle(radius, color, alpha)
    surface.blit(g, (int(pos[0]) - radius, int(pos[1]) - radius),
                 special_flags=pygame.BLEND_ADD)


def draw_cannon(surface, x, y, shield_active=False, invincible=False):
    xi, yi = int(x), int(y)

    # Engine glow
    draw_glow(surface, (xi, yi + 18), 22, CYAN, 60)

    # Body
    body_color = (0, 210, 230) if not invincible else (200, 200, 255)
    pygame.draw.rect(surface, body_color, (xi - 26, yi + 8, 52, 22), border_radius=6)
    # Side fins
    pygame.draw.polygon(surface, DARK_CYAN, [(xi-26,yi+8),(xi-40,yi+28),(xi-26,yi+30)])
    pygame.draw.polygon(surface, DARK_CYAN, [(xi+26,yi+8),(xi+40,yi+28),(xi+26,yi+30)])
    # Barrel
    pygame.draw.rect(surface, body_color, (xi - 5, yi - 14, 10, 24), border_radius=4)
    # Barrel tip glow
    draw_glow(surface, (xi, yi - 14), 8, CYAN, 50)

    if shield_active:
        t = pygame.time.get_ticks()
        pulse = int(3 + 2 * math.sin(t / 200))
        pygame.draw.circle(surface, SHIELD_COLOR, (xi, yi), 42, pulse)
        draw_glow(surface, (xi, yi), 50, SHIELD_COLOR, 40)


def draw_enemy_basic(surface, x, y):
    # Body glow
    draw_glow(surface, (x, y), 28, RED, 50)
    pygame.draw.ellipse(surface, (200, 40, 40), (x - 20, y - 10, 40, 20))
    pygame.draw.ellipse(surface, (255, 80, 80), (x - 18, y - 8, 36, 16))   # highlight
    pygame.draw.ellipse(surface, YELLOW,        (x - 8,  y - 16, 16, 14))
    pygame.draw.polygon(surface, (180, 30, 30), [(x-20,y),(x-36,y+16),(x-10,y+8)])
    pygame.draw.polygon(surface, (180, 30, 30), [(x+20,y),(x+36,y+16),(x+10,y+8)])


def draw_enemy_fast(surface, x, y):
    draw_glow(surface, (x, y), 20, ORANGE, 55)
    pygame.draw.polygon(surface, (220, 110, 0), [(x,y-20),(x-15,y+13),(x+15,y+13)])
    pygame.draw.polygon(surface, (255, 180, 50),[(x,y-10),(x-7, y+8), (x+7, y+8)])
    pygame.draw.circle(surface, YELLOW, (x, y+2), 5)


def draw_enemy_tank(surface, x, y):
    draw_glow(surface, (x, y), 38, PURPLE, 50)
    pygame.draw.ellipse(surface, (140, 0, 200), (x-30, y-15, 60, 30))
    pygame.draw.ellipse(surface, (190, 60, 255),(x-26, y-11, 52, 22))  # highlight
    pygame.draw.ellipse(surface, PINK,          (x-12, y-22, 24, 18))
    pygame.draw.polygon(surface, (120, 0, 180), [(x-30,y),(x-50,y+22),(x-14,y+12)])
    pygame.draw.polygon(surface, (120, 0, 180), [(x+30,y),(x+50,y+22),(x+14,y+12)])


def draw_powerup(surface, x, y, kind, tick):
    colors  = {"rapid": YELLOW, "triple": CYAN, "shield": SHIELD_COLOR}
    labels  = {"rapid": "R",    "triple": "3",  "shield": "S"}
    c = colors.get(kind, WHITE)
    pulse = 14 + int(2 * math.sin(tick / 200))
    draw_glow(surface, (x, y), pulse + 8, c, 60)
    pygame.draw.circle(surface, c, (int(x), int(y)), pulse, 2)
    lbl = font.render(labels.get(kind, "?"), True, c)
    surface.blit(lbl, (int(x) - lbl.get_width()//2, int(y) - lbl.get_height()//2))


def draw_heart(surface, x, y, filled=True):
    color = (230, 50, 70) if filled else (60, 60, 70)
    if filled:
        draw_glow(surface, (x, y+4), 12, (230, 50, 70), 40)
    pygame.draw.circle(surface, color, (x - 5, y), 6)
    pygame.draw.circle(surface, color, (x + 5, y), 6)
    pygame.draw.polygon(surface, color, [(x - 10, y + 3), (x + 10, y + 3), (x, y + 16)])


# ---------------------------------------------------------------------------
# Classes
# ---------------------------------------------------------------------------

class Star:
    def __init__(self, x=None, y=None):
        self.x = x if x is not None else random.randint(0, WIDTH)
        self.y = y if y is not None else random.randint(0, HEIGHT)
        self.speed      = random.uniform(0.4, 2.8)
        self.size       = random.randint(1, 3)
        self.brightness = random.randint(80, 220)
        self.twinkle    = random.uniform(0, math.pi * 2)

    def update(self):
        self.y += self.speed
        self.twinkle += 0.05
        if self.y > HEIGHT:
            self.x     = random.randint(0, WIDTH)
            self.y     = 0
            self.speed = random.uniform(0.4, 2.8)

    def draw(self, surface):
        b = int(self.brightness * (0.7 + 0.3 * math.sin(self.twinkle)))
        pygame.draw.circle(surface, (b, b, b), (int(self.x), int(self.y)), self.size)


class Player:
    MAX_LIVES = 5

    def __init__(self):
        self.x = WIDTH // 2
        self.y = HEIGHT - 50
        self.speed = 6
        self.lives = 3
        self.invincible_timer = 0
        self.shield       = False
        self.shield_timer = 0
        self.rapid_timer  = 0
        self.triple_timer = 0

    def update(self, keys):
        if keys[pygame.K_LEFT]  and self.x > 30:         self.x -= self.speed
        if keys[pygame.K_RIGHT] and self.x < WIDTH - 30: self.x += self.speed
        if self.invincible_timer > 0: self.invincible_timer -= 1
        if self.shield_timer > 0:
            self.shield_timer -= 1
            self.shield = self.shield_timer > 0
        if self.rapid_timer  > 0: self.rapid_timer  -= 1
        if self.triple_timer > 0: self.triple_timer -= 1

    def draw(self, surface):
        if self.invincible_timer > 0 and self.invincible_timer % 6 < 3:
            return
        draw_cannon(surface, self.x, self.y, self.shield,
                    invincible=self.invincible_timer > 0)

    def shoot(self):
        if self.triple_timer > 0:
            return [
                PlayerBullet(self.x - 12, self.y - 10, angle=-15),
                PlayerBullet(self.x,      self.y - 10, angle=0),
                PlayerBullet(self.x + 12, self.y - 10, angle=15),
            ]
        return [PlayerBullet(self.x, self.y - 10)]

    def shoot_cooldown_frames(self):
        return 8 if self.rapid_timer > 0 else 18

    def take_hit(self):
        if self.shield:
            self.shield = False
            self.shield_timer = 0
            self.invincible_timer = 60
            return False
        if self.invincible_timer > 0:
            return False
        self.lives -= 1
        self.invincible_timer = 120
        return True

    def collect_powerup(self, kind):
        if   kind == "rapid":  self.rapid_timer  = 300
        elif kind == "triple": self.triple_timer = 300
        elif kind == "shield":
            self.shield = True
            self.shield_timer = 400


class PlayerBullet:
    SPEED = 16

    def __init__(self, x, y, angle=0):
        rad = math.radians(angle)
        self.x  = float(x)
        self.y  = float(y)
        self.vx = math.sin(rad) * self.SPEED
        self.vy = -math.cos(rad) * self.SPEED
        self.radius = 5
        self.trail  = []   # list of (x, y)

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 6:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy

    def draw(self, surface):
        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            alpha_r = max(2, int(4 * i / len(self.trail)))
            a = int(180 * i / len(self.trail))
            c = (min(255, 200 + a//4), min(255, 200 + a//4), 0)
            pygame.draw.circle(surface, c, (int(tx), int(ty)), alpha_r)
        # Glow + core
        draw_glow(surface, (self.x, self.y), 10, YELLOW, 70)
        pygame.draw.circle(surface, WHITE,  (int(self.x), int(self.y)), 3)
        pygame.draw.circle(surface, YELLOW, (int(self.x), int(self.y)), self.radius, 2)

    def off_screen(self):
        return self.y < 0 or self.x < 0 or self.x > WIDTH


class EnemyBullet:
    def __init__(self, x, y, target_x, target_y):
        self.x = float(x)
        self.y = float(y)
        speed  = 4
        dx = target_x - x
        dy = target_y - y
        dist = max((dx*dx + dy*dy)**0.5, 1)
        self.vx = dx / dist * speed
        self.vy = dy / dist * speed
        self.radius = 6
        self.trail  = []
        self.tick   = 0

    def update(self):
        self.trail.append((self.x, self.y))
        if len(self.trail) > 8:
            self.trail.pop(0)
        self.x += self.vx
        self.y += self.vy
        self.tick += 1

    def draw(self, surface):
        # Trail
        for i, (tx, ty) in enumerate(self.trail):
            r = max(1, int(4 * i / len(self.trail)))
            a = int(160 * i / len(self.trail))
            c = (255, max(0, 80 - (len(self.trail)-i)*10), 0)
            pygame.draw.circle(surface, c, (int(tx), int(ty)), r)
        # Outer glow — big and obvious
        draw_glow(surface, (self.x, self.y), 14, ENEMY_BULLET_COLOR, 90)
        # Mid ring
        pygame.draw.circle(surface, ENEMY_BULLET_COLOR,
                           (int(self.x), int(self.y)), self.radius, 2)
        # Bright inner core
        pygame.draw.circle(surface, ENEMY_BULLET_GLOW,
                           (int(self.x), int(self.y)), 3)

    def off_screen(self):
        return self.y > HEIGHT or self.x < 0 or self.x > WIDTH

    def hits_player(self, player):
        dx = self.x - player.x
        dy = self.y - player.y
        return (dx*dx + dy*dy)**0.5 < self.radius + 22


ENEMY_TYPES = {
    "basic": dict(hp=1, speed=(1.5, 3.0), radius=20, score=10,  shoot_chance=0.002, draw=draw_enemy_basic),
    "fast":  dict(hp=1, speed=(3.5, 5.5), radius=14, score=20,  shoot_chance=0.001, draw=draw_enemy_fast),
    "tank":  dict(hp=3, speed=(0.8, 1.8), radius=28, score=40,  shoot_chance=0.004, draw=draw_enemy_tank),
}


class Enemy:
    def __init__(self, kind="basic"):
        cfg = ENEMY_TYPES[kind]
        self.kind         = kind
        self.x            = float(random.randint(50, WIDTH - 50))
        self.y            = float(random.randint(-100, -20))
        self.speed        = random.uniform(*cfg["speed"])
        self.radius       = cfg["radius"]
        self.score        = cfg["score"]
        self.hp           = cfg["hp"]
        self.max_hp       = cfg["hp"]
        self.shoot_chance = cfg["shoot_chance"]
        self._draw        = cfg["draw"]

    def update(self):
        self.y += self.speed

    def draw(self, surface):
        self._draw(surface, int(self.x), int(self.y))
        if self.max_hp > 1:
            bw = self.radius * 2
            filled = int(bw * self.hp / self.max_hp)
            bar_y = int(self.y) + self.radius + 5
            pygame.draw.rect(surface, DARK_GRAY, (int(self.x) - self.radius, bar_y, bw, 5), border_radius=2)
            color = GREEN if self.hp == self.max_hp else ORANGE if self.hp > 1 else RED
            pygame.draw.rect(surface, color, (int(self.x) - self.radius, bar_y, filled, 5), border_radius=2)

    def try_shoot(self, player):
        if random.random() < self.shoot_chance:
            return EnemyBullet(self.x, self.y + self.radius, player.x, player.y)
        return None

    def off_screen(self):
        return self.y > HEIGHT + 40

    def hits(self, bullet):
        dx = self.x - bullet.x
        dy = self.y - bullet.y
        return (dx*dx + dy*dy)**0.5 < self.radius + bullet.radius


class PowerUp:
    KINDS = ["rapid", "triple", "shield"]

    def __init__(self, x, y):
        self.x      = float(x)
        self.y      = float(y)
        self.kind   = random.choice(self.KINDS)
        self.vy     = 1.5
        self.radius = 14

    def update(self):
        self.y += self.vy

    def draw(self, surface):
        draw_powerup(surface, self.x, self.y, self.kind, pygame.time.get_ticks())

    def off_screen(self):
        return self.y > HEIGHT + 20

    def hits_player(self, player):
        dx = self.x - player.x
        dy = self.y - player.y
        return (dx*dx + dy*dy)**0.5 < self.radius + 25


class Particle:
    def __init__(self, x, y, color=None):
        self.x     = float(x)
        self.y     = float(y)
        self.vx    = random.uniform(-5, 5)
        self.vy    = random.uniform(-6, 2)
        self.life  = random.randint(20, 50)
        self.color = color or random.choice([YELLOW, RED, WHITE, ORANGE, PINK])

    def update(self):
        self.x  += self.vx
        self.y  += self.vy
        self.vy += 0.12
        self.vx *= 0.97
        self.life -= 1

    def draw(self, surface):
        r = max(int(self.life / 7), 1)
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), r)

    def dead(self):
        return self.life <= 0


class FloatingText:
    def __init__(self, x, y, text, color=WHITE, big=False):
        self.x    = float(x)
        self.y    = float(y)
        self.text = text
        self.color = color
        self.life  = 60
        self.f     = med_font if big else font

    def update(self):
        self.y    -= 1.2
        self.life -= 1

    def draw(self, surface):
        alpha = max(int(255 * self.life / 60), 0)
        surf  = self.f.render(self.text, True, self.color)
        surf.set_alpha(alpha)
        surface.blit(surf, (int(self.x) - surf.get_width()//2, int(self.y)))

    def dead(self):
        return self.life <= 0


# ---------------------------------------------------------------------------
# Screen flash on hit
# ---------------------------------------------------------------------------

class ScreenFlash:
    def __init__(self):
        self.timer = 0
        self.color = RED

    def trigger(self, color=RED):
        self.timer = 12
        self.color = color

    def update(self):
        if self.timer > 0:
            self.timer -= 1

    def draw(self, surface):
        if self.timer > 0:
            alpha = int(120 * self.timer / 12)
            s = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            s.fill((*self.color, alpha))
            surface.blit(s, (0, 0))


# ---------------------------------------------------------------------------
# HUD
# ---------------------------------------------------------------------------

def draw_hud(surface, score, player, wave, streak, next_life_at):
    # Semi-transparent top bar
    bar = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
    bar.fill((0, 0, 0, 100))
    surface.blit(bar, (0, 0))

    surface.blit(font.render(f"Score: {score}", True, WHITE), (10, 10))

    wave_surf = font.render(f"Wave {wave}", True, CYAN)
    surface.blit(wave_surf, (WIDTH//2 - wave_surf.get_width()//2, 10))

    if streak >= 3:
        col = ORANGE if streak >= 5 else YELLOW
        s = font.render(f"x{streak} STREAK!", True, col)
        surface.blit(s, (WIDTH - s.get_width() - 10, 10))

    # Hearts
    for i in range(player.MAX_LIVES):
        draw_heart(surface, 20 + i * 30, 50, filled=(i < player.lives))

    # Next-life bar
    if player.lives < player.MAX_LIVES:
        prev     = next_life_at - 200
        progress = min(max((score - prev) / 200, 0.0), 1.0)
        bx, by, bw, bh = 10, 72, 120, 6
        pygame.draw.rect(surface, DARK_GRAY, (bx, by, bw, bh), border_radius=3)
        pygame.draw.rect(surface, GREEN,     (bx, by, int(bw * progress), bh), border_radius=3)
        lbl = font.render(f"+life@{next_life_at}", True, GREEN)
        surface.blit(lbl, (bx + bw + 6, by - 5))

    # Power-up pills
    px = WIDTH - 10
    for label, color, timer in [
        ("RAPID",  YELLOW,      player.rapid_timer),
        ("TRIPLE", CYAN,        player.triple_timer),
        ("SHIELD", SHIELD_COLOR, player.shield_timer),
    ]:
        if timer > 0:
            s = font.render(f"{label} {timer//60+1}s", True, color)
            px -= s.get_width() + 10
            surface.blit(s, (px, 40))


def draw_wave_banner(surface, wave, timer):
    if timer <= 0:
        return
    alpha = min(255, timer * 8)
    surf = med_font.render(f"-- WAVE  {wave} --", True, CYAN)
    surf.set_alpha(alpha)
    surface.blit(surf, (WIDTH//2 - surf.get_width()//2, HEIGHT//2 - 20))


# ---------------------------------------------------------------------------
# Wave config
# ---------------------------------------------------------------------------

def wave_config(wave):
    interval = max(25, 80 - wave * 4)
    if wave <= 2:
        weights = {"basic": 10, "fast": 0,  "tank": 0}
    elif wave <= 5:
        weights = {"basic": 7,  "fast": 3,  "tank": 0}
    else:
        weights = {"basic": 5,  "fast": 3,  "tank": 2}
    return interval, weights


def pick_enemy_kind(weights):
    kinds = [k for k, w in weights.items() for _ in range(w)]
    return random.choice(kinds)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_game():
    player        = Player()
    bullets       = []
    enemy_bullets = []
    enemies       = []
    particles     = []
    powerups      = []
    floats        = []
    stars         = [Star() for _ in range(120)]
    flash         = ScreenFlash()

    score          = 0
    next_life_at   = 200
    wave           = 1
    kills_in_wave  = 0
    kills_needed   = 10
    wave_banner    = 90
    spawn_timer    = 0
    spawn_interval, enemy_weights = wave_config(wave)
    shoot_cooldown = 0
    streak         = 0
    game_over      = False

    while True:
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                if game_over and event.key == pygame.K_r:
                    return

        if not game_over:
            keys = pygame.key.get_pressed()
            player.update(keys)

            if keys[pygame.K_SPACE] and shoot_cooldown <= 0:
                bullets.extend(player.shoot())
                shoot_cooldown = player.shoot_cooldown_frames()
            if shoot_cooldown > 0:
                shoot_cooldown -= 1

            spawn_timer += 1
            if spawn_timer >= spawn_interval:
                enemies.append(Enemy(pick_enemy_kind(enemy_weights)))
                spawn_timer = 0

            for s in stars:         s.update()
            for b in bullets:       b.update()
            for b in enemy_bullets: b.update()
            for e in enemies:
                e.update()
                shot = e.try_shoot(player)
                if shot: enemy_bullets.append(shot)
            for p in powerups: p.update()
            for p in particles: p.update()
            for f in floats:    f.update()
            flash.update()

            bullets       = [b for b in bullets       if not b.off_screen()]
            enemy_bullets = [b for b in enemy_bullets if not b.off_screen()]
            particles     = [p for p in particles     if not p.dead()]
            floats        = [f for f in floats        if not f.dead()]
            powerups      = [p for p in powerups      if not p.off_screen()]

            # Player bullets vs enemies
            surviving = []
            for e in enemies:
                hit_bullet = next((b for b in bullets if e.hits(b)), None)
                if hit_bullet:
                    bullets.remove(hit_bullet)
                    e.hp -= 1
                    if e.hp <= 0:
                        for _ in range(24): particles.append(Particle(e.x, e.y))
                        streak += 1
                        pts = e.score * (2 if streak >= 5 else 1)
                        score += pts
                        kills_in_wave += 1
                        floats.append(FloatingText(e.x, e.y - 20, f"+{pts}",
                                                   ORANGE if streak >= 5 else YELLOW))
                        if score >= next_life_at and player.lives < player.MAX_LIVES:
                            player.lives += 1
                            next_life_at += 200
                            floats.append(FloatingText(WIDTH//2, HEIGHT//2, "+1 LIFE!", GREEN, big=True))
                            flash.trigger(GREEN)
                        if random.random() < 0.18:
                            powerups.append(PowerUp(e.x, e.y))
                    else:
                        surviving.append(e)
                        for _ in range(6): particles.append(Particle(e.x, e.y, WHITE))
                else:
                    surviving.append(e)
            enemies = surviving

            # Enemies reach bottom
            next_enemies = []
            for e in enemies:
                if e.off_screen():
                    streak = 0
                    for _ in range(10): particles.append(Particle(e.x, HEIGHT - 10))
                    if player.take_hit():
                        floats.append(FloatingText(player.x, player.y - 30, "HIT!", RED))
                        flash.trigger(RED)
                else:
                    next_enemies.append(e)
            enemies = next_enemies

            # Enemy bullets hit player
            next_ebs = []
            for b in enemy_bullets:
                if b.hits_player(player):
                    streak = 0
                    if player.take_hit():
                        floats.append(FloatingText(player.x, player.y - 30, "HIT!", RED))
                        for _ in range(12): particles.append(Particle(player.x, player.y, RED))
                        flash.trigger(RED)
                else:
                    next_ebs.append(b)
            enemy_bullets = next_ebs

            # Power-up collection
            next_pu = []
            for pu in powerups:
                if pu.hits_player(player):
                    player.collect_powerup(pu.kind)
                    floats.append(FloatingText(player.x, player.y - 40, pu.kind.upper() + "!", GREEN))
                    flash.trigger((0, 180, 80))
                else:
                    next_pu.append(pu)
            powerups = next_pu

            # Wave progression
            if kills_in_wave >= kills_needed:
                wave          += 1
                kills_in_wave  = 0
                kills_needed   = 10 + wave * 2
                wave_banner    = 90
                spawn_interval, enemy_weights = wave_config(wave)
                enemies.clear()

            if wave_banner > 0:
                wave_banner -= 1

            if player.lives <= 0:
                game_over = True

        # ---- Draw ----
        screen.blit(get_background(), (0, 0))
        for s in stars:         s.draw(screen)
        for p in particles:     p.draw(screen)
        for pu in powerups:     pu.draw(screen)
        for b in enemy_bullets: b.draw(screen)
        for b in bullets:       b.draw(screen)
        for e in enemies:       e.draw(screen)
        if not game_over:
            player.draw(screen)
        for f in floats:        f.draw(screen)

        flash.draw(screen)
        draw_hud(screen, score, player, wave, streak, next_life_at)
        draw_wave_banner(screen, wave, wave_banner)

        if game_over:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            screen.blit(overlay, (0, 0))
            over  = big_font.render("GAME OVER", True, RED)
            final = font.render(f"Final Score: {score}   Wave: {wave}", True, WHITE)
            hint  = font.render("R = Restart     ESC = Quit", True, GRAY)
            screen.blit(over,  (WIDTH//2 - over.get_width()//2,  HEIGHT//2 - 70))
            screen.blit(final, (WIDTH//2 - final.get_width()//2, HEIGHT//2 + 10))
            screen.blit(hint,  (WIDTH//2 - hint.get_width()//2,  HEIGHT//2 + 54))

        pygame.display.flip()


def splash_screen():
    title_font   = pygame.font.SysFont("monospace", 64, bold=True)
    section_font = pygame.font.SysFont("monospace", 18, bold=True)
    body_font    = pygame.font.SysFont("monospace", 17)
    credit_font  = pygame.font.SysFont("monospace", 19)
    start_font   = pygame.font.SysFont("monospace", 24)
    stars = [Star() for _ in range(120)]

    # How-to-play table: (key label, description, color)
    HOW_TO = [
        ("← →",     "move cannon",                    CYAN),
        ("SPACE",    "shoot",                          CYAN),
        ("",         "",                               None),           # spacer
        ("YELLOW",   "rapid-fire power-up",            YELLOW),
        ("CYAN",     "triple-shot power-up",           (0, 220, 255)),
        ("PURPLE",   "shield power-up",                (180, 80, 255)),
        ("",         "",                               None),           # spacer
        ("+1 LIFE",  "earn a life every 200 pts",      GREEN),
        ("STREAK",   "chain kills for bonus score",    (255, 160, 40)),
    ]

    PANEL_W, PANEL_H = 460, 310
    panel_x = WIDTH  // 2 - PANEL_W // 2
    panel_y = HEIGHT // 2 - 60

    while True:
        clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit(); sys.exit()
                return

        t = pygame.time.get_ticks()
        for s in stars: s.update()

        screen.blit(get_background(), (0, 0))
        for s in stars: s.draw(screen)

        # ── Title ──────────────────────────────────────────────────────────
        title_surf = title_font.render("SPACE SHOOTER", True, CYAN)
        glow_surf  = title_font.render("SPACE SHOOTER", True, (0, 70, 110))
        tx = WIDTH // 2 - title_surf.get_width() // 2
        for dx, dy in [(-3,0),(3,0),(0,-3),(0,3)]:
            screen.blit(glow_surf, (tx + dx, 52 + dy))
        screen.blit(title_surf, (tx, 52))

        # pulsing "built by fumi"
        pulse = 0.55 + 0.45 * math.sin(t / 420)
        r = int(120 + 135 * pulse); g = int(200 + 55 * pulse); b = 255
        credit_surf = credit_font.render("built by  fumi", True, (r, g, b))
        screen.blit(credit_surf, (WIDTH // 2 - credit_surf.get_width() // 2, 126))

        # ── HOW TO PLAY panel ──────────────────────────────────────────────
        # semi-transparent background
        panel = pygame.Surface((PANEL_W, PANEL_H), pygame.SRCALPHA)
        panel.fill((0, 10, 30, 175))
        screen.blit(panel, (panel_x, panel_y))

        # panel border
        pygame.draw.rect(screen, DARK_CYAN, (panel_x, panel_y, PANEL_W, PANEL_H), 1)
        pygame.draw.rect(screen, (0, 60, 90), (panel_x+1, panel_y+1, PANEL_W-2, PANEL_H-2), 1)

        # section header
        header = section_font.render("HOW  TO  PLAY", True, CYAN)
        hx = panel_x + PANEL_W // 2 - header.get_width() // 2
        screen.blit(header, (hx, panel_y + 12))
        pygame.draw.line(screen, DARK_CYAN,
                         (panel_x + 20, panel_y + 34),
                         (panel_x + PANEL_W - 20, panel_y + 34), 1)

        # rows
        row_y = panel_y + 44
        key_x   = panel_x + 20
        desc_x  = panel_x + 130
        for key, desc, color in HOW_TO:
            if key == "":          # spacer
                row_y += 8
                continue
            key_surf  = body_font.render(key,  True, color)
            desc_surf = body_font.render(desc, True, (200, 210, 220))
            screen.blit(key_surf,  (key_x,  row_y))
            screen.blit(desc_surf, (desc_x, row_y))
            # subtle dot separator
            pygame.draw.circle(screen, DARK_CYAN, (desc_x - 12, row_y + 9), 2)
            row_y += 26

        # ── Blinking prompt ────────────────────────────────────────────────
        if (t // 550) % 2 == 0:
            prompt = start_font.render("— press any key to start —", True, WHITE)
            screen.blit(prompt, (WIDTH // 2 - prompt.get_width() // 2,
                                 panel_y + PANEL_H + 18))

        pygame.display.flip()


splash_screen()
while True:
    run_game()
