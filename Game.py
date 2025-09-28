''''
Water-Wise Lawn — Pygame
------------------------------------------
Teach water conservation via lawn care choices.

UI REWORK:
- All player choices are arrow toggles:
    * Grass Type
    * Mowing Height
    * Mowing Frequency
    * Watering (None / Light / Deep)
- Only one button remains: ▶ Next Month
- Lawn sprite changes based on health (grass7.png .. grass1.png).
- If health <= 40, a 3s timer begins, then Game Over screen.
'''

import os
import sys
import random
import pygame
from dataclasses import dataclass, field
from typing import Callable, List, Tuple

# --------------------------- Window / Layout Constants ---------------------------

WIDTH, HEIGHT = 1100, 700
PANEL_W = 380
LAWN_W = WIDTH - PANEL_W
FPS = 60

# --------------------------- Colors ---------------------------------------------
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)

BG_TOP = (135, 206, 235)
BG_BOTTOM = (176, 224, 230)

BUTTON_BG = (170, 220, 170)
BUTTON_BORDER = (100, 160, 100)
PANEL_BG = (147, 196, 195)
PANEL_BORDER = (100, 140, 150)

AQUA = (91, 155, 213)
GOLD = (247, 208, 96)
GREEN = (40, 150, 90)
YELLOW = (243, 191, 63)
RED = (215, 83, 79)

# --------------------------- Data Models ----------------------------------------

@dataclass
class GrassType:
    name: str
    note: str

GRASS_TYPES = [
    GrassType("Cool-Season", "Prefers moderate temps; fair drought performance."),
    GrassType("Warm-Season", "Thrives in heat; tolerates stress."),
    GrassType("Native", "Low-input, drought-hardy; eco-friendly."),
]

MOW_HEIGHTS = ["High", "Medium", "Low"]
MOW_FREQS = ["Rare", "Normal", "Often"]
WATERING_OPTS = ["None", "Light", "Deep"]

@dataclass
class Lawn:
    health: float = 100.0
    moisture: float = 55.0
    grass: GrassType = field(default_factory=lambda: GRASS_TYPES[2])
    root_depth: float = 50.0
    mow_height_idx: int = 0
    mow_freq_idx: int = 1
    watering_idx: int = 0   # index into WATERING_OPTS
    last_watering: str = "None"

@dataclass
class Aquifer:
    level: float = 100.0

@dataclass
class GameState:
    month_count: int = 1
    lawn: Lawn = field(default_factory=Lawn)
    aquifer: Aquifer = field(default_factory=Aquifer)
    is_failing: bool = False
    fail_start_ms: int = 0
    in_game_over: bool = False

# --------------------------- Utility -------------------------------------------

def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def draw_gradient(surface: pygame.Surface, color_top: Tuple[int, int, int], color_bottom: Tuple[int, int, int]) -> None:
    for y in range(HEIGHT):
        t = y / (HEIGHT - 1)
        r = int(color_top[0] * (1 - t) + color_bottom[0] * t)
        g = int(color_top[1] * (1 - t) + color_bottom[1] * t)
        b = int(color_top[2] * (1 - t) + color_bottom[2] * t)
        pygame.draw.line(surface, (r, g, b), (0, y), (WIDTH, y))

# --------------------------- Images --------------------------------------------

def load_grass_images(target_size: Tuple[int, int]) -> dict:
    images = {}
    base_dir = os.path.dirname(__file__)
    fallback_colors = {
        7: (34, 139, 34),
        6: (52, 153, 56),
        5: (74, 160, 68),
        4: (124, 171, 81),
        3: (160, 160, 60),
        2: (172, 145, 64),
        1: (150, 120, 60),
    }
    for i in range(1, 8):
        filename = f"grass{i}.png"
        path = os.path.join(base_dir, filename)
        try:
            img = pygame.image.load(path).convert_alpha()
            # Nearest-neighbor keeps pixel art crisp
            img = pygame.transform.scale(img, target_size)
            images[i] = img
        except Exception:
            surf = pygame.Surface(target_size, pygame.SRCALPHA)
            surf.fill(fallback_colors[i])
            images[i] = surf
    return images

