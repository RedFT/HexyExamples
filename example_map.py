from __future__ import annotations
from collections import deque

import numpy as np
import hexy as hx
import pygame as pg

from example_hex import ExampleHex
from example_hex import make_hex_surface

TARGET_FPS = 60

HEX_RADIUS = 30
VIEWPORT_PIXEL_SIZE = (1600, 1600)

COLORS = np.array([
    [244, 98, 105],  # red
    [251, 149, 80],  # orange
    [141, 207, 104],  # green
    [53, 111, 163],  # water blue
    [85, 163, 193],  # sky blue
])


class Selection:
    class Type:
        POINT = 0
        RING = 1
        DISK = 2
        LINE = 3
        SPIRAL = 4

        @staticmethod
        def to_string(selection_type):
            if selection_type == Selection.Type.DISK:
                return "disk"
            elif selection_type == Selection.Type.RING:
                return "ring"
            elif selection_type == Selection.Type.LINE:
                return "line"
            elif selection_type == Selection.Type.SPIRAL:
                return "spiral"
            else:
                return "point"

    @staticmethod
    def get_selection(selection_type: Type, cube_mouse, selection_radius: ClampedInteger, clicked_hex=None):
        """

        Args:
            selection_type: The shape of the selection brush

            cube_mouse: cube_mouse is the cube coordinate of the potential hex at mouse coordinates : a triple of
            cube coordinates selection_radius: the size of the "selection brush"

            selection_radius : the size of the selection surface (radius for a circle, ring, spiral, length of a
            line, etc ...)

            clicked_hex: the cube coordinate current selected hex (the most recently clicked) : a triple of cube coordinates

        Returns: the list of hexes that would fit the selection

        @note : all selection functions in hexy use CUBE coordinates (hexy doc should be updated to reflect this)

        """
        if selection_type == Selection.Type.DISK:
            return hx.get_disk(cube_mouse, selection_radius.value)
        elif selection_type == Selection.Type.RING:
            return hx.get_ring(cube_mouse, selection_radius.value)
        elif selection_type == Selection.Type.LINE:
            return hx.get_hex_line(clicked_hex, cube_mouse)
        elif selection_type == Selection.Type.SPIRAL:
            click_rad = int(hx.get_cube_distance([0, 0, 0], clicked_hex))
            mouse_rad = int(hx.get_cube_distance([0, 0, 0], cube_mouse))
            return hx.get_spiral([0, 0, 0],
                                 min(click_rad, mouse_rad),
                                 max(click_rad, mouse_rad))
        else:
            return np.array([cube_mouse.copy()])


class ClampedInteger:
    """
    A simple class for "clamping" an integer value between a range. Its value will not increase beyond `upper_limit`
    and will not decrease below `lower_limit`.
    """

    def __init__(self, initial_value, lower_limit, upper_limit):
        self.value = initial_value
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

    def __iadd__(self, other):
        self.value = min(self.value + other, self.upper_limit)
        return self

    def __isub__(self, other):
        self.value = max(self.value - other, self.lower_limit)
        return self


class CyclicInteger:
    """
    A simple helper class for "cycling" an integer through a range of values. Its value will be set to `lower_limit`
    if it increases above `upper_limit`. Its value will be set to `upper_limit` if its value decreases below
    `lower_limit`.
    """

    def __init__(self, initial_value, lower_limit, upper_limit):
        self.value = initial_value
        self.lower_limit = lower_limit
        self.upper_limit = upper_limit

    def __iadd__(self, other):
        self.value += other
        if self.value > self.upper_limit:
            self.value = self.lower_limit
        return self

    def __isub__(self, other):
        self.value -= other
        if self.value < self.lower_limit:
            self.value = self.upper_limit
        return self


