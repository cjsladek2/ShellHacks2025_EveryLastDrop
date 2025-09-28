import pygame
import sys
from ChatWithSLMNew import chat_with_slm  # AquaGuide logic

# Initialize pygame
pygame.init()

# Screen setup
WIDTH, HEIGHT = 900, 650
screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("Chat with AquaGuide!")

# Fonts
# Fonts (using custom TTF)
FONT = pygame.font.Font("/Users/charlotte/Desktop/BloomandDoom/Minecraft.ttf", 20)
TITLE_FONT = pygame.font.Font("/Users/charlotte/Desktop/BloomandDoom/Minecraft.ttf", 38)
BUTTON_FONT = pygame.font.Font("/Users/charlotte/Desktop/BloomandDoom/Minecraft.ttf", 18)


# Color scheme (cute palette)
COLOR_AQUA   = (136, 199, 219)   # #88c7db
COLOR_BLUE   = (93, 151, 209)    # #5d97d1
COLOR_GREEN  = (197, 236, 172)   # #c5ecac
COLOR_YELLOW = (221, 223, 128)   # #dddf80

# Assign roles (ensure contrast between touching elements)
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

BUTTON_COLOR = COLOR_GREEN      # prompt buttons
BUTTON_HOVER = COLOR_YELLOW

SCROLLBAR_COLOR = (80, 80, 80, 160)

ARROW_BG = COLOR_BLUE
ARROW_HOVER = (60, 110, 180)    # darker blue: clear contrast vs aqua bottom bar

# Layout globals
CHAT_AREA_TOP = 80
CHAT_AREA_BOTTOM = HEIGHT - 140
CHAT_AREA_HEIGHT = CHAT_AREA_BOTTOM - CHAT_AREA_TOP

# Input + chat history
input_text = ""
chat_history = []
max_history = 100

# Cursor blink
cursor_visible = True
cursor_timer = 0
cursor_interval = 500

# Scroll physics (chat)
scroll_offset = 0.0
scroll_velocity = 0.0
scroll_damping = 0.85
scroll_step = 10

# Scrollbar drag
dragging_scrollbar = False
drag_start_y = 0
scroll_start_offset = 0

# Predefined buttons
predefined_buttons = [
    ("Watering Habits", "Please tell me about some eco-friendly watering habits for my lawn"),
    ("Mowing Habits", "Please tell me about the best mowing habits for my lawn to conserve water"),
    ("Soil Management", "Tell me about the best soil management techniques for my lawn"),
    ("Fertilization & Care", "Please tell me about the best fertilizer options for my lawn, to make my lawn healthy and conserve water"),
    ("Stress Conditioning", "Tell me about stress conditioning for my lawn"),
    ("Grass Species", "Tell me about the best grass species to build a healthy, ecofriendly, drought-tolerant lawn"),
    ("Native Landscaping", "Tell me about alternatives to grass — what else can I do with my lawn, such as native plants?"),
]

button_height = 36
button_spacing = 10
button_scroll_offset = 0

# Arrow buttons + dynamic rects initialized
left_arrow_rect = None
right_arrow_rect = None
button_rect = None
scrollbar_rect = None
predefined_button_rects = []


def wrap_text(text, font, max_width):
    """
    Wrap text into lines that fit max_width.
    Preserves paragraph breaks with controlled spacing.
    """
    lines = []
    paragraphs = text.split("\n")

    for idx, para in enumerate(paragraphs):
        words = para.split(" ")
        current_line = ""
        for word in words:
            test_line = current_line + word + " "
            if font.size(test_line)[0] <= max_width:
                current_line = test_line
            else:
                lines.append(current_line.strip())
                current_line = word + " "
        if current_line:
            lines.append(current_line.strip())

        # Add paragraph marker only if not the last paragraph
        if idx < len(paragraphs) - 1:
            lines.append("<PARA_BREAK>")

    return lines