def health_to_grass_key(health: float) -> int:
    if health > 90: return 7
    elif health > 80: return 6
    elif health > 70: return 5
    elif health > 60: return 4
    elif health > 50: return 3
    elif health > 40: return 2
    else: return 1

# --------------------------- UI Elements ---------------------------------------

class Button:
    def __init__(self, rect: pygame.Rect, text: str, on_click: Callable[[], None]):
        self.rect = rect
        self.text = text
        self.on_click = on_click

    def draw(self, surf: pygame.Surface, font: pygame.font.Font):
        pygame.draw.rect(surf, BUTTON_BG, self.rect, border_radius=12)
        pygame.draw.rect(surf, BUTTON_BORDER, self.rect, width=2, border_radius=12)
        label = font.render(self.text, True, BLACK)
        surf.blit(label, label.get_rect(center=self.rect.center))

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.rect.collidepoint(ev.pos):
            self.on_click()

class ArrowToggle:
    def __init__(self, rect: pygame.Rect, label: str, options: List[str],
                 get_index: Callable[[], int], set_index: Callable[[int], None]):
        self.rect = rect
        self.label = label
        self.options = options
        self.get_index = get_index
        self.set_index = set_index
        self.left_rect = pygame.Rect(rect.x + 12, rect.y + rect.h // 2 - 15, 28, 28)
        self.right_rect = pygame.Rect(rect.right - 40, rect.y + rect.h // 2 - 15, 28, 28)

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font):
        pygame.draw.rect(surf, PANEL_BG, self.rect, border_radius=10)
        pygame.draw.rect(surf, PANEL_BORDER, self.rect, width=2, border_radius=10)
        label_surf = font.render(self.label, True, WHITE)
        surf.blit(label_surf, (self.rect.x + 12, self.rect.y + 6))
        idx = self.get_index()
        opt_surf = font.render(self.options[idx], True, WHITE)
        surf.blit(opt_surf, (self.rect.centerx - opt_surf.get_width() // 2, self.rect.centery - 8))
        pygame.draw.polygon(surf, WHITE, [
            (self.left_rect.right, self.left_rect.top),
            (self.left_rect.left, self.left_rect.centery),
            (self.left_rect.right, self.left_rect.bottom)
        ])
        pygame.draw.polygon(surf, WHITE, [
            (self.right_rect.left, self.right_rect.top),
            (self.right_rect.right, self.right_rect.centery),
            (self.right_rect.left, self.right_rect.bottom)
        ])

    def handle_event(self, ev: pygame.event.Event):
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.left_rect.collidepoint(ev.pos):
                self.set_index((self.get_index() - 1) % len(self.options))
            elif self.right_rect.collidepoint(ev.pos):
                self.set_index((self.get_index() + 1) % len(self.options))

class SliderBar:
    def __init__(self, rect: pygame.Rect, label: str, color: Tuple[int, int, int]):
        self.rect = rect
        self.label = label
        self.color = color
        self.value = 0.0

    def set_value(self, v: float):
        self.value = clamp(v, 0.0, 100.0)

    def draw(self, surf: pygame.Surface, font: pygame.font.Font, small: pygame.font.Font):
        label = font.render(self.label, True, WHITE)
        surf.blit(label, (self.rect.x, self.rect.y - 26))
        pygame.draw.rect(surf, (60, 60, 60), self.rect, border_radius=8)
        fill_w = int(self.rect.w * (self.value / 100.0))
        pygame.draw.rect(surf, self.color, (self.rect.x, self.rect.y, fill_w, self.rect.h), border_radius=8)
        pygame.draw.rect(surf, WHITE, self.rect, width=2, border_radius=8)
        val_txt = small.render(f"{int(self.value)}", True, WHITE)
        surf.blit(val_txt, (self.rect.right - 32, self.rect.y + 2))

# --------------------------- Game Logic ----------------------------------------

def calculate_multiplier(state: GameState) -> float:
    lawn = state.lawn
    total = 1.0
    if lawn.grass.name.startswith("Cool-Season"):
        total *= 0.97
    elif lawn.grass.name.startswith("Warm-Season"):
        total *= 1.00
    elif lawn.grass.name.startswith("Native"):
        total *= 1.05
    if lawn.mow_height_idx == 0:
        total *= 1.03
    elif lawn.mow_height_idx == 1:
        total *= 1.00
    else:
        total *= 0.95
    if lawn.mow_freq_idx == 1:
        total *= 1.02
    elif lawn.mow_freq_idx == 0:
        total *= 0.97
    else:
        total *= 0.94
    if lawn.last_watering == "Deep":
        total *= 1.04
    elif lawn.last_watering == "Light":
        total *= 0.98
    else:
        total *= 0.96
    return total

def monthly_moisture_update(state: GameState):
    base_et = 8.0
    height = MOW_HEIGHTS[state.lawn.mow_height_idx]
    if height == "High":
        et = base_et * 0.85
    elif height == "Medium":
        et = base_et * 1.00
    else:
        et = base_et * 1.15
    rain = 0.0
    if random.random() < 0.4:
        rain = random.uniform(4.0, 10.0)
    state.lawn.moisture = clamp(state.lawn.moisture + rain - et, 0, 100)
    if rain > 0:
        state.aquifer.level = clamp(state.aquifer.level + rain * 0.1, 0, 100)

def apply_next_month(state: GameState):
    # Read the watering choice selected in the toggle
    state.lawn.last_watering = WATERING_OPTS[state.lawn.watering_idx]
    # Apply choice multipliers
    mult = calculate_multiplier(state)
    state.lawn.health = clamp(state.lawn.health * mult, 0, 100)
    # Advance time & update dashboards
    state.month_count += 1
    monthly_moisture_update(state)
    # Start 3s fail timer if we entered the lowest band
    if not state.is_failing and state.lawn.health <= 40:
        state.is_failing = True
        state.fail_start_ms = pygame.time.get_ticks()

# --------------------------- Drawing -------------------------------------------

def draw_lawn(screen: pygame.Surface, lawn_rect: pygame.Rect, lawn_images: dict, health: float):
    key = health_to_grass_key(health)
    screen.blit(lawn_images[key], lawn_rect.topleft)

def draw_panel(screen: pygame.Surface, panel_rect: pygame.Rect, fonts, state: GameState,
               sliders, toggles, buttons):
    FONT, TITLE, SMALL = fonts
    pygame.draw.rect(screen, PANEL_BG, panel_rect)
    pygame.draw.rect(screen, PANEL_BORDER, panel_rect, width=2)
    title = TITLE.render("Water-Wise Lawn", True, WHITE)
    screen.blit(title, (panel_rect.x + 20, 16))
    sub = SMALL.render(f"Month #{state.month_count}   |   Grass: {state.lawn.grass.name}", True, WHITE)
    screen.blit(sub, (panel_rect.x + 20, 50))
    sliders["health"].set_value(state.lawn.health)
    sliders["moisture"].set_value(state.lawn.moisture)
    sliders["aquifer"].set_value(state.aquifer.level)
    for key in ("health", "moisture", "aquifer"):
        sliders[key].draw(screen, FONT, SMALL)
    for t in toggles:
        t.draw(screen, FONT, SMALL)
    for b in buttons:
        b.draw(screen, FONT)

# --------------------------- Game Over ------------------------------------------

def game_over_loop(screen: pygame.Surface, fonts, lawn_rect: pygame.Rect):
    FONT, TITLE, SMALL = fonts
    clock = pygame.time.Clock()
    while True:
        clock.tick(FPS)
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                return
        screen.fill(BLACK)
        overlay = pygame.Surface((lawn_rect.w, lawn_rect.h), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, lawn_rect.topleft)
        msg1 = TITLE.render("Game Over", True, RED)
        msg2 = FONT.render("Your lawn failed. Press R to restart.", True, WHITE)
        msg3 = SMALL.render("Tip: Taller mowing + deep watering helps!", True, WHITE)
        screen.blit(msg1, msg1.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 18)))
        screen.blit(msg2, msg2.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 18)))
        screen.blit(msg3, msg3.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 46)))
        pygame.display.flip()