class ExampleHexMap:
    def __init__(self, viewport_pixel_size=VIEWPORT_PIXEL_SIZE, hex_radius=HEX_RADIUS, caption="ExampleHexMap"):
        self.viewport_pixel_size = viewport_pixel_size
        self.caption = caption

        # Pygame parameters
        self.size = np.array(viewport_pixel_size)
        self.width, self.height = self.size
        # Pixel center coordinate
        self.center = self.size / 2

        self.hex_radius = hex_radius

        self.hex_map = hx.HexMap()
        self.max_coord = 8

        self.selection_radius = ClampedInteger(3, 1, 5)

        self.selected_hex_image = make_hex_surface(
            (128, 128, 128, 180),
            self.hex_radius,
            (255, 255, 255),
            hollow=False,
            border=5)

        self.selection_type = CyclicInteger(3, 0, 4)
        self._clicked_hex_as_cube_coord = np.array([[0, 0, 0]])

        # Get all possible coordinates within `self.max_coord` as radius.
        all_coordinates = hx.get_disk(np.array((0, 0, 0)), self.max_coord)
        col_idx = np.random.randint(0, 4, len(all_coordinates))

        # Convert `all_coordinates` (that are cube coordinate) to axial coordinates, create hexes and randomly filter
        # out some hexes.
        hexes = []
        num_shown_hexes = np.random.binomial(len(all_coordinates), .95)
        axial_coordinates = hx.cube_to_axial(all_coordinates)
        axial_coordinates = axial_coordinates[np.random.choice(len(axial_coordinates), num_shown_hexes, replace=False)]

        for i, axial in enumerate(axial_coordinates):
            hex_color = list(COLORS[col_idx[i]])
            hex_color.append(255)
            hexes.append(ExampleHex(axial, hex_color, hex_radius))
            hexes[-1].set_value(i)  # the number at the center of the hex

        self.hex_map[np.array(axial_coordinates)] = hexes

        # pygame specific variables
        self.main_surf = None
        self.font = None
        self.clock = None
        self.init_pg()

    @property
    def clicked_hex_as_cube_coord(self):
        return self._clicked_hex_as_cube_coord[0]

    @property
    def clicked_hex_axial_coord(self):
        return hx.cube_to_axial(self._clicked_hex_as_cube_coord)

    def init_pg(self):
        pg.init()
        self.main_surf = pg.display.set_mode(self.viewport_pixel_size)
        pg.display.set_caption(self.caption)

        pg.font.init()
        self.font = pg.font.SysFont("monospace", 14, True)
        self.clock = pg.time.Clock()

    def handle_events(self):
        running = True
        for event in pg.event.get():
            if event.type == pg.QUIT:
                running = False

            if event.type == pg.MOUSEBUTTONDOWN:
                if event.button == 1:
                    self._clicked_hex_as_cube_coord = hx.pixel_to_cube(
                        np.array([pg.mouse.get_pos() - self.center]),
                        self.hex_radius)
                if event.button == 3:
                    self.selection_type += 1
                if event.button == 4:
                    self.selection_radius += 1
                if event.button == 5:
                    self.selection_radius -= 1

            if event.type == pg.KEYUP:
                if event.key == pg.K_UP:
                    self.selection_radius += 1
                elif event.key == pg.K_DOWN:
                    self.selection_radius -= 1

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_ESCAPE:
                    running = False

        return running

    def main_loop(self):
        running = self.handle_events()

        return running

    def draw(self):
        # Draw all hexes
        hexagons = list(self.hex_map.values())
        # hex_positions = np.array([hexagon.get_draw_position() for hexagon in hexagons])
        # sorted_indexes = np.argsort(hex_positions[:, 1])
        # for index in sorted_indexes:
        #     self.main_surf.blit(hexagons[index].image, hex_positions[index] + self.center)
        self.main_surf.blits((hexagon.image, hexagon.get_draw_position() + self.center) for hexagon in hexagons)

        # draw numbers on the hexes
        for hexagon in list(self.hex_map.values()):
            text = self.font.render(str(hexagon.value), False, (0, 0, 0))
            text.set_alpha(160)
            text_pos = hexagon.get_position() + self.center
            text_pos -= (text.get_width() / 2, text.get_height() / 2)
            self.main_surf.blit(text, text_pos)

        mouse_pos = np.array([pg.mouse.get_pos()]) - self.center

        # pixel_to_cube is meant to be able to convert many pixels to cube coordinates, so it's output and input
        # `mouse_pos` are 2d arrays. We want the only want the first element here; hence the `[0]`
        # This pos is totally "theorical" and it is possible that here is no hex at these cube coords in the hexmap
        mouse_pos_as_cube_coord = hx.pixel_to_cube(mouse_pos, self.hex_radius)[0]

        # Get the selected hexes based in the currently active selection shape
        selected_hexes_cube_coords = Selection.get_selection(self.selection_type.value, mouse_pos_as_cube_coord,
                                                             self.selection_radius,
                                                             self.clicked_hex_as_cube_coord)

        selected_hexes_axial_coords = hx.cube_to_axial(selected_hexes_cube_coords)
        selected_hexes = self.hex_map[selected_hexes_axial_coords]

        # we exhaust the mapping iterator as efficiently as possible (because we don't care about the result just
        # about the drawing on screen side effect
        deque(map(self.draw_selected_hex, selected_hexes), maxlen=0)

        self.draw_HUD(mouse_pos, selected_hexes_cube_coords)

        # Update screen
        pg.display.update()
        # sneak the clearing of the buffer (not the displayed screen)
        # Fill the Background color
        self.main_surf.fill(COLORS[-1])
        # Aim for 30 frames per second refresh rate
        self.clock.tick(TARGET_FPS)

    def draw_HUD(self, mouse_pos, selected_hexes_cube_coords):
        # draw "HUD"
        selection_type_text = self.font.render(
            "(Right Click To Change) Selection Type: " + Selection.Type.to_string(self.selection_type.value),
            True,
            (50, 50, 50))
        radius_text = self.font.render(
            "(Scroll Mouse Wheel To Change) Radius: " + str(self.selection_radius.value),
            True,
            (50, 50, 50))
        fps_text = self.font.render(" FPS: " + str(int(self.clock.get_fps())), True, (50, 50, 50))
        clicked_hx_coord = self.font.render(" clicked hex coord (cubic): " + str(self._clicked_hex_as_cube_coord),
                                            True,
                                            (50, 50, 50))
        clicked_hexes = self.hex_map[self.clicked_hex_axial_coord]
        clicked_hx_text = self.font.render(" clicked hex: " + str(clicked_hexes[0]) if clicked_hexes else "_", True,
                                           (50, 50, 50))
        mouse_pos_text = self.font.render(f" mouse pos : {pg.mouse.get_pos()} => {mouse_pos} ", True,
                                          (50, 50, 50))
        rad_hex_text = self.font.render(f"rad_hex selection {selected_hexes_cube_coords}", True,
                                        (50, 50, 50))

        display_driver_text = self.font.render(f"PG display driver: {pg.display.get_driver()}", True,  (50,50,50))
        self.main_surf.blit(fps_text, (5, 0))
        self.main_surf.blit(radius_text, (5, 15))
        self.main_surf.blit(selection_type_text, (5, 30))
        self.main_surf.blit(clicked_hx_coord, (5, 45))
        self.main_surf.blit(clicked_hx_text, (5, 60))
        self.main_surf.blit(mouse_pos_text, (self.viewport_pixel_size[0] - mouse_pos_text.get_width(), 0))
        self.main_surf.blit(display_driver_text, (self.viewport_pixel_size[0] - display_driver_text.get_width(), 15))
        self.main_surf.blit(rad_hex_text, (5, 75))

    def draw_selected_hex(self, hexagon):
        self.main_surf.blit(self.selected_hex_image, hexagon.get_draw_position() + self.center)

    def quit_app(self):
        pg.quit()
        raise SystemExit


if __name__ == '__main__':
    example_hex_map = ExampleHexMap()

    while example_hex_map.main_loop():
        example_hex_map.draw()

    example_hex_map.quit_app()
