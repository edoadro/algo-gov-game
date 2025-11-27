"""
UI Manager for retro-styled TUI rendering
Pokemon-style text box interface
"""
import pygame
from settings import COLOR_TEXT, COLOR_ACCENT, COLOR_BG


def draw_text(surface, text, font, color, x, y, center=False):
    """
    Draw text on the surface at the specified position

    Args:
        surface: pygame surface to draw on
        text: string to render
        font: pygame font object
        color: RGB tuple
        x, y: position coordinates
        center: if True, center the text at (x, y)
    """
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()

    if center:
        text_rect.center = (x, y)
    else:
        text_rect.topleft = (x, y)

    surface.blit(text_surface, text_rect)
    return text_rect


def draw_multiline_text(surface, text, font, color, x, y, max_width):
    """
    Draw text with word wrapping to fit within max_width

    Args:
        surface: pygame surface to draw on
        text: string to render (will be wrapped)
        font: pygame font object
        color: RGB tuple
        x, y: top-left position
        max_width: maximum width in pixels before wrapping

    Returns:
        Total height of rendered text block
    """
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        test_surface = font.render(test_line, True, color)

        if test_surface.get_width() > max_width:
            if len(current_line) == 1:
                # Single word is too long, just use it
                lines.append(test_line)
                current_line = []
            else:
                # Remove last word and start new line
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]

    # Add remaining words
    if current_line:
        lines.append(' '.join(current_line))

    # Draw all lines
    line_height = font.get_height()
    for i, line in enumerate(lines):
        draw_text(surface, line, font, color, x, y + i * line_height)

    return len(lines) * line_height


def measure_multiline_text(text, font, max_width):
    """
    Calculate height of text with word wrapping without drawing

    Args:
        text: string to measure
        font: pygame font object
        max_width: maximum width in pixels before wrapping

    Returns:
        int: Total height of text block
    """
    words = text.split(' ')
    lines = []
    current_line = []

    for word in words:
        current_line.append(word)
        test_line = ' '.join(current_line)
        # We need a dummy surface to measure size, but font.size() works without one usually
        # pygame.font.Font.size returns (width, height)
        w, h = font.size(test_line)

        if w > max_width:
            if len(current_line) == 1:
                lines.append(test_line)
                current_line = []
            else:
                current_line.pop()
                lines.append(' '.join(current_line))
                current_line = [word]

    if current_line:
        lines.append(' '.join(current_line))

    line_height = font.get_height()
    return len(lines) * line_height


def draw_text_box(surface, x, y, width, height, border_width=3):
    """
    Draw a Pokemon-style bordered text box

    Args:
        surface: pygame surface to draw on
        x, y: top-left position
        width, height: box dimensions
        border_width: thickness of border

    Returns:
        Inner rect (x, y, width, height) for content area
    """
    # Draw background
    pygame.draw.rect(surface, COLOR_BG, (x, y, width, height))

    # Draw border
    pygame.draw.rect(surface, COLOR_TEXT, (x, y, width, height), border_width)

    # Return inner content area (with padding)
    padding = 15
    return (x + padding, y + padding, width - 2*padding, height - 2*padding)


def draw_menu_options(surface, options, selected_index, font, x, y, line_spacing=35):
    """
    Draw a list of selectable text options with cursor

    Args:
        surface: pygame surface to draw on
        options: list of text strings
        selected_index: which option is currently selected (0-indexed)
        font: pygame font object
        x, y: starting position for first option
        line_spacing: vertical space between options

    Returns:
        Total height used
    """
    for i, option_text in enumerate(options):
        # Draw cursor for selected option
        if i == selected_index:
            cursor = "> "
            color = COLOR_ACCENT
        else:
            cursor = "  "
            color = COLOR_TEXT

        # Draw the option text with cursor
        full_text = cursor + option_text
        draw_text(surface, full_text, font, color, x, y + i * line_spacing)

    return len(options) * line_spacing

def draw_text_right(surface, text, font, color, x_right, y):
    """
    Draw text on the surface, right-aligned at x_right.
    
    Args:
        surface: pygame surface to draw on
        text: string to render
        font: pygame font object
        color: RGB tuple
        x_right, y: position coordinates (x_right is the rightmost point)
    """
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.topright = (x_right, y)
    surface.blit(text_surface, text_rect)
    return text_rect