# --------------------------- Main -----------------------------------------------

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Water-Wise Lawn")
    clock = pygame.time.Clock()

    # Fonts (pixel font if available, otherwise system fallback)
    font_path = os.path.join(os.path.dirname(__file__), "Minecraft.ttf")
    if os.path.exists(font_path):
        FONT = pygame.font.Font(font_path, 20)
        TITLE = pygame.font.Font(font_path, 28)
        SMALL = pygame.font.Font(font_path, 16)
    else:
        FONT = pygame.font.SysFont("verdana", 20)
        TITLE = pygame.font.SysFont("verdana", 28, bold=True)
        SMALL = pygame.font.SysFont("verdana", 16)

    panel_rect = pygame.Rect(LAWN_W, 0, PANEL_W, HEIGHT)
    lawn_rect = pygame.Rect(0, 0, LAWN_W, HEIGHT)
    lawn_images = load_grass_images((lawn_rect.w, lawn_rect.h))
    state = GameState()

    sliders = {
        "health":   SliderBar(pygame.Rect(panel_rect.x + 24,  90, panel_rect.w - 48, 22), "Lawn Health",  GREEN),
        "moisture": SliderBar(pygame.Rect(panel_rect.x + 24, 150, panel_rect.w - 48, 22), "Soil Moisture", AQUA),
        "aquifer":  SliderBar(pygame.Rect(panel_rect.x + 24, 210, panel_rect.w - 48, 22), "Aquifer Level", GOLD),
    }

    tog_grass = ArrowToggle(
        pygame.Rect(panel_rect.x + 20, 270, panel_rect.w - 40, 70),
        "Grass Type", [g.name for g in GRASS_TYPES],
        get_index=lambda: GRASS_TYPES.index(state.lawn.grass),
        set_index=lambda i: setattr(state.lawn, "grass", GRASS_TYPES[i])
    )
    tog_height = ArrowToggle(
        pygame.Rect(panel_rect.x + 20, 360, panel_rect.w - 40, 70),
        "Mowing Height", MOW_HEIGHTS,
        get_index=lambda: state.lawn.mow_height_idx,
        set_index=lambda i: setattr(state.lawn, "mow_height_idx", i)
    )
    tog_freq = ArrowToggle(
        pygame.Rect(panel_rect.x + 20, 450, panel_rect.w - 40, 70),
        "Mowing Frequency", MOW_FREQS,
        get_index=lambda: state.lawn.mow_freq_idx,
        set_index=lambda i: setattr(state.lawn, "mow_freq_idx", i)
    )
    tog_water = ArrowToggle(
        pygame.Rect(panel_rect.x + 20, 540, panel_rect.w - 40, 70),
        "Watering", WATERING_OPTS,
        get_index=lambda: state.lawn.watering_idx,
        set_index=lambda i: setattr(state.lawn, "watering_idx", i)
    )

    btn_next = Button(
        pygame.Rect(panel_rect.x + 20, panel_rect.bottom - 60, panel_rect.w - 40, 46),
        "▶ Next Month", lambda: apply_next_month(state)
    )

    toggles = [tog_grass, tog_height, tog_freq, tog_water]
    buttons = [btn_next]

    running = True
    while running:
        clock.tick(FPS)

        # -------- Events --------
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
            else:
                for b in buttons:
                    b.handle_event(ev)
                for t in toggles:
                    t.handle_event(ev)

        # -------- Updates --------
        if state.is_failing and not state.in_game_over:
            if pygame.time.get_ticks() - state.fail_start_ms >= 3000:
                state.in_game_over = True

        if state.in_game_over:
            game_over_loop(screen, (FONT, TITLE, SMALL), lawn_rect)
            # after returning, restart fresh state
            state = GameState()

        # -------- Draw --------
        draw_gradient(screen, BG_TOP, BG_BOTTOM)
        draw_lawn(screen, lawn_rect, lawn_images, state.lawn.health)
        draw_panel(screen, panel_rect, (FONT, TITLE, SMALL), state, sliders, toggles, buttons)
        pygame.display.flip()

    pygame.quit()
    sys.exit()

# Proper module guard OUTSIDE of main()
if __name__ == "__main__":
    main()