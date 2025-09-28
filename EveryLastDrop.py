import os
import sys
import random
import pygame
from dataclasses import dataclass, field
from typing import Callable, List, Tuple
from enum import Enum


# --------------------------- Optional SLM import ---------------------------
try:
    from ChatWithSLMNew import chat_with_slm
except Exception as e:
    print("Error importing ChatWithSLMNew:", e)
    raise   # show the real traceback instead of masking it

# --------------------------- Window Layout --------------------------------
pygame.init()
pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)

# --------------------------- Background Music ---------------------------
try:
    bg_music_path = os.path.join(os.path.dirname(__file__), "bg_loop.wav")
    BG_LOOP = pygame.mixer.Sound(bg_music_path)
except Exception:
    BG_LOOP = None

TOTAL_W, TOTAL_H = 1300, 700
FPS = 60

# Left: Game (2/3), Right: Chat (1/3)
GAME_W = TOTAL_W * 2 // 3
CHAT_W = TOTAL_W - GAME_W

GAME_RECT = pygame.Rect(0, 0, GAME_W, TOTAL_H)
CHAT_RECT = pygame.Rect(GAME_W, 0, CHAT_W, TOTAL_H)

screen = pygame.display.set_mode((TOTAL_W, TOTAL_H))
pygame.display.set_caption("Every Last Drop")

# --------------------------- Fonts ----------------------------------------
def load_fonts():
    # Try user's absolute path first, then local, then fallback
    candidates = [
        "Minecraft.ttf",
        os.path.join(os.path.dirname(__file__), "Minecraft.ttf"),
    ]
    font_path = None
    for p in candidates:
        if os.path.exists(p):
            font_path = p
            break

    if font_path:
        FONT = pygame.font.Font(font_path, 20)
        TITLE = pygame.font.Font(font_path, 38)
        BUTTON = pygame.font.Font(font_path, 18)
        TITLE_SMALL = pygame.font.Font(font_path, 28)
        SMALL = pygame.font.Font(font_path, 16)
    else:
        # Fallbacks
        FONT = pygame.font.SysFont("georgia", 20)
        TITLE = pygame.font.SysFont("georgia", 38, bold=True)
        BUTTON = pygame.font.SysFont("georgia", 18, bold=True)
        TITLE_SMALL = pygame.font.SysFont("verdana", 28, bold=True)
        SMALL = pygame.font.SysFont("verdana", 16)
    return FONT, TITLE, BUTTON, TITLE_SMALL, SMALL

FONT, TITLE_FONT, BUTTON_FONT, GAME_TITLE_FONT, SMALL_FONT = load_fonts()

# --------------------------- Shared Utility --------------------------------
def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))

def draw_vertical_gradient(surface: pygame.Surface, rect: pygame.Rect, color_top, color_bottom):
    # Draw inside rect only
    for dy in range(rect.h):
        t = dy / max(1, rect.h - 1)
        r = int(color_top[0] * (1 - t) + color_bottom[0] * t)
        g = int(color_top[1] * (1 - t) + color_bottom[1] * t)
        b = int(color_top[2] * (1 - t) + color_bottom[2] * t)
        pygame.draw.line(surface, (r, g, b), (rect.x, rect.y + dy), (rect.right - 1, rect.y + dy))

def draw_shadow_rect(surface, rect, color, radius=0, shadow_offset=(4, 4), shadow_alpha=80):
    shadow_rect = rect.move(*shadow_offset)
    shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect(), border_radius=radius)
    surface.blit(shadow_surface, shadow_rect.topleft)
    pygame.draw.rect(surface, color, rect, border_radius=radius)

def quiz_popup(level: int, screen, FONT, BUTTON_FONT):
    question = next(q for q in QUESTIONS_BY_MONTH if q["month"] == level)
    answered = False
    explanation_shown = False
    running = True
    result = None

    WIDTH, HEIGHT = screen.get_size()
    popup_w, popup_h = WIDTH // 2, HEIGHT // 2  # half screen width & height
    popup_x = (WIDTH - popup_w) // 2
    popup_y = (HEIGHT - popup_h) // 2
    popup_rect = pygame.Rect(popup_x, popup_y, popup_w, popup_h)

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if not answered:
                    if true_btn.collidepoint(event.pos):
                        answered, result = True, True
                    elif false_btn.collidepoint(event.pos):
                        answered, result = True, False
                elif explanation_shown and exit_btn.collidepoint(event.pos):
                    running = False

        # --- Dim background ---
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        screen.blit(overlay, (0, 0))

        # --- Popup background ---
        pygame.draw.rect(screen, (240, 250, 255), popup_rect, border_radius=16)
        pygame.draw.rect(screen, (60, 60, 60), popup_rect, 3, border_radius=16)

        if not answered:
            # --- Question text ---
            wrapped = []
            words = question["prompt"].split()
            line = ""
            for w in words:
                if FONT.size(line+w)[0] < popup_rect.w-40:
                    line += w+" "
                else:
                    wrapped.append(line); line = w+" "
            wrapped.append(line)
            for i, ln in enumerate(wrapped):
                text = FONT.render(ln.strip(), True, (30,30,30))
                text = FONT.render(ln.strip(), True, (30, 30, 30))
                text_rect = text.get_rect(center=(popup_rect.centerx, popup_rect.y + 60 + i * 28))
                screen.blit(text, text_rect)

            # --- True / False buttons ---
            btn_w, btn_h, spacing = 140, 50, 40
            total_w = btn_w * 2 + spacing

            start_x = popup_rect.centerx - total_w // 2
            y = popup_rect.bottom - 100

            true_btn = pygame.Rect(start_x, y, btn_w, btn_h)
            false_btn = pygame.Rect(start_x + btn_w + spacing, y, btn_w, btn_h)

            pygame.draw.rect(screen, (136,199,219), true_btn, border_radius=12)   # Aqua
            pygame.draw.rect(screen, (93,151,209), true_btn, 3, border_radius=12) # Outline
            ttxt = BUTTON_FONT.render("TRUE", True, (0,0,0))
            screen.blit(ttxt, ttxt.get_rect(center=true_btn.center))

            pygame.draw.rect(screen, (197,236,172), false_btn, border_radius=12)   # Green
            pygame.draw.rect(screen, (93,151,209), false_btn, 3, border_radius=12) # Outline
            ftxt = BUTTON_FONT.render("FALSE", True, (0,0,0))
            screen.blit(ftxt, ftxt.get_rect(center=false_btn.center))

        else:
            # --- Feedback ---
            correct = question["is_true"] == result
            status = "Correct!" if correct else "Incorrect!"
            color = (40,150,90) if correct else (215,83,79)
            status_text = FONT.render(status, True, color)
            status_rect = status_text.get_rect(center=(popup_rect.centerx, popup_rect.y + 40))
            screen.blit(status_text, status_rect)

            # --- Explanation ---
            wrapped = []
            words = question["explanation"].split()
            line = ""
            for w in words:
                if FONT.size(line+w)[0] < popup_rect.w-40:
                    line += w+" "
                else:
                    wrapped.append(line); line = w+" "
            wrapped.append(line)
            for i, ln in enumerate(wrapped):
                text = FONT.render(ln.strip(), True, (30, 30, 30))
                text_rect = text.get_rect(center=(popup_rect.centerx, popup_rect.y + 80 + i * 28))
                screen.blit(text, text_rect)

            # --- Exit button ---
            exit_btn = pygame.Rect(popup_rect.centerx-70, popup_rect.bottom-80, 140, 50)
            pygame.draw.rect(screen, (221,223,128), exit_btn, border_radius=12)   # Yellow
            pygame.draw.rect(screen, (93,151,209), exit_btn, 3, border_radius=12) # Outline
            etxt = BUTTON_FONT.render("CONTINUE", True, (0,0,0))
            screen.blit(etxt, etxt.get_rect(center=exit_btn.center))
            explanation_shown = True

        pygame.display.flip()
    return True


