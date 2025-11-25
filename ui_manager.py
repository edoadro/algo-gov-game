"""
UI Manager for retro-styled text rendering and buttons
"""
import pygame
from settings import COLOR_TEXT, COLOR_BUTTON, COLOR_BUTTON_HOVER


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


class Button:
    """Simple clickable button with hover effect"""

    def __init__(self, x, y, width, height, text, font):
        """
        Initialize button

        Args:
            x, y: top-left position
            width, height: button dimensions
            text: button label
            font: pygame font object
        """
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.font = font
        self.hovered = False

    def update(self, mouse_pos):
        """Update hover state based on mouse position"""
        self.hovered = self.rect.collidepoint(mouse_pos)

    def is_clicked(self, mouse_pos, mouse_clicked):
        """Check if button was clicked"""
        return self.rect.collidepoint(mouse_pos) and mouse_clicked

    def draw(self, surface):
        """Draw the button"""
        # Choose color based on hover state
        color = COLOR_BUTTON_HOVER if self.hovered else COLOR_BUTTON

        # Draw button rectangle
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, COLOR_TEXT, self.rect, 2)  # Border

        # Draw text centered on button
        text_surface = self.font.render(self.text, True, COLOR_TEXT)
        text_rect = text_surface.get_rect(center=self.rect.center)
        surface.blit(text_surface, text_rect)