def draw_gradient_background():
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        r = int(BG_TOP[0] * (1 - ratio) + BG_BOTTOM[0] * ratio)
        g = int(BG_TOP[1] * (1 - ratio) + BG_BOTTOM[1] * ratio)
        b = int(BG_TOP[2] * (1 - ratio) + BG_BOTTOM[2] * ratio)
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))


def draw_shadow_rect(surface, rect, color, radius=0, shadow_offset=(4, 4), shadow_alpha=80):
    shadow_rect = rect.move(*shadow_offset)
    shadow_surface = pygame.Surface((shadow_rect.width, shadow_rect.height), pygame.SRCALPHA)
    pygame.draw.rect(shadow_surface, (0, 0, 0, shadow_alpha), shadow_surface.get_rect(), border_radius=radius)
    surface.blit(shadow_surface, shadow_rect.topleft)
    pygame.draw.rect(surface, color, rect, border_radius=radius)


def calculate_total_height():
    y_offset = 0
    for speaker, msg in chat_history[-max_history:]:
        lines = wrap_text(msg, FONT, 420)
        lines = wrap_text(msg, FONT, 420)
        bubble_height = 0
        for line in lines:
            if line == "<PARA_BREAK>":
                bubble_height += 10  # small paragraph gap
            else:
                bubble_height += 28  # normal line height
        bubble_height += 24  # padding inside bubble
        y_offset += bubble_height + 20
    return y_offset


def draw_scrollbar(total_height):
    """Draw draggable scrollbar indicator."""
    global scrollbar_rect
    if total_height <= CHAT_AREA_HEIGHT:
        scrollbar_rect = None
        return

    bar_height = max(40, CHAT_AREA_HEIGHT * (CHAT_AREA_HEIGHT / total_height))
    max_scroll = total_height - CHAT_AREA_HEIGHT
    scroll_ratio = scroll_offset / max_scroll if max_scroll > 0 else 0
    bar_y = CHAT_AREA_TOP + int((CHAT_AREA_HEIGHT - bar_height) * scroll_ratio)

    scrollbar_rect = pygame.Rect(WIDTH - 12, bar_y, 8, bar_height)
    pygame.draw.rect(screen, SCROLLBAR_COLOR, scrollbar_rect, border_radius=3)