# ======================================================================
#                               CHAT UI
# ======================================================================
class ChatUI:
    # Color scheme (cute palette)
    COLOR_AQUA   = (136, 199, 219)   # #88c7db
    COLOR_BLUE   = (93, 151, 209)    # #5d97d1
    COLOR_GREEN  = (197, 236, 172)   # #c5ecac
    COLOR_YELLOW = (221, 223, 128)   # #dddf80

    BG_TOP = COLOR_AQUA
    BG_BOTTOM = COLOR_BLUE
    TITLE_BAR = COLOR_BLUE
    BOTTOM_BAR = COLOR_AQUA

    YOU_BUBBLE = COLOR_GREEN
    AQUA_BUBBLE = COLOR_YELLOW
    TEXT_COLOR = (30, 30, 30)
    AQUA_TEXT = (30, 30, 30)

    INPUT_BG = (255, 255, 255)
    CURSOR_COLOR = (40, 40, 40)

    BUTTON_COLOR = COLOR_GREEN
    BUTTON_HOVER = COLOR_YELLOW

    SCROLLBAR_COLOR = (255, 255, 255, 190)  # white again (more visible)
    ARROW_BG = COLOR_BLUE
    ARROW_HOVER = (60, 110, 180)

    def __init__(self, rect: pygame.Rect, fonts: Tuple[pygame.font.Font, pygame.font.Font, pygame.font.Font]):
        self.rect = rect.copy()
        self.W, self.H = rect.w, rect.h

        self.FONT, self.TITLE_FONT, self.BUTTON_FONT = fonts
        self.disabled = False

        # Layout
        self.CHAT_AREA_TOP = 80
        self.CHAT_AREA_BOTTOM = self.H - 140
        self.CHAT_AREA_HEIGHT = self.CHAT_AREA_BOTTOM - self.CHAT_AREA_TOP
        self.bubble_max_w = min(440, self.W - 60)  # leave margins

        # State
        self.input_text = ""
        self.chat_history: List[Tuple[str, str]] = []
        self.max_history = 100

        self.cursor_visible = True
        self.cursor_timer = 0
        self.cursor_interval = 500

        self.scroll_offset = 0.0
        self.scroll_velocity = 0.0
        self.scroll_damping = 0.85
        self.scroll_step = 10

        self.dragging_scrollbar = False
        self.drag_start_y = 0
        self.scroll_start_offset = 0

        self.predefined_buttons = [
            ("Watering Habits",
             "Please tell me about some eco-friendly watering habits for my lawn"),

            ("Mowing Habits",
             "Please tell me about the best mowing habits for my lawn to conserve water"),

            ("Soil Management",
             "Tell me about the best soil management techniques for my lawn"),

            ("Fertilization & Care",
             "Please tell me about the best fertilizer options for my lawn, to make my lawn healthy and conserve water"),

            ("Stress Conditioning",
             "Tell me about stress conditioning for my lawn"),

            ("Grass Species",
             "Tell me about the best grass species to build a healthy, ecofriendly, drought-tolerant lawn"),

            ("Native Landscaping",
             "Tell me about alternatives to grass -- what else can I do with my lawn, such as native plants?"),
        ]

        self.button_height = 36
        self.button_spacing = 10
        self.button_scroll_offset = 0

        self.left_arrow_rect = None
        self.right_arrow_rect = None
        self.ask_button_rect = None
        self.scrollbar_rect = None
        self.predefined_button_rects: List[pygame.Rect] = []

        # Sounds
        self.pop_sound = None
        try:
            sound_path = os.path.join(os.path.dirname(__file__), "pop.wav")
            self.pop_sound = pygame.mixer.Sound(sound_path)
        except Exception:
            self.pop_sound = None

        # Greeting
        self.chat_history.append(("AquaGuide",
            "Hi! I'm AquaGuide, your personal AI Assistant to answer all your questions about "
            "sustainable lawn care and guide you through your water conservation journey. "
            "If you have any questions or want advice, just ask!"))

    # ---------- Helpers ----------
    def wrap_text(self, text: str, font: pygame.font.Font, max_width: int) -> List[str]:
        """Wrap text into lines that fit max_width. Preserves paragraph gaps."""
        lines = []
        paragraphs = text.split("\n")
        for idx, para in enumerate(paragraphs):
            words = para.split(" ")
            current = ""
            for w in words:
                test = current + w + " "
                if font.size(test)[0] <= max_width:
                    current = test
                else:
                    if current:
                        lines.append(current.strip())
                    current = w + " "
            if current:
                lines.append(current.strip())
            if idx < len(paragraphs) - 1:
                lines.append("<PARA_BREAK>")
        return lines

    def calc_total_height(self) -> int:
        y = 0
        for speaker, msg in self.chat_history[-self.max_history:]:
            lines = self.wrap_text(msg, self.FONT, self.bubble_max_w)
            bubble_h = 0
            for ln in lines:
                if ln == "<PARA_BREAK>":
                    bubble_h += 10
                else:
                    bubble_h += 28
            bubble_h += 24
            y += bubble_h + 20
        return y

    # ---------- Drawing ----------
    def draw_predefined_buttons(self, surf: pygame.Surface):
        self.predefined_button_rects = []

        button_y = self.H - 100
        arrow_w = 30
        margin = 10

        left_arrow = pygame.Rect(self.rect.x + margin, self.rect.y + button_y,
                                 arrow_w, self.button_height)
        right_arrow = pygame.Rect(self.rect.x + self.W - margin - arrow_w,
                                  self.rect.y + button_y,
                                  arrow_w, self.button_height)
        self.left_arrow_rect = left_arrow
        self.right_arrow_rect = right_arrow

        scroll_area_x = left_arrow.right + margin
        scroll_area_w = max(0, right_arrow.left - margin - scroll_area_x)
        scroll_area = pygame.Rect(scroll_area_x, self.rect.y + button_y,
                                  scroll_area_w, self.button_height)

        # Measure all buttons
        metrics = []
        total_w = 0
        for label, prompt in self.predefined_buttons:
            text_surface = self.BUTTON_FONT.render(label, True, (30, 30, 30))
            w = text_surface.get_width() + 30
            metrics.append((label, w, text_surface))
            total_w += w + self.button_spacing
        if total_w > 0:
            total_w -= self.button_spacing

        max_offset = max(0, total_w - scroll_area_w)
        self.button_scroll_offset = clamp(self.button_scroll_offset, 0, max_offset)

        row_surface = pygame.Surface((max(total_w, 1), self.button_height), pygame.SRCALPHA)
        xoff = 0
        mouse = pygame.mouse.get_pos()
        over_arrows = (left_arrow.collidepoint(mouse) or right_arrow.collidepoint(mouse))

        # Draw each button
        for (label, w, text_surface), (btn_label, prompt) in zip(metrics, self.predefined_buttons):
            rect_on_row = pygame.Rect(xoff, 0, w, self.button_height)
            btn_rect_screen = pygame.Rect(
                scroll_area_x + rect_on_row.x - self.button_scroll_offset,
                self.rect.y + button_y,
                rect_on_row.width, rect_on_row.height
            )
            visible = btn_rect_screen.colliderect(scroll_area)
            self.predefined_button_rects.append(btn_rect_screen if visible else pygame.Rect(0, 0, 0, 0))

            hovered = (visible and not over_arrows and btn_rect_screen.collidepoint(mouse))
            color = self.BUTTON_HOVER if hovered else self.BUTTON_COLOR

            draw_shadow_rect(row_surface, rect_on_row, color, radius=8, shadow_offset=(2, 2), shadow_alpha=80)
            row_surface.blit(
                text_surface,
                (rect_on_row.centerx - text_surface.get_width() // 2,
                 rect_on_row.centery - text_surface.get_height() // 2)
            )
            xoff += w + self.button_spacing

        # Clip and blit row
        prev_clip = screen.get_clip()
        screen.set_clip(scroll_area)
        screen.blit(row_surface, (scroll_area_x - self.button_scroll_offset, self.rect.y + button_y))
        screen.set_clip(prev_clip)

        # Arrows
        la_color = self.ARROW_HOVER if left_arrow.collidepoint(mouse) else self.ARROW_BG
        ra_color = self.ARROW_HOVER if right_arrow.collidepoint(mouse) else self.ARROW_BG
        draw_shadow_rect(screen, left_arrow, la_color, radius=6, shadow_offset=(2, 2), shadow_alpha=80)
        draw_shadow_rect(screen, right_arrow, ra_color, radius=6, shadow_offset=(2, 2), shadow_alpha=80)

        pygame.draw.polygon(
            screen, (255, 255, 255),
            [(left_arrow.centerx + 6, left_arrow.centery - 8),
             (left_arrow.centerx - 6, left_arrow.centery),
             (left_arrow.centerx + 6, left_arrow.centery + 8)]
        )
        pygame.draw.polygon(
            screen, (255, 255, 255),
            [(right_arrow.centerx - 6, right_arrow.centery - 8),
             (right_arrow.centerx + 6, right_arrow.centery),
             (right_arrow.centerx - 6, right_arrow.centery + 8)]
        )

    def draw_scrollbar(self, total_h: int):
        if total_h <= self.CHAT_AREA_HEIGHT:
            self.scrollbar_rect = None
            return
        max_scroll = max(0, total_h - self.CHAT_AREA_HEIGHT)
        bar_h = max(40, int(self.CHAT_AREA_HEIGHT * (self.CHAT_AREA_HEIGHT / total_h)))
        scroll_ratio = self.scroll_offset / max_scroll if max_scroll > 0 else 0
        bar_y = self.rect.y + self.CHAT_AREA_TOP + int((self.CHAT_AREA_HEIGHT - bar_h) * scroll_ratio)
        r = pygame.Rect(self.rect.x + self.W - 12, bar_y, 8, bar_h)

        # Draw with alpha
        s = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
        s.fill(self.SCROLLBAR_COLOR)
        screen.blit(s, r.topleft)
        self.scrollbar_rect = r

    def draw(self, surface: pygame.Surface):
        # Background gradient in chat area
        draw_vertical_gradient(surface, self.rect, self.BG_TOP, self.BG_BOTTOM)

        # Title bar
        title_rect = pygame.Rect(self.rect.x, self.rect.y, self.W, 70)
        draw_shadow_rect(surface, title_rect, self.TITLE_BAR, radius=0, shadow_offset=(0, 3), shadow_alpha=100)
        title_surface = self.TITLE_FONT.render("AquaGuide", True, (255, 255, 255))
        surface.blit(title_surface, (self.rect.x + self.W // 2 - title_surface.get_width() // 2, self.rect.y + 18))

        # Chat scrollable area
        chat_area_surface = pygame.Surface((self.W, self.CHAT_AREA_HEIGHT), pygame.SRCALPHA)
        yoff = -self.scroll_offset
        for speaker, msg in self.chat_history[-self.max_history:]:
            lines = self.wrap_text(msg, self.FONT, self.bubble_max_w)
            bubble_h = 0
            for ln in lines:
                bubble_h += 10 if ln == "<PARA_BREAK>" else 28
            bubble_h += 24

            if speaker == "You":
                bubble_rect = pygame.Rect(self.W - (self.bubble_max_w + 40), yoff, self.bubble_max_w + 20, bubble_h)
                color = self.YOU_BUBBLE
                text_color = self.TEXT_COLOR
                align_left = False
            else:
                bubble_rect = pygame.Rect(20, yoff, self.bubble_max_w + 20, bubble_h)
                color = self.AQUA_BUBBLE
                text_color = self.AQUA_TEXT
                align_left = True

            draw_shadow_rect(chat_area_surface, bubble_rect, color, radius=16, shadow_offset=(3, 3), shadow_alpha=70)
            line_y = yoff + 14
            for ln in lines:
                if ln == "<PARA_BREAK>":
                    line_y += 10
                    continue
                ts = self.FONT.render(ln, True, text_color)
                if align_left:
                    chat_area_surface.blit(ts, (bubble_rect.x + 18, line_y))
                else:
                    chat_area_surface.blit(ts, (bubble_rect.right - ts.get_width() - 18, line_y))
                line_y += 28
            yoff += bubble_h + 20

        surface.blit(chat_area_surface, (self.rect.x, self.rect.y + self.CHAT_AREA_TOP))

        # Scrollbar
        total_h = self.calc_total_height()
        self.draw_scrollbar(total_h)

        # Bottom bar
        bottom_bar_rect = pygame.Rect(self.rect.x, self.rect.y + self.H - 120, self.W, 120)
        draw_shadow_rect(surface, bottom_bar_rect, self.BOTTOM_BAR, radius=0, shadow_offset=(0, -2), shadow_alpha=100)

        # Predefined buttons
        self.draw_predefined_buttons(surface)

        # Input
        input_rect = pygame.Rect(self.rect.x + 20, self.rect.y + self.H - 50, self.W - 150, 42)
        draw_shadow_rect(surface, input_rect, self.INPUT_BG, radius=12, shadow_offset=(2, 2), shadow_alpha=90)

        # Render full text
        ts_full = self.FONT.render(self.input_text, True, self.CURSOR_COLOR)

        # Clip if too wide for the box
        max_width = input_rect.w - 20
        if ts_full.get_width() > max_width:
            text_surface = ts_full.subsurface(
                (ts_full.get_width() - max_width, 0, max_width, ts_full.get_height())
            )
        else:
            text_surface = ts_full

        # Blit clipped or full text
        surface.blit(text_surface, (input_rect.x + 14, input_rect.y + 12))

        # Cursor (always at end of visible text)
        if self.cursor_visible:
            cx = input_rect.x + 14 + text_surface.get_width() + 2
            cy = input_rect.y + 12
            ch = text_surface.get_height()
            pygame.draw.line(surface, self.CURSOR_COLOR, (cx, cy), (cx, cy + ch), 2)

        # Ask button
        self.ask_button_rect = pygame.Rect(self.rect.x + self.W - 120, self.rect.y + self.H - 50, 100, 42)
        mouse = pygame.mouse.get_pos()
        bcolor = self.BUTTON_HOVER if self.ask_button_rect.collidepoint(mouse) else self.BUTTON_COLOR
        draw_shadow_rect(surface, self.ask_button_rect, bcolor, radius=8, shadow_offset=(2, 2), shadow_alpha=80)
        btxt = self.BUTTON_FONT.render("Ask", True, (0, 0, 0))
        surface.blit(btxt, (self.ask_button_rect.centerx - btxt.get_width() // 2,
                            self.ask_button_rect.centery - btxt.get_height() // 2))

    # ---------- Events / Update ----------
    def update(self, dt_ms: int):
        self.cursor_timer += dt_ms
        if self.cursor_timer >= self.cursor_interval:
            self.cursor_visible = not self.cursor_visible
            self.cursor_timer = 0

        # Inertia
        self.scroll_offset += self.scroll_velocity * dt_ms / 16.0
        self.scroll_velocity *= self.scroll_damping
        total_h = self.calc_total_height()
        max_scroll = max(0, total_h - self.CHAT_AREA_HEIGHT)
        if self.scroll_offset < 0:
            self.scroll_offset = 0
            self.scroll_velocity = 0
        elif self.scroll_offset > max_scroll:
            self.scroll_offset = max_scroll
            self.scroll_velocity = 0

    def handle_event(self, ev: pygame.event.Event):
        if self.disabled:
            return
        # Keyboard always active for chat input (assuming the game isn't over/won)
        if ev.type == pygame.KEYDOWN:
            if ev.key == pygame.K_RETURN:
                self.submit_question()
            elif ev.key == pygame.K_BACKSPACE:
                self.input_text = self.input_text[:-1]
            else:
                if ev.unicode and ev.key != pygame.K_ESCAPE:
                    self.input_text += ev.unicode
            return

        # Mouse events only if inside our rect
        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION, pygame.MOUSEWHEEL):
            mx, my = pygame.mouse.get_pos()
            inside = self.rect.collidepoint(mx, my)

            if ev.type == pygame.MOUSEWHEEL:
                if not inside:
                    return
                mods = pygame.key.get_mods()
                if mods & pygame.KMOD_SHIFT:
                    self.button_scroll_offset -= ev.y * 30
                else:
                    total_h = self.calc_total_height()
                    if total_h > self.CHAT_AREA_HEIGHT:
                        self.scroll_velocity -= ev.y * self.scroll_step
                return

            if not inside and ev.type != pygame.MOUSEBUTTONDOWN:
                return

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                # Ask button
                if self.ask_button_rect and self.ask_button_rect.collidepoint(ev.pos):
                    self.submit_question()
                    return

                # Arrows first (consume click)
                if self.left_arrow_rect and self.left_arrow_rect.collidepoint(ev.pos):
                    self.button_scroll_offset -= 120
                    self.button_scroll_offset = max(0, self.button_scroll_offset)
                    return
                if self.right_arrow_rect and self.right_arrow_rect.collidepoint(ev.pos):
                    self.button_scroll_offset += 120
                    self.button_scroll_offset = max(0, self.button_scroll_offset)
                    return

                # Scrollbar drag
                if self.scrollbar_rect and self.scrollbar_rect.collidepoint(ev.pos):
                    self.dragging_scrollbar = True
                    self.drag_start_y = ev.pos[1]
                    self.scroll_start_offset = self.scroll_offset
                    return

                # Predefined buttons → send prompt to SLM
                for rect, (label, prompt) in zip(self.predefined_button_rects, self.predefined_buttons):
                    if rect.width > 0 and rect.collidepoint(ev.pos):
                        self.submit_question(prompt)
                        if self.pop_sound:
                            try:
                                self.pop_sound.play()
                            except Exception:
                                pass
                        return


            elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                self.dragging_scrollbar = False

            elif ev.type == pygame.MOUSEMOTION and self.dragging_scrollbar and self.scrollbar_rect:
                total_h = self.calc_total_height()
                max_scroll = max(0, total_h - self.CHAT_AREA_HEIGHT)
                bar_h = self.scrollbar_rect.height
                track_h = self.CHAT_AREA_HEIGHT - bar_h
                if track_h > 0:
                    dy = ev.pos[1] - self.drag_start_y
                    self.scroll_offset = self.scroll_start_offset + (dy / track_h) * max_scroll
                    self.scroll_offset = clamp(self.scroll_offset, 0, max_scroll)

    def submit_question(self, prompt: str = None):
        text = prompt if prompt else self.input_text.strip()
        if not text:
            return
        self.chat_history.append(("You", text))

        if self.pop_sound:
            try:
                self.pop_sound.play()
            except Exception:
                pass

        try:
            resp = chat_with_slm(text)
        except Exception as e:
            resp = f"[Error contacting SLM: {e}]"

        if self.pop_sound:
            try:
                self.pop_sound.play()
            except Exception:
                pass

        self.chat_history.append(("AquaGuide", resp))
        if not prompt:
            self.input_text = ""

        total_h = self.calc_total_height()
        if total_h > self.CHAT_AREA_HEIGHT:
            self.scroll_offset = total_h - self.CHAT_AREA_HEIGHT
        else:
            self.scroll_offset = 0

# ======================================================================
#                        LAWN SIMULATOR (Right Pane)
# ======================================================================
WHITE = (255, 255, 255)
BLACK = (20, 20, 20)
BG_TOP_GAME = (135, 206, 235)
BG_BOTTOM_GAME = (176, 224, 230)
BUTTON_BG = (170, 220, 170)
BUTTON_BORDER = (100, 160, 100)
PANEL_BG = (147, 196, 195)
PANEL_BORDER = (100, 140, 150)
AQUA = (91, 155, 213)
GOLD = (247, 208, 96)
GREEN = (40, 150, 90)
YELLOW = (243, 191, 63)
RED = (215, 83, 79)
DIVIDER_COLOR = (60, 60, 60)  # subtle dark gray
DIVIDER_W = 4                 # thin divider bar

@dataclass
class GrassType:
    name: str
    multiplier: float
    note: str

# Ranked by water need (higher need → lower multiplier)
GRASS_TYPES = [
    GrassType("St. Augustine", 0.8, "Thirstiest, needs frequent irrigation."),
    GrassType("Bermuda", 0.9, "Moderate–high water need, sun-loving."),
    GrassType("Zoysia", 1.0, "Balanced, moderate water need."),
    GrassType("Bahia", 1.1, "Drought-tolerant, lowest water need."),
]


MOW_HEIGHTS = ["High", "Medium", "Low"]
MOW_FREQS = ["Rare", "Normal", "Often"]
WATERING_OPTS = [
    "Light Frequent",
    "Light Infrequent",
    "Heavy Frequent",
    "Heavy Infrequent",
]

# --------------------------- QUIZ QUESTIONS ---------------------------
QUESTIONS_BY_MONTH = [
    {
        "month": 1,
        "prompt": "T/F: A single deep, infrequent watering is generally better for grass root development and drought resistance than several light, frequent waterings.",
        "is_true": True,
        "explanation": "Deep watering encourages deeper root systems, while frequent shallow watering keeps roots near the surface.",
    },
    {
        "month": 2,
        "prompt": "T/F: Leaving grass clippings on the lawn ('grasscycling') contributes to thatch buildup and should be avoided in eco-friendly lawn care.",
        "is_true": False,
        "explanation": "Grass clippings decompose quickly and return nutrients to the soil; they do not significantly contribute to thatch.",
    },
    {
        "month": 3,
        "prompt": "T/F: The Floridan Aquifer underlies all of Florida and parts of Georgia, Alabama, South Carolina, and Mississippi.",
        "is_true": True,
        "explanation": "The Floridan Aquifer is one of the most productive in the world, spanning Florida and four other states.",
    },
    {
        "month": 4,
        "prompt": "T/F: Scalping (cutting grass very short) improves lawn health by making grass regrow thicker and faster.",
        "is_true": False,
        "explanation": "Scalping stresses grass, weakens roots, and increases weeds and water use.",
    },
    {
        "month": 5,
        "prompt": "T/F: Fertilizer runoff is a major source of nutrient pollution in Florida's waterways and can contribute to harmful algal blooms.",
        "is_true": True,
        "explanation": "Runoff with nitrogen and phosphorus fuels algal blooms, harming ecosystems and water quality.",
    },
    {
        "month": 6,
        "prompt": "T/F: The Floridan Aquifer is primarily recharged by rainwater in areas with permeable soils and exposed porous limestone (recharge zones).",
        "is_true": True,
        "explanation": "Recharge happens quickly in sandy, porous areas like Central Florida.",
    },
    {
        "month": 7,
        "prompt": "T/F: Aerating compacted soil can reduce irrigation needs by improving water infiltration and root growth.",
        "is_true": True,
        "explanation": "Aeration promotes deeper roots and better water retention, reducing irrigation needs.",
    },
    {
        "month": 8,
        "prompt": "T/F: Over-pumping the Floridan Aquifer can cause saltwater intrusion, contaminating freshwater wells.",
        "is_true": True,
        "explanation": "Excess pumping lowers freshwater pressure, allowing saltwater to enter freshwater zones.",
    },
    {
        "month": 9,
        "prompt": "T/F: Watering lawns in the early morning is more efficient than at night because it reduces evaporation and disease risk.",
        "is_true": True,
        "explanation": "Morning watering reduces evaporation and lets grass dry quickly, lowering fungal risk.",
    },
    {
        "month": 10,
        "prompt": "T/F: Outdoor irrigation often accounts for more than half of residential water use in Florida.",
        "is_true": True,
        "explanation": "Landscape irrigation frequently exceeds 50% of household water use in Florida.",
    },
    {
        "month": 11,
        "prompt": "T/F: Mulching plant beds helps conserve soil moisture, suppress weeds, and reduce nearby turf's irrigation needs.",
        "is_true": True,
        "explanation": "Mulch conserves water, moderates temperature, and reduces competition from weeds.",
    },
    {
        "month": 12,
        "prompt": "T/F: Capturing rainwater in barrels or cisterns for irrigation reduces demand on the Floridan Aquifer.",
        "is_true": True,
        "explanation": "Rainwater harvesting offsets potable water irrigation, lowering aquifer withdrawals.",
    },
]


@dataclass
class Lawn:
    health: float = 100.0
    moisture: float = 55.0
    grass: GrassType = field(default_factory=lambda: GRASS_TYPES[0])
    root_depth: float = 3
    mow_height_idx: int = 0
    mow_freq_idx: int = 1
    watering_idx: int = 0
    last_watering: str = "None"

@dataclass
class Aquifer:
    level: float = 100.0

@dataclass
@dataclass
@dataclass
class GameState:
    lawn: Lawn = field(default_factory=Lawn)
    aquifer: Aquifer = field(default_factory=Aquifer)
    month_count: int = 1
    is_failing: bool = False
    fail_start_ms: int = 0
    in_game_over: bool = False
    in_game_won: bool = False

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
        # Label
        label = font.render(self.label, True, WHITE)
        surf.blit(label, (self.rect.x, self.rect.y - 26))

        w, h = self.rect.w, self.rect.h
        bar_surf = pygame.Surface((w, h), pygame.SRCALPHA)

        # Track background (dark capsule)
        pygame.draw.rect(bar_surf, (60, 60, 60), bar_surf.get_rect(), border_radius=8)

        # Filled region width
        fill_w = int(w * (self.value / 100.0))

        if fill_w > 0:
            # Solid fill
            fill_rect = pygame.Rect(0, 0, fill_w, h)
            pygame.draw.rect(bar_surf, self.color, fill_rect)

            # --- Diagonal stripes ONLY inside the filled region ---
            prev_clip = bar_surf.get_clip()
            bar_surf.set_clip(pygame.Rect(0, 0, fill_w, h))  # clip to filled area

            stripe_gap = 10  # spacing between stripes
            stripe_thickness = 2  # line thickness
            stripe_color = (255, 255, 255, 55)

            # "\" direction: top-left to bottom-right
            for x in range(-h, fill_w + h, stripe_gap):
                start = (x, h)
                end = (x + h, 0)
                pygame.draw.line(bar_surf, stripe_color, start, end, stripe_thickness)

            bar_surf.set_clip(prev_clip)

        # Clip everything to the rounded capsule shape (keeps rounded corners)
        mask = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=8)
        bar_surf.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        # Blit bar and draw outline
        surf.blit(bar_surf, (self.rect.x, self.rect.y))
        pygame.draw.rect(surf, WHITE, self.rect, width=2, border_radius=8)

        # Value text
        val_txt = small.render(f"{int(self.value)}", True, WHITE)
        surf.blit(val_txt, (self.rect.right - 32, self.rect.y + 2))


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
            img = pygame.transform.scale(img, target_size)  # nearest by default in SDL2 builds
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

def calculate_multiplier(state: GameState) -> float:
    lawn = state.lawn
    total = 1.0

    # Grass type base multiplier
    total *= lawn.grass.multiplier

    # Mowing height
    if lawn.mow_height_idx == 0:      # High
        total *= 1.05
    elif lawn.mow_height_idx == 1:    # Medium
        total *= 1.00
    else:                             # Low
        total *= 0.95

    # Mowing frequency
    if lawn.mow_freq_idx == 1:        # Normal
        total *= 1.00
    elif lawn.mow_freq_idx == 0:      # Rare
        total *= 1.05
    else:                             # Often
        total *= 0.95

    # Watering strategies
    watering_mults = {
        "Light Frequent": 0.85,
        "Light Infrequent": 1.0,
        "Heavy Frequent": 0.9,
        "Heavy Infrequent": 1.15,
    }
    total *= watering_mults.get(lawn.last_watering, 1.0)

    return total


def monthly_moisture_update(state: GameState):
    base_et = 8.0
    height = MOW_HEIGHTS[state.lawn.mow_height_idx]

    # evapotranspiration (ET) varies with mow height
    if height == "High":
        et = base_et * 0.85
    elif height == "Medium":
        et = base_et * 1.00
    else:  # Low
        et = base_et * 1.15

    # watering adds soil moisture instead of rain
    if state.lawn.last_watering == "Light Frequent":
        water = 10
    elif state.lawn.last_watering == "Light Infrequent":
        water = 5
    elif state.lawn.last_watering == "Heavy Frequent":
        water = 20
    elif state.lawn.last_watering == "Heavy Infrequent":
        water = 10
    else:
        water = 0

    # update soil moisture (water in – ET out)
    state.lawn.moisture = clamp(state.lawn.moisture + water - et, 0, 100)

    # aquifer depletion happens here too
    state.aquifer.level = clamp(state.aquifer.level - water * 0.5, 0, 100)

def apply_next_month(state: GameState):
    if state.in_game_over or state.in_game_won:
        return

    state.lawn.last_watering = WATERING_OPTS[state.lawn.watering_idx]

    # ----- AQUIFER DEPLETION FROM WATERING -----
    if state.lawn.last_watering == "Light Frequent":
        state.aquifer.level = clamp(state.aquifer.level - 9, 0, 100)
    elif state.lawn.last_watering == "Light Infrequent":
        state.aquifer.level = clamp(state.aquifer.level - 2, 0, 100)
    elif state.lawn.last_watering == "Heavy Frequent":
        state.aquifer.level = clamp(state.aquifer.level - 12, 0, 100)
    elif state.lawn.last_watering == "Heavy Infrequent":
        state.aquifer.level = clamp(state.aquifer.level - 4, 0, 100)

    mult = calculate_multiplier(state)
    state.lawn.health = clamp(state.lawn.health * mult, 0, 100)
    state.month_count += 1
    monthly_moisture_update(state)

    # ----- ROOT DEPTH UPDATE -----
    root_change = 0
    if state.lawn.watering_idx in (0, 2):  # frequent watering
        root_change -= 1
    else:  # infrequent watering
        root_change += 1

    state.lawn.root_depth = max(1, min(20, state.lawn.root_depth + root_change))

    # Check failure condition
    if state.lawn.root_depth <= 1 or state.lawn.health <= 40 or state.aquifer.level <= 0:
        state.is_failing = True
        state.fail_start_ms = pygame.time.get_ticks()
        state.in_game_over = True
        state.in_game_won = False
        return
    # -----------------------------

    if state.month_count > 12:
        state.in_game_won = True
        state.in_game_over = False


def game_over_overlay(surface: pygame.Surface, fonts):
    FONT, TITLE, SMALL = fonts
    # Darken the entire window
    overlay = pygame.Surface((TOTAL_W, TOTAL_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))  # slightly darker than before
    surface.blit(overlay, (0, 0))

    # Centered messages across full screen
    msg1 = TITLE.render("Game Over", True, RED)
    msg2 = FONT.render("Your lawn failed. Press R to restart.", True, WHITE)
    msg3 = SMALL.render("Tip: Taller mowing + deep watering helps!", True, WHITE)

    cx, cy = TOTAL_W // 2, TOTAL_H // 2
    surface.blit(msg1, msg1.get_rect(center=(cx, cy - 30)))
    surface.blit(msg2, msg2.get_rect(center=(cx, cy + 10)))
    surface.blit(msg3, msg3.get_rect(center=(cx, cy + 40)))

def game_won_overlay(surface: pygame.Surface, fonts):
    FONT, TITLE, SMALL = fonts
    overlay = pygame.Surface((TOTAL_W, TOTAL_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (0, 0))

    msg1 = TITLE.render("You Won!", True, GREEN)
    msg2 = FONT.render("Congratulations, you kept your lawn alive for 1 year!", True, WHITE)
    msg3 = SMALL.render("Press R to restart and try again.", True, WHITE)

    cx, cy = TOTAL_W // 2, TOTAL_H // 2
    surface.blit(msg1, msg1.get_rect(center=(cx, cy - 30)))
    surface.blit(msg2, msg2.get_rect(center=(cx, cy + 10)))
    surface.blit(msg3, msg3.get_rect(center=(cx, cy + 40)))

class WaterWisePane:
    def __init__(self, rect: pygame.Rect, chat: ChatUI):
        self.rect = rect.copy()
        self.W, self.H = rect.w, rect.h
        self.state = GameState()
        self.chat = chat

        # Panel and lawn
        panel_w = min(380, int(self.W * 0.58))
        self.panel_rect = pygame.Rect(self.rect.x + self.W - panel_w, self.rect.y, panel_w, self.H)
        self.lawn_rect  = pygame.Rect(self.rect.x, self.rect.y, self.W - panel_w, self.H)

        # Lawn images
        self.lawn_images = load_grass_images((self.lawn_rect.w, self.lawn_rect.h))

        # House image
        try:
            house_path = os.path.join(os.path.dirname(__file__), "House.png")
            self.house_img = pygame.image.load(house_path).convert_alpha()
            scale_w = int(self.lawn_rect.w * 0.45)
            scale_h = int(self.house_img.get_height() * (scale_w / self.house_img.get_width()))
            self.house_img = pygame.transform.scale(self.house_img, (scale_w, scale_h))
        except Exception:
            self.house_img = None

        # --- Sliders ---
        self.sliders = {
            "health":   SliderBar(pygame.Rect(self.panel_rect.x + 24,  90, self.panel_rect.w - 48, 22), "Lawn Health",  GREEN),
            "moisture": SliderBar(pygame.Rect(self.panel_rect.x + 24, 150, self.panel_rect.w - 48, 22), "Soil Moisture", AQUA),
            "aquifer":  SliderBar(pygame.Rect(self.panel_rect.x + 24, 210, self.panel_rect.w - 48, 22), "Aquifer Level", GOLD),
        }

        # --- Toggles ---
        self.tog_grass = ArrowToggle(
            pygame.Rect(self.panel_rect.x + 20, 270, self.panel_rect.w - 40, 70),
            "Grass Type", [g.name for g in GRASS_TYPES],
            get_index=lambda: GRASS_TYPES.index(self.state.lawn.grass),
            set_index=lambda i: setattr(self.state.lawn, "grass", GRASS_TYPES[i])
        )
        self.tog_height = ArrowToggle(
            pygame.Rect(self.panel_rect.x + 20, 360, self.panel_rect.w - 40, 70),
            "Mowing Height", MOW_HEIGHTS,
            get_index=lambda: self.state.lawn.mow_height_idx,
            set_index=lambda i: setattr(self.state.lawn, "mow_height_idx", i)
        )
        self.tog_freq = ArrowToggle(
            pygame.Rect(self.panel_rect.x + 20, 450, self.panel_rect.w - 40, 70),
            "Mowing Frequency", MOW_FREQS,
            get_index=lambda: self.state.lawn.mow_freq_idx,
            set_index=lambda i: setattr(self.state.lawn, "mow_freq_idx", i)
        )
        self.tog_water = ArrowToggle(
            pygame.Rect(self.panel_rect.x + 20, 540, self.panel_rect.w - 40, 70),
            "Watering", WATERING_OPTS,
            get_index=lambda: self.state.lawn.watering_idx,
            set_index=lambda i: setattr(self.state.lawn, "watering_idx", i)
        )

        # --- Next Month button ---
        self.btn_next = Button(
            pygame.Rect(self.panel_rect.x + 20, self.panel_rect.bottom - 60, self.panel_rect.w - 40, 46),
            "Go to Next Month  >>",
            lambda: self.handle_next_month()
        )

        # --- Group widgets ---
        self.toggles = [self.tog_grass, self.tog_height, self.tog_freq, self.tog_water]
        self.buttons = [self.btn_next]

    # ---------------- Methods ----------------

    def handle_next_month(self):
        """Show quiz before advancing to the next month."""
        if quiz_popup(self.state.month_count, screen, FONT, BUTTON_FONT):
            apply_next_month(self.state)

    def draw_root_visualization(self, surface: pygame.Surface, lawn_rect: pygame.Rect, root_depth: int):
        viz_w, viz_h = 120, 180
        viz_rect = pygame.Rect(lawn_rect.x + 20, lawn_rect.bottom - viz_h - 20, viz_w, viz_h)

        bg_surf = pygame.Surface(viz_rect.size, pygame.SRCALPHA)
        bg_surf.fill((0, 0, 0, 110))
        pygame.draw.rect(bg_surf, (255, 255, 255, 150), bg_surf.get_rect(), width=1, border_radius=8)
        surface.blit(bg_surf, viz_rect.topleft)

        ground_y = viz_rect.y + 25
        pygame.draw.line(surface, GREEN, (viz_rect.x, ground_y), (viz_rect.right, ground_y), 3)

        max_depth_px = viz_h - 40
        root_len = (root_depth / 20.0) * max_depth_px

        if root_len > 0:
            start_pos = (viz_rect.centerx, ground_y)
            end_pos = (viz_rect.centerx, ground_y + root_len)
            pygame.draw.line(surface, (210, 180, 140), start_pos, end_pos, 3)
            for i in range(1, 4):
                branch_y = ground_y + (root_len * (i / 3.5))
                branch_len = root_len * 0.2
                pygame.draw.line(surface, (210, 180, 140), (start_pos[0], branch_y),
                                 (start_pos[0] - branch_len, branch_y + 10), 2)
                pygame.draw.line(surface, (210, 180, 140), (start_pos[0], branch_y),
                                 (start_pos[0] + branch_len, branch_y + 10), 2)

        label = SMALL_FONT.render(f"Root Depth: {root_depth}", True, WHITE)
        surface.blit(label, label.get_rect(midtop=viz_rect.midtop).move(0, 5))

    def draw(self, surface: pygame.Surface):
        # Background
        draw_vertical_gradient(surface, self.rect, BG_TOP_GAME, BG_BOTTOM_GAME)

        # Lawn
        key = health_to_grass_key(self.state.lawn.health)
        surface.blit(self.lawn_images[key], self.lawn_rect.topleft)

        # House
        if self.house_img:
            margin_x = 30  # pushes it left from right edge
            margin_y = 30  # pushes it down from top edge
            x = self.lawn_rect.right - self.house_img.get_width() - margin_x
            y = self.lawn_rect.top + margin_y
            surface.blit(self.house_img, (x, y))

        # Panel
        pygame.draw.rect(surface, PANEL_BG, self.panel_rect)
        pygame.draw.rect(surface, PANEL_BORDER, self.panel_rect, width=2)
        title = GAME_TITLE_FONT.render("LAWN SIMULATOR", True, WHITE)
        surface.blit(title, (self.panel_rect.x + 20, 16))
        sub = SMALL_FONT.render(f"Month #{self.state.month_count}   |   Grass: {self.state.lawn.grass.name}", True, WHITE)
        surface.blit(sub, (self.panel_rect.x + 20, 50))

        # Sliders
        self.sliders["health"].set_value(self.state.lawn.health)
        self.sliders["moisture"].set_value(self.state.lawn.moisture)
        self.sliders["aquifer"].set_value(self.state.aquifer.level)
        for k in ("health", "moisture", "aquifer"):
            self.sliders[k].draw(surface, FONT, SMALL_FONT)

        # Toggles & buttons
        for t in self.toggles:
            t.draw(surface, FONT, SMALL_FONT)
        for b in self.buttons:
            b.draw(surface, FONT)

        # Root visualization
        self.draw_root_visualization(surface, self.lawn_rect, self.state.lawn.root_depth)

        # Game state overlays
        if self.state.is_failing and not self.state.in_game_over:
            if pygame.time.get_ticks() - self.state.fail_start_ms >= 3000:
                self.state.in_game_over = True

        if self.state.in_game_over:
            game_over_overlay(surface, (FONT, GAME_TITLE_FONT, SMALL_FONT))
            return "over"
        elif self.state.in_game_won:
            game_won_overlay(surface, (FONT, GAME_TITLE_FONT, SMALL_FONT))
            return "won"

        return None

    def handle_event(self, ev: pygame.event.Event):
        if (self.state.in_game_over or self.state.in_game_won):
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_r:
                self.state = GameState()
                self.chat.disabled = False
            return

        if ev.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
            if not self.rect.collidepoint(pygame.mouse.get_pos()):
                return

        for b in self.buttons:
            b.handle_event(ev)
        for t in self.toggles:
            t.handle_event(ev)

    def handle_next_month(self):
        # show quiz before applying the next month
        if quiz_popup(self.state.month_count, screen, FONT, BUTTON_FONT):
            apply_next_month(self.state)

class ScreenState(Enum):
    INTRO = 1
    GAME = 2

# ----------------- INTRO CLASS -----------------
import pygame
import os

class IntroSlides:
    def __init__(self, size, FONT, TITLE_FONT):
        self.W, self.H = size
        self.FONT = FONT
        self.TITLE_FONT = TITLE_FONT

        self.typing_sound = None
        try:
            sound_path = os.path.join(os.path.dirname(__file__), "typewriter.wav")
            self.typing_sound = pygame.mixer.Sound(sound_path)
        except Exception:
            self.typing_sound = None

        # Slides: (background, text, text_color)
        self.slides = [
            ("black",
             "By the year 2045, regions of Florida including Orange, Osceola, Seminole, "
             "Polk, and Lake counties are expected to face a groundwater shortfall of an "
             "estimated 96 million gallons of water a day...",
             (255, 255, 255)),

            ("black",
             "Most of the region's water comes from the Floridian aquifer, a massive "
             "geologic formation spanning 100,000 square miles beneath Florida.",
             (255, 255, 255)),

            ("Aquifer.png",
             "Yet, despite these dire predictions, half of all water taken from the "
             "public supply ends up watering private lawns, dumping fresh water into the dirt.",
             (255, 255, 255)),

            ("black",
             "The more the aquifer drains, the more fragile the ground becomes... Not only can "
             "the disappearing fresh water trigger \"saltwater intrusion\" as seawater surges inland, "
             "but our relentless pumping drains the buoyant contents supporting the limestone "
             "caves underneath homes and highways, disrupting a delicate balance",
             (255, 255, 255)),

            ("Sinkhole.png",
             "...and resulting in sudden, catastrophic sinkholes that swallow up homes and cars whole.",
             (255, 255, 255)),

            ("black",
             "Your mission: Maintain a healthy lawn while using as little water as possible. "
             "Your lawn may fail if its roots are too shallow, its overall lawn health is below 40, or you have drained the whole aquifer."
             "If you can keep your lawn alive for one year without draining the aquifer, "
             "your mission is a success.",
             (255, 255, 255)),  # black text on light background
        ]

        self.current_slide = 0
        self.typed_text = ""
        self.char_index = 0
        self.typing_speed = 3.5     # frames per character
        self.frame_count = 0
        self.wait_timer = 0
        self.done = False

        #skip button stuff
        self.skip_rect = pygame.Rect(self.W - 140, self.H - 60, 120, 40)
        self.speed_multiplier = 1.0  # normal typing/waiting speed

    def update(self):
        """Advance typing effect and handle timing between slides."""
        if self.done:
            return True

        bg, text, color = self.slides[self.current_slide]

        if self.char_index < len(text):
            # Typing effect
            self.frame_count += 1
            if self.frame_count >= self.typing_speed / self.speed_multiplier:
                self.char_index += 1
                self.typed_text = text[:self.char_index]
                self.frame_count = 0

                # 🔊 Typing sound (skip spaces)
                if self.typing_sound and text[self.char_index - 1] != " ":
                    self.typing_sound.play()
        else:
            # Finished typing → wait before next slide
            self.wait_timer += self.speed_multiplier
            if self.wait_timer >= 90:  # ~0.5s

                if self.current_slide >= len(self.slides) - 2:
                    # ✅ For the last TWO slides, wait longer
                    if self.wait_timer >= 210:  # ~3s
                        if self.current_slide == len(self.slides) - 1:
                            # Last slide → end slideshow
                            self.done = True
                            return True
                        else:
                            # Second-to-last slide → advance to last
                            self.current_slide += 1
                            self.char_index = 0
                            self.typed_text = ""
                            self.frame_count = 0
                            self.wait_timer = 0
                else:
                    # Normal slide timing
                    self.current_slide += 1
                    self.char_index = 0
                    self.typed_text = ""
                    self.frame_count = 0
                    self.wait_timer = 0

        return False

    def handle_event(self, ev):
        """Handle input events for speeding up slides."""
        if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            if self.skip_rect.collidepoint(ev.pos):
                self.speed_multiplier = 5 #5X speed -- zoom!

    def draw(self, surface):
        if self.done:
            return

        bg, full_text, color = self.slides[self.current_slide]

        # --- Draw background first ---
        if bg == "black":
            surface.fill((0, 0, 0))
        else:
            try:
                img = pygame.image.load(os.path.join(os.path.dirname(__file__), bg)).convert()
                img = pygame.transform.scale(img, (self.W, self.H))
                surface.blit(img, (0, 0))
            except Exception:
                surface.fill((0, 0, 0))

        # --- Then draw text ---
        max_width = int(self.W * 0.6)
        lines = self.wrap_text(self.typed_text, self.FONT, max_width)
        line_heights = [self.FONT.size(line)[1] for line in lines]
        total_height = sum(line_heights) + (len(lines) - 1) * 10
        y = (self.H - total_height) // 2
        for line in lines:
            ts = self.FONT.render(line, True, color)
            surface.blit(ts, (self.W // 2 - ts.get_width() // 2, y))
            y += ts.get_height() + 10

        # --- Cursor ---
        if self.char_index < len(full_text) or pygame.time.get_ticks() % 1000 < 500:
            if lines:
                last_line = lines[-1]
                last_ts = self.FONT.render(last_line, True, color)
                cursor_x = self.W // 2 + (last_ts.get_width() // 2) + 5
                cursor_y = y - last_ts.get_height() - 10
                pygame.draw.line(surface, color,
                                 (cursor_x, cursor_y),
                                 (cursor_x, cursor_y + last_ts.get_height()), 2)

        # --- Finally draw Skip/Fast Button (always on top) ---
        if not self.done and self.skip_rect:
            pygame.draw.rect(surface, (200, 200, 200), self.skip_rect, border_radius=8)
            pygame.draw.rect(surface, (100, 100, 100), self.skip_rect, width=2, border_radius=8)

            label = ">> Faster" if self.speed_multiplier == 1.0 else "Fast!"
            txt = self.FONT.render(label, True, (0, 0, 0))
            surface.blit(txt, (
                self.skip_rect.centerx - txt.get_width() // 2,
                self.skip_rect.centery - txt.get_height() // 2
            ))

    def draw_fast_button(self, surface):
        if self.done:
            return
        # draw the same button, but with a bold outline so it's obvious
        pygame.draw.rect(surface, (200, 200, 200), self.skip_rect, border_radius=8)
        pygame.draw.rect(surface, (0, 0, 0), self.skip_rect, width=3, border_radius=8)  # thicker outline

        label = ">> Faster" if self.speed_multiplier == 1.0 else "Fast!"
        txt = self.FONT.render(label, True, (0, 0, 0))
        surface.blit(
            txt,
            (self.skip_rect.centerx - txt.get_width() // 2,
             self.skip_rect.centery - txt.get_height() // 2),
        )

    def wrap_text(self, text, font, max_width):
        """Word-wrap text to fit a max width."""
        words = text.split(" ")
        lines = []
        current = ""
        for w in words:
            test = current + w + " "
            if font.size(test)[0] <= max_width:
                current = test
            else:
                lines.append(current.strip())
                current = w + " "
        if current:
            lines.append(current.strip())
        return lines


def main():
    state = ScreenState.INTRO
    intro = IntroSlides((TOTAL_W, TOTAL_H), FONT, TITLE_FONT)

    clock = pygame.time.Clock()
    chat = ChatUI(CHAT_RECT, (FONT, TITLE_FONT, BUTTON_FONT))
    lawn = WaterWisePane(GAME_RECT, chat)

    running = True
    while running:
        dt = clock.tick(FPS)

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
                break
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                running = False
                break

            # Play pop sound on *any* button press (mouse clicks)
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                if chat.pop_sound:
                    try:
                        chat.pop_sound.play()
                    except Exception:
                        pass

            # Play pop sound on RETURN/ENTER key
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_RETURN:
                if chat.pop_sound:
                    try:
                        chat.pop_sound.play()
                    except Exception:
                        pass

            # Route events to both panes (mouse routed by pane containment)

            if state == ScreenState.INTRO:
                intro.handle_event(ev)  # let intro slides handle button click

            chat.handle_event(ev)
            lawn.handle_event(ev)

        # Updates
        if state == ScreenState.INTRO:
            done = intro.update()
            intro.draw(screen)

            intro.draw_fast_button(screen) #MAKE SURE THE BUTTON IS ON TOP

            if done:
                state = ScreenState.GAME

                # Start background music loop as soon as game begins
                if BG_LOOP:
                    BG_LOOP.play(loops=-1)

        elif state == ScreenState.GAME:
            chat.update(dt)
            chat.draw(screen)
            status = lawn.draw(screen)
            if status in ("over", "won"):
                chat.disabled = True

            # Divider bar
            divider_rect = pygame.Rect(GAME_RECT.right, 0, DIVIDER_W, TOTAL_H)
            pygame.draw.rect(screen, DIVIDER_COLOR, divider_rect)

        pygame.display.flip()

    if BG_LOOP:
        BG_LOOP.stop()

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()