def draw_predefined_buttons():
    """Draw horizontally scrollable predefined prompt buttons inside arrow area (no fade)."""
    global predefined_button_rects, button_scroll_offset
    global left_arrow_rect, right_arrow_rect

    predefined_button_rects = []

    button_y = HEIGHT - 100
    arrow_width = 30
    margin = 10

    # Arrow button rects
    left_arrow_rect = pygame.Rect(margin, button_y, arrow_width, button_height)
    right_arrow_rect = pygame.Rect(WIDTH - margin - arrow_width, button_y, arrow_width, button_height)

    # Scrollable area between arrows
    scroll_area_x = left_arrow_rect.right + margin
    scroll_area_w = max(0, right_arrow_rect.left - margin - scroll_area_x)
    scroll_area_rect = pygame.Rect(scroll_area_x, button_y, scroll_area_w, button_height)

    # Compute button metrics
    button_metrics = []
    total_width = 0
    for label, _ in predefined_buttons:
        text_surface = BUTTON_FONT.render(label, True, (30, 30, 30))
        btn_width = text_surface.get_width() + 30
        button_metrics.append((label, btn_width, text_surface))
        total_width += btn_width + button_spacing
    if total_width > 0:
        total_width -= button_spacing  # remove last gap

    # Clamp scroll offset
    max_offset = max(0, total_width - scroll_area_w)
    button_scroll_offset = max(0, min(button_scroll_offset, max_offset))

    # Create row surface
    row_surface = pygame.Surface((max(total_width, 1), button_height), pygame.SRCALPHA)
    x_offset = 0
    mouse_pos = pygame.mouse.get_pos()

    # Determine if mouse is currently over either arrow (used to suppress hover)
    over_arrows = (
        (left_arrow_rect and left_arrow_rect.collidepoint(mouse_pos)) or
        (right_arrow_rect and right_arrow_rect.collidepoint(mouse_pos))
    )

    for (label, btn_width, text_surface), (_, prompt) in zip(button_metrics, predefined_buttons):
        rect_on_row = pygame.Rect(x_offset, 0, btn_width, button_height)

        # Screen rect for hover/click
        btn_rect_screen = pygame.Rect(
            scroll_area_x + rect_on_row.x - button_scroll_offset,
            button_y, rect_on_row.width, rect_on_row.height
        )
        visible = btn_rect_screen.colliderect(scroll_area_rect)

        # Only append if visible, otherwise store a zero rect (keeps indices aligned)
        predefined_button_rects.append(btn_rect_screen if visible else pygame.Rect(0, 0, 0, 0))

        # Hover highlight if visible + hovered, but NEVER while cursor is on an arrow
        hovered = (visible and not over_arrows and btn_rect_screen.collidepoint(mouse_pos))
        color = BUTTON_HOVER if hovered else BUTTON_COLOR

        # Draw button
        draw_shadow_rect(row_surface, rect_on_row, color, radius=8, shadow_offset=(2, 2), shadow_alpha=80)
        row_surface.blit(
            text_surface,
            (rect_on_row.centerx - text_surface.get_width() // 2,
             rect_on_row.centery - text_surface.get_height() // 2)
        )

        x_offset += btn_width + button_spacing

    # Blit row_surface into the scroll area
    screen.set_clip(scroll_area_rect)
    screen.blit(row_surface, (scroll_area_x - button_scroll_offset, button_y))
    screen.set_clip(None)

    # Draw arrows
    la_color = ARROW_HOVER if left_arrow_rect.collidepoint(mouse_pos) else ARROW_BG
    ra_color = ARROW_HOVER if right_arrow_rect.collidepoint(mouse_pos) else ARROW_BG
    draw_shadow_rect(screen, left_arrow_rect, la_color, radius=6, shadow_offset=(2, 2), shadow_alpha=80)
    draw_shadow_rect(screen, right_arrow_rect, ra_color, radius=6, shadow_offset=(2, 2), shadow_alpha=80)

    pygame.draw.polygon(
        screen, (255, 255, 255),
        [(left_arrow_rect.centerx + 6, left_arrow_rect.centery - 8),
         (left_arrow_rect.centerx - 6, left_arrow_rect.centery),
         (left_arrow_rect.centerx + 6, left_arrow_rect.centery + 8)]
    )
    pygame.draw.polygon(
        screen, (255, 255, 255),
        [(right_arrow_rect.centerx - 6, right_arrow_rect.centery - 8),
         (right_arrow_rect.centerx + 6, right_arrow_rect.centery),
         (right_arrow_rect.centerx - 6, right_arrow_rect.centery + 8)]
    )


def draw_chat():
    global button_rect

    screen.fill((0, 0, 0, 0))
    draw_gradient_background()

    # Title bar
    title_rect = pygame.Rect(0, 0, WIDTH, 70)
    draw_shadow_rect(screen, title_rect, TITLE_BAR, radius=0, shadow_offset=(0, 3), shadow_alpha=100)
    title_surface = TITLE_FONT.render("AquaGuide", True, (255, 255, 255))
    screen.blit(title_surface, (WIDTH // 2 - title_surface.get_width() // 2, 18))

    # Chat area
    chat_surface = pygame.Surface((WIDTH, CHAT_AREA_HEIGHT), pygame.SRCALPHA)
    y_offset = -scroll_offset
    for speaker, msg in chat_history[-max_history:]:
        lines = wrap_text(msg, FONT, 420)
        lines = wrap_text(msg, FONT, 420)
        bubble_height = 0
        for line in lines:
            if line == "<PARA_BREAK>":
                bubble_height += 10  # small paragraph gap
            else:
                bubble_height += 28  # normal line height
        bubble_height += 24  # padding inside bubble
        if speaker == "You":
            bubble_rect = pygame.Rect(WIDTH - 460, y_offset, 440, bubble_height)
            color = YOU_BUBBLE
            text_color = TEXT_COLOR
            align_left = False
        else:
            bubble_rect = pygame.Rect(20, y_offset, 440, bubble_height)
            color = AQUA_BUBBLE
            text_color = AQUA_TEXT
            align_left = True
        draw_shadow_rect(chat_surface, bubble_rect, color, radius=16, shadow_offset=(3, 3), shadow_alpha=70)
        line_y = y_offset + 14
        for line in lines:
            if line == "<PARA_BREAK>":
                line_y += 10  # smaller vertical gap than a full blank line
                continue
            text_surface = FONT.render(line, True, text_color)
            if align_left:
                chat_surface.blit(text_surface, (bubble_rect.x + 18, line_y))
            else:
                chat_surface.blit(text_surface, (bubble_rect.right - text_surface.get_width() - 18, line_y))
            line_y += 28  # normal line spacing

        y_offset += bubble_height + 20
    screen.blit(chat_surface, (0, CHAT_AREA_TOP))

    # Scrollbar
    total_height = calculate_total_height()
    draw_scrollbar(total_height)

    # Bottom bar (behind prompt buttons + input)
    bottom_bar_rect = pygame.Rect(0, HEIGHT - 120, WIDTH, 120)
    draw_shadow_rect(screen, bottom_bar_rect, BOTTOM_BAR, radius=0, shadow_offset=(0, -2), shadow_alpha=100)

    # Predefined buttons row (with fade + arrows)
    draw_predefined_buttons()

    # Input bar
    input_rect = pygame.Rect(20, HEIGHT - 50, WIDTH - 150, 42)
    draw_shadow_rect(screen, input_rect, INPUT_BG, radius=12, shadow_offset=(2, 2), shadow_alpha=90)
    text_surface = FONT.render(input_text, True, CURSOR_COLOR)
    screen.blit(text_surface, (input_rect.x + 14, input_rect.y + 12))

    # Cursor
    if cursor_visible:
        cursor_x = input_rect.x + 14 + text_surface.get_width() + 2
        cursor_y = input_rect.y + 12
        cursor_height = text_surface.get_height()
        pygame.draw.line(screen, CURSOR_COLOR, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_height), 2)

    # Ask button (dynamic)
    button_rect = pygame.Rect(WIDTH - 120, HEIGHT - 50, 100, 42)
    mouse_pos = pygame.mouse.get_pos()
    button_color = BUTTON_HOVER if button_rect.collidepoint(mouse_pos) else BUTTON_COLOR
    draw_shadow_rect(screen, button_rect, button_color, radius=8, shadow_offset=(2, 2), shadow_alpha=80)
    button_text = BUTTON_FONT.render("Ask", True, (0, 0, 0))
    screen.blit(
        button_text,
        (button_rect.centerx - button_text.get_width() // 2,
         button_rect.centery - button_text.get_height() // 2)
    )

    pygame.display.flip()


def submit_question(prompt=None):
    global input_text, chat_history, scroll_offset
    text = prompt if prompt else input_text.strip()
    if text:
        chat_history.append(("You", text))
        try:
            response = chat_with_slm(text)
        except Exception as e:
            response = f"[Error contacting SLM: {e}]"

        # TEST2
        pop_sound = pygame.mixer.Sound("soundeffects/pop.wav")
        pop_sound.play()

        #starts thinking
        chat_history.append(("AquaGuide", response))

        if not prompt:
            input_text = ""
        total_height = calculate_total_height()
        if total_height > CHAT_AREA_HEIGHT:
            scroll_offset = total_height - CHAT_AREA_HEIGHT
        else:
            scroll_offset = 0


def main():
    global input_text, cursor_visible, cursor_timer
    global scroll_offset, scroll_velocity, button_scroll_offset
    global dragging_scrollbar, drag_start_y, scroll_start_offset
    global WIDTH, HEIGHT, CHAT_AREA_TOP, CHAT_AREA_BOTTOM, CHAT_AREA_HEIGHT
    global button_rect, scrollbar_rect, predefined_button_rects, left_arrow_rect, right_arrow_rect
    global screen  # ensure resize uses the same global surface

    clock = pygame.time.Clock()
    running = True

    #TEST
    chat_history.append(("AquaGuide", "Hi! I'm AquaGuide, your personal AI Assistant to answer all your questions about sustainable lawn care and guide you through your water conservation journey. If you have any questions or want advice, just ask!"))

    while running:
        dt = clock.tick(60)
        cursor_timer += dt
        if cursor_timer >= cursor_interval:
            cursor_visible = not cursor_visible
            cursor_timer = 0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                WIDTH, HEIGHT = event.w, event.h
                screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
                CHAT_AREA_TOP = 80
                CHAT_AREA_BOTTOM = HEIGHT - 140
                CHAT_AREA_HEIGHT = CHAT_AREA_BOTTOM - CHAT_AREA_TOP

            elif event.type == pygame.MOUSEWHEEL:
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    button_scroll_offset -= event.y * 30
                else:
                    total_height = calculate_total_height()
                    if total_height > CHAT_AREA_HEIGHT:
                        scroll_velocity -= event.y * scroll_step

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Ask button
                    if button_rect and button_rect.collidepoint(event.pos):
                        submit_question()
                    else:
                        # --- ARROWS FIRST (exclusive priority) ---
                        if left_arrow_rect and left_arrow_rect.collidepoint(event.pos):
                            button_scroll_offset -= 120
                            # clamp immediately
                            # (draw_predefined_buttons will also clamp, but this keeps it snappy)
                            # quick clamp using a temporary max_offset guess; final clamp happens on next draw
                            button_scroll_offset = max(0, button_scroll_offset)
                            continue  # do not allow prompt buttons to process this click
                        if right_arrow_rect and right_arrow_rect.collidepoint(event.pos):
                            button_scroll_offset += 120
                            button_scroll_offset = max(0, button_scroll_offset)
                            continue  # same: consume click

                        # Scrollbar drag
                        if scrollbar_rect and scrollbar_rect.collidepoint(event.pos):
                            dragging_scrollbar = True
                            drag_start_y = event.pos[1]
                            scroll_start_offset = scroll_offset
                        else:
                            # --- Prompt buttons AFTER arrows ---
                            for (rect, (_, prompt)) in zip(predefined_button_rects, predefined_buttons):
                                if rect.width > 0 and rect.collidepoint(event.pos):
                                    submit_question(prompt)
                                    break

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    dragging_scrollbar = False

            elif event.type == pygame.MOUSEMOTION and dragging_scrollbar:
                if scrollbar_rect:
                    total_height = calculate_total_height()
                    max_scroll = max(0, total_height - CHAT_AREA_HEIGHT)
                    bar_height = scrollbar_rect.height
                    track_height = CHAT_AREA_HEIGHT - bar_height
                    if track_height > 0:
                        delta_y = event.pos[1] - drag_start_y
                        scroll_offset = scroll_start_offset + (delta_y / track_height) * max_scroll
                        scroll_offset = max(0, min(scroll_offset, max_scroll))

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:
                    submit_question()
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                else:
                    input_text += event.unicode

        # Apply inertia (chat)
        scroll_offset += scroll_velocity * dt / 16
        scroll_velocity *= scroll_damping
        total_height = calculate_total_height()
        max_scroll = max(0, total_height - CHAT_AREA_HEIGHT)
        if scroll_offset < 0:
            scroll_offset = 0
            scroll_velocity = 0
        elif scroll_offset > max_scroll:
            scroll_offset = max_scroll
            scroll_velocity = 0

        draw_chat()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()

