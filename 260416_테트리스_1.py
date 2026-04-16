import random
import sys
from collections import deque

import pygame

# =========================
# 기본 설정
# =========================
CELL_SIZE = 28
COLS = 10
ROWS = 20
PLAY_X = 30
PLAY_Y = 30
PLAY_W = COLS * CELL_SIZE
PLAY_H = ROWS * CELL_SIZE
SIDE_X = PLAY_X + PLAY_W + 30
SCREEN_W = 760
SCREEN_H = 640
FPS = 60

BG_COLOR = (18, 18, 24)
PANEL_COLOR = (28, 30, 40)
GRID_COLOR = (45, 48, 62)
TEXT_COLOR = (235, 235, 240)
DIM_TEXT = (170, 170, 185)
ACCENT = (90, 190, 255)
GAME_OVER_COLOR = (255, 90, 90)
MENU_OVERLAY = (0, 0, 0, 170)
SUB_BOX = (35, 38, 50)
HOVER_BOX = (45, 50, 68)
SELECT_BOX = (48, 58, 82)

COLOR_MAP = {
    "I": (80, 240, 240),
    "O": (240, 240, 80),
    "T": (170, 90, 240),
    "S": (90, 220, 120),
    "Z": (240, 90, 90),
    "J": (90, 130, 240),
    "L": (240, 170, 70),
}

DIFFICULTY_OPTIONS = ["쉬움", "보통", "어려움"]
EASY_LOCK_DELAY = 0.5

# 4x4 기준 회전 상태
PIECES = {
    "I": [
        [
            "....",
            "IIII",
            "....",
            "....",
        ],
        [
            "..I.",
            "..I.",
            "..I.",
            "..I.",
        ],
        [
            "....",
            "....",
            "IIII",
            "....",
        ],
        [
            ".I..",
            ".I..",
            ".I..",
            ".I..",
        ],
    ],
    "O": [
        [
            ".OO.",
            ".OO.",
            "....",
            "....",
        ]
    ] * 4,
    "T": [
        [
            ".T..",
            "TTT.",
            "....",
            "....",
        ],
        [
            ".T..",
            ".TT.",
            ".T..",
            "....",
        ],
        [
            "....",
            "TTT.",
            ".T..",
            "....",
        ],
        [
            ".T..",
            "TT..",
            ".T..",
            "....",
        ],
    ],
    "S": [
        [
            ".SS.",
            "SS..",
            "....",
            "....",
        ],
        [
            ".S..",
            ".SS.",
            "..S.",
            "....",
        ],
        [
            "....",
            ".SS.",
            "SS..",
            "....",
        ],
        [
            "S...",
            "SS..",
            ".S..",
            "....",
        ],
    ],
    "Z": [
        [
            "ZZ..",
            ".ZZ.",
            "....",
            "....",
        ],
        [
            "..Z.",
            ".ZZ.",
            ".Z..",
            "....",
        ],
        [
            "....",
            "ZZ..",
            ".ZZ.",
            "....",
        ],
        [
            ".Z..",
            "ZZ..",
            "Z...",
            "....",
        ],
    ],
    "J": [
        [
            "J...",
            "JJJ.",
            "....",
            "....",
        ],
        [
            ".JJ.",
            ".J..",
            ".J..",
            "....",
        ],
        [
            "....",
            "JJJ.",
            "..J.",
            "....",
        ],
        [
            ".J..",
            ".J..",
            "JJ..",
            "....",
        ],
    ],
    "L": [
        [
            "..L.",
            "LLL.",
            "....",
            "....",
        ],
        [
            ".L..",
            ".L..",
            ".LL.",
            "....",
        ],
        [
            "....",
            "LLL.",
            "L...",
            "....",
        ],
        [
            "LL..",
            ".L..",
            ".L..",
            "....",
        ],
    ],
}

LEVEL_FRAMES = [
    48, 43, 38, 33, 28, 23, 18, 13, 8, 6,
    5, 5, 5, 4, 4, 4, 3, 3, 3, 2,
]

MOVE_SPEED_OPTIONS = [
    ("느림", 150),
    ("보통", 95),
    ("빠름", 55),
]
SOFT_DROP_OPTIONS = [
    ("느림", 70),
    ("보통", 45),
    ("빠름", 22),
]


def get_piece_cells(name, rotation):
    shape = PIECES[name][rotation % 4]
    cells = []
    for y, row in enumerate(shape):
        for x, ch in enumerate(row):
            if ch != ".":
                cells.append((x, y))
    return cells


def gravity_seconds_for_level(level):
    if level < len(LEVEL_FRAMES):
        frames = LEVEL_FRAMES[level]
    elif level < 29:
        frames = 2
    else:
        frames = 1
    return frames / 60.0


class TetrisGame:
    def __init__(self):
        self.start_level = 0
        self.difficulty_index = 1
        self.allow_reset_during_play = False
        self.move_speed_index = 1
        self.soft_drop_speed_index = 1
        self.reset()

    @property
    def difficulty_name(self):
        return DIFFICULTY_OPTIONS[self.difficulty_index]

    @property
    def show_ghost(self):
        return self.difficulty_name != "어려움"

    @property
    def easy_mode(self):
        return self.difficulty_name == "쉬움"

    def reset(self):
        self.board = [[None for _ in range(COLS)] for _ in range(ROWS)]
        self.queue = deque()
        self._fill_bag()
        self._fill_bag()
        self.current = None
        self.score = 0
        self.lines = 0
        self.level = self.start_level
        self.game_over = False
        self.gravity_timer = 0.0
        self.last_clear_count = 0
        self.lock_delay_timer = 0.0
        self.spawn_new_piece()

    def _fill_bag(self):
        bag = list(PIECES.keys())
        random.shuffle(bag)
        self.queue.extend(bag)

    def _pop_next_piece(self):
        if len(self.queue) < 7:
            self._fill_bag()
        return self.queue.popleft()

    def spawn_new_piece(self):
        name = self._pop_next_piece()
        self.current = {
            "name": name,
            "rot": 0,
            "x": 3,
            "y": -1,
        }
        self.lock_delay_timer = 0.0
        if self.collision(self.current["x"], self.current["y"], self.current["rot"]):
            self.game_over = True

    def collision(self, px, py, rot):
        name = self.current["name"]
        for cx, cy in get_piece_cells(name, rot):
            bx = px + cx
            by = py + cy
            if bx < 0 or bx >= COLS or by >= ROWS:
                return True
            if by >= 0 and self.board[by][bx] is not None:
                return True
        return False

    def is_touching_ground(self):
        return self.collision(self.current["x"], self.current["y"] + 1, self.current["rot"])

    def move(self, dx, dy):
        if self.game_over:
            return False
        nx = self.current["x"] + dx
        ny = self.current["y"] + dy
        if not self.collision(nx, ny, self.current["rot"]):
            self.current["x"] = nx
            self.current["y"] = ny
            if not self.is_touching_ground():
                self.lock_delay_timer = 0.0
            return True
        return False

    def rotate(self, direction):
        if self.game_over:
            return
        old_rot = self.current["rot"]
        new_rot = (old_rot + direction) % 4
        kicks = [(0, 0), (-1, 0), (1, 0), (-2, 0), (2, 0), (0, -1)]
        for kx, ky in kicks:
            nx = self.current["x"] + kx
            ny = self.current["y"] + ky
            if not self.collision(nx, ny, new_rot):
                self.current["rot"] = new_rot
                self.current["x"] = nx
                self.current["y"] = ny
                if not self.is_touching_ground():
                    self.lock_delay_timer = 0.0
                return

    def lock_piece(self):
        name = self.current["name"]
        for cx, cy in get_piece_cells(name, self.current["rot"]):
            bx = self.current["x"] + cx
            by = self.current["y"] + cy
            if 0 <= by < ROWS and 0 <= bx < COLS:
                self.board[by][bx] = name

        cleared = self.clear_lines()
        self.last_clear_count = cleared

        if cleared == 1:
            self.score += 100 * (self.level + 1)
        elif cleared == 2:
            self.score += 300 * (self.level + 1)
        elif cleared == 3:
            self.score += 500 * (self.level + 1)
        elif cleared >= 4:
            self.score += 800 * (self.level + 1)

        self.lines += cleared
        self.level = self.start_level + (self.lines // 10)
        self.gravity_timer = 0.0
        self.lock_delay_timer = 0.0
        self.spawn_new_piece()

    def clear_lines(self):
        remaining = [row for row in self.board if any(cell is None for cell in row)]
        cleared = ROWS - len(remaining)
        while len(remaining) < ROWS:
            remaining.insert(0, [None for _ in range(COLS)])
        self.board = remaining
        return cleared

    def _handle_post_drop_contact(self):
        if self.game_over:
            return
        if self.is_touching_ground():
            if self.easy_mode:
                if self.lock_delay_timer <= 0.0:
                    self.lock_delay_timer = 0.0001
            else:
                self.lock_piece()
        else:
            self.lock_delay_timer = 0.0

    def soft_drop_step(self):
        if self.game_over:
            return
        if self.move(0, 1):
            self.score += 1
            self._handle_post_drop_contact()
        else:
            if self.easy_mode:
                if self.lock_delay_timer <= 0.0:
                    self.lock_delay_timer = 0.0001
            else:
                self.lock_piece()

    def hard_drop(self):
        if self.game_over:
            return
        distance = 0
        while self.move(0, 1):
            distance += 1
        self.score += distance * 2
        self.lock_piece()

    def update(self, dt):
        if self.game_over:
            return

        self.gravity_timer += dt
        gravity_interval = gravity_seconds_for_level(self.level)

        while self.gravity_timer >= gravity_interval and not self.game_over:
            self.gravity_timer -= gravity_interval
            if self.move(0, 1):
                self._handle_post_drop_contact()
                if self.game_over:
                    return
                if self.easy_mode and self.lock_delay_timer > 0.0:
                    break
            else:
                if self.easy_mode:
                    if self.lock_delay_timer <= 0.0:
                        self.lock_delay_timer = 0.0001
                    break
                self.lock_piece()
                return

        if self.easy_mode and not self.game_over:
            if self.is_touching_ground():
                if self.lock_delay_timer > 0.0:
                    self.lock_delay_timer += dt
                else:
                    self.lock_delay_timer = dt
                if self.lock_delay_timer >= EASY_LOCK_DELAY:
                    self.lock_piece()
            else:
                self.lock_delay_timer = 0.0

    def preview_names(self, count=3):
        while len(self.queue) < count:
            self._fill_bag()
        return list(self.queue)[:count]


class UITextHelper:
    @staticmethod
    def draw_text(screen, text, font, color, x, y, align="topleft"):
        surf = font.render(text, True, color)
        rect = surf.get_rect()
        setattr(rect, align, (x, y))
        screen.blit(surf, rect)
        return rect

    @staticmethod
    def wrap_text(text, font, max_width):
        if text == "":
            return [""]
        words = text.split(" ")
        lines = []
        current = ""
        for word in words:
            test = word if current == "" else current + " " + word
            if font.size(test)[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
        return lines or [""]


TEXT = UITextHelper.draw_text
WRAP = UITextHelper.wrap_text


def draw_piece_mini(screen, name, x, y, mini_cell=18):
    panel = pygame.Rect(x, y, mini_cell * 4, mini_cell * 4)
    pygame.draw.rect(screen, SUB_BOX, panel, border_radius=8)
    shape = PIECES[name][0]
    for row_idx, row in enumerate(shape):
        for col_idx, ch in enumerate(row):
            if ch != ".":
                color = COLOR_MAP[name]
                rx = x + col_idx * mini_cell + 2
                ry = y + row_idx * mini_cell + 2
                rect = pygame.Rect(rx, ry, mini_cell - 4, mini_cell - 4)
                pygame.draw.rect(screen, color, rect, border_radius=4)


def draw_board(screen, game):
    board_rect = pygame.Rect(PLAY_X, PLAY_Y, PLAY_W, PLAY_H)
    pygame.draw.rect(screen, PANEL_COLOR, board_rect, border_radius=12)

    for y in range(ROWS):
        for x in range(COLS):
            cell_rect = pygame.Rect(
                PLAY_X + x * CELL_SIZE,
                PLAY_Y + y * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE,
            )
            pygame.draw.rect(screen, GRID_COLOR, cell_rect, 1)
            cell = game.board[y][x]
            if cell:
                inner = cell_rect.inflate(-3, -3)
                pygame.draw.rect(screen, COLOR_MAP[cell], inner, border_radius=5)

    if not game.game_over and game.current:
        name = game.current["name"]

        if game.show_ghost:
            ghost_y = game.current["y"]
            while not game.collision(game.current["x"], ghost_y + 1, game.current["rot"]):
                ghost_y += 1
            for cx, cy in get_piece_cells(name, game.current["rot"]):
                bx = game.current["x"] + cx
                by = ghost_y + cy
                if by >= 0:
                    rect = pygame.Rect(
                        PLAY_X + bx * CELL_SIZE + 7,
                        PLAY_Y + by * CELL_SIZE + 7,
                        CELL_SIZE - 14,
                        CELL_SIZE - 14,
                    )
                    pygame.draw.rect(screen, COLOR_MAP[name], rect, 2, border_radius=4)

        for cx, cy in get_piece_cells(name, game.current["rot"]):
            bx = game.current["x"] + cx
            by = game.current["y"] + cy
            if by >= 0:
                cell_rect = pygame.Rect(
                    PLAY_X + bx * CELL_SIZE,
                    PLAY_Y + by * CELL_SIZE,
                    CELL_SIZE,
                    CELL_SIZE,
                )
                inner = cell_rect.inflate(-3, -3)
                pygame.draw.rect(screen, COLOR_MAP[name], inner, border_radius=5)


def draw_side_panel(screen, game, font_small, font_medium, font_big):
    panel = pygame.Rect(SIDE_X, PLAY_Y, SCREEN_W - SIDE_X - 30, PLAY_H)
    pygame.draw.rect(screen, PANEL_COLOR, panel, border_radius=12)

    TEXT(screen, "TETRIS", font_big, ACCENT, SIDE_X + 20, PLAY_Y + 18)
    TEXT(screen, f"점수  {game.score}", font_medium, TEXT_COLOR, SIDE_X + 20, PLAY_Y + 70)
    TEXT(screen, f"라인  {game.lines}", font_medium, TEXT_COLOR, SIDE_X + 20, PLAY_Y + 102)
    TEXT(screen, f"레벨  {game.level}", font_medium, TEXT_COLOR, SIDE_X + 20, PLAY_Y + 134)
    TEXT(screen, f"난이도  {game.difficulty_name}", font_medium, TEXT_COLOR, SIDE_X + 20, PLAY_Y + 166)

    TEXT(screen, "다음 블록", font_medium, ACCENT, SIDE_X + 20, PLAY_Y + 214)
    for i, name in enumerate(game.preview_names(3)):
        draw_piece_mini(screen, name, SIDE_X + 20, PLAY_Y + 245 + i * 88)

    info_box = pygame.Rect(SIDE_X + 16, PLAY_Y + 508, panel.width - 32, 88)
    pygame.draw.rect(screen, SUB_BOX, info_box, border_radius=10)

    move_name = MOVE_SPEED_OPTIONS[game.move_speed_index][0]
    drop_name = SOFT_DROP_OPTIONS[game.soft_drop_speed_index][0]
    info_lines = [
        f"좌/우 속도: {move_name}   아래 속도: {drop_name}",
        "회전: R 시계 / Q 반시계   내리기: ↓ / SPACE",
        f"ESC 메뉴   ENTER 리셋: {'허용' if game.allow_reset_during_play else '게임오버 때만'}",
    ]
    line_y = info_box.y + 12
    for line in info_lines:
        TEXT(screen, line, font_small, DIM_TEXT, info_box.x + 12, line_y)
        line_y += 24


def draw_game_over(screen, font_big, font_small):
    overlay = pygame.Surface((PLAY_W, PLAY_H), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 160))
    screen.blit(overlay, (PLAY_X, PLAY_Y))
    TEXT(screen, "GAME OVER", font_big, GAME_OVER_COLOR, PLAY_X + PLAY_W // 2, PLAY_Y + 210, "center")
    TEXT(screen, "ENTER: 다시 시작 / ESC: 메뉴", font_small, TEXT_COLOR, PLAY_X + PLAY_W // 2, PLAY_Y + 255, "center")


class MenuSystem:
    def __init__(self, game):
        self.game = game
        self.open = False
        self.page = "main"
        self.index = 0
        self.scroll = 0
        self.content_rect = pygame.Rect(0, 0, 0, 0)
        self.close_rect = pygame.Rect(0, 0, 0, 0)
        self.back_rect = pygame.Rect(0, 0, 0, 0)
        self.item_rects = []
        self.left_arrow_rects = {}
        self.right_arrow_rects = {}
        self.main_items = ["게임 계속", "새 게임 시작", "설정", "난이도", "도움말", "종료"]
        self.settings_items = ["ENTER 즉시 리셋", "좌/우 이동 속도", "아래 이동 속도", "뒤로"]
        self.difficulty_items = ["시작 레벨", "난이도 모드", "이 설정으로 새 게임 시작", "뒤로"]

    def toggle(self):
        if self.open:
            self.close_menu()
        else:
            self.open_menu()

    def open_menu(self):
        self.open = True
        self.page = "main"
        self.index = 0
        self.scroll = 0

    def close_menu(self):
        self.open = False
        self.page = "main"
        self.index = 0
        self.scroll = 0

    def current_items(self):
        if self.page == "main":
            return self.main_items
        if self.page == "settings":
            return self.settings_items
        if self.page == "difficulty":
            return self.difficulty_items
        return []

    def move_cursor(self, amount):
        items = self.current_items()
        if items:
            self.index = (self.index + amount) % len(items)

    def scroll_help(self, amount):
        self.scroll = max(0, self.scroll + amount)

    def on_left(self):
        if self.page == "settings":
            if self.index == 0:
                self.game.allow_reset_during_play = not self.game.allow_reset_during_play
            elif self.index == 1:
                self.game.move_speed_index = (self.game.move_speed_index - 1) % len(MOVE_SPEED_OPTIONS)
            elif self.index == 2:
                self.game.soft_drop_speed_index = (self.game.soft_drop_speed_index - 1) % len(SOFT_DROP_OPTIONS)
        elif self.page == "difficulty":
            if self.index == 0:
                self.game.start_level = max(0, self.game.start_level - 1)
            elif self.index == 1:
                self.game.difficulty_index = (self.game.difficulty_index - 1) % len(DIFFICULTY_OPTIONS)

    def on_right(self):
        if self.page == "settings":
            if self.index == 0:
                self.game.allow_reset_during_play = not self.game.allow_reset_during_play
            elif self.index == 1:
                self.game.move_speed_index = (self.game.move_speed_index + 1) % len(MOVE_SPEED_OPTIONS)
            elif self.index == 2:
                self.game.soft_drop_speed_index = (self.game.soft_drop_speed_index + 1) % len(SOFT_DROP_OPTIONS)
        elif self.page == "difficulty":
            if self.index == 0:
                self.game.start_level = min(15, self.game.start_level + 1)
            elif self.index == 1:
                self.game.difficulty_index = (self.game.difficulty_index + 1) % len(DIFFICULTY_OPTIONS)

    def select(self):
        if self.page == "main":
            item = self.main_items[self.index]
            if item == "게임 계속":
                self.close_menu()
            elif item == "새 게임 시작":
                self.game.reset()
                self.close_menu()
            elif item == "설정":
                self.page = "settings"
                self.index = 0
            elif item == "난이도":
                self.page = "difficulty"
                self.index = 0
            elif item == "도움말":
                self.page = "help"
                self.scroll = 0
            elif item == "종료":
                pygame.quit()
                sys.exit()
        elif self.page == "settings":
            if self.index == 0:
                self.game.allow_reset_during_play = not self.game.allow_reset_during_play
            elif self.index == 1:
                self.game.move_speed_index = (self.game.move_speed_index + 1) % len(MOVE_SPEED_OPTIONS)
            elif self.index == 2:
                self.game.soft_drop_speed_index = (self.game.soft_drop_speed_index + 1) % len(SOFT_DROP_OPTIONS)
            elif self.index == 3:
                self.page = "main"
                self.index = 0
        elif self.page == "difficulty":
            if self.index == 0:
                self.game.start_level = (self.game.start_level + 1) % 16
            elif self.index == 1:
                self.game.difficulty_index = (self.game.difficulty_index + 1) % len(DIFFICULTY_OPTIONS)
            elif self.index == 2:
                self.game.reset()
                self.close_menu()
            elif self.index == 3:
                self.page = "main"
                self.index = 0
        elif self.page == "help":
            self.page = "main"
            self.index = 0
            self.scroll = 0

    def back(self):
        if self.page == "main":
            self.close_menu()
        else:
            self.page = "main"
            self.index = 0
            self.scroll = 0

    def handle_mouse_motion(self, pos):
        if not self.open:
            return
        for idx, rect in self.item_rects:
            if rect.collidepoint(pos):
                self.index = idx
                break

    def handle_mouse_click(self, pos):
        if not self.open:
            return False
        if self.close_rect.collidepoint(pos):
            self.back()
            return True
        if self.back_rect.collidepoint(pos):
            self.back()
            return True
        for idx, rect in self.item_rects:
            if rect.collidepoint(pos):
                self.index = idx
                if idx in self.left_arrow_rects and self.left_arrow_rects[idx].collidepoint(pos):
                    self.on_left()
                elif idx in self.right_arrow_rects and self.right_arrow_rects[idx].collidepoint(pos):
                    self.on_right()
                else:
                    self.select()
                return True
        return self.content_rect.collidepoint(pos)

    def handle_wheel(self, amount, mouse_pos):
        if not self.open:
            return False
        if self.page == "help" and self.content_rect.collidepoint(mouse_pos):
            self.scroll = max(0, self.scroll - amount * 28)
            return True
        return False

    def item_value_text(self, idx):
        if self.page == "settings":
            if idx == 0:
                return "허용" if self.game.allow_reset_during_play else "게임오버 후만"
            if idx == 1:
                return MOVE_SPEED_OPTIONS[self.game.move_speed_index][0]
            if idx == 2:
                return SOFT_DROP_OPTIONS[self.game.soft_drop_speed_index][0]
        elif self.page == "difficulty":
            if idx == 0:
                return str(self.game.start_level)
            if idx == 1:
                return DIFFICULTY_OPTIONS[self.game.difficulty_index]
        return ""

    def page_title(self):
        return {
            "main": "메뉴",
            "settings": "설정",
            "difficulty": "난이도",
            "help": "도움말",
        }[self.page]

    def draw_item_page(self, screen, panel, font_small, font_medium):
        self.item_rects = []
        self.left_arrow_rects = {}
        self.right_arrow_rects = {}
        self.content_rect = pygame.Rect(panel.x + 26, panel.y + 92, panel.width - 52, panel.height - 162)

        items = self.current_items()
        box_h = 58
        gap = 12
        box_y = self.content_rect.y + 8
        value_color = ACCENT

        for idx, item in enumerate(items):
            box_rect = pygame.Rect(self.content_rect.x + 6, box_y, self.content_rect.width - 12, box_h)
            selected = idx == self.index
            fill = SELECT_BOX if selected else SUB_BOX
            pygame.draw.rect(screen, fill, box_rect, border_radius=12)
            if selected:
                pygame.draw.rect(screen, ACCENT, box_rect, 2, border_radius=12)

            self.item_rects.append((idx, box_rect))
            TEXT(screen, item, font_medium, TEXT_COLOR, box_rect.x + 18, box_rect.centery, "midleft")

            value_text = self.item_value_text(idx)
            if value_text:
                left_arrow = pygame.Rect(box_rect.right - 132, box_rect.y + 13, 32, 32)
                right_arrow = pygame.Rect(box_rect.right - 42, box_rect.y + 13, 32, 32)
                self.left_arrow_rects[idx] = left_arrow
                self.right_arrow_rects[idx] = right_arrow
                for rect, label in ((left_arrow, "<"), (right_arrow, ">")):
                    hover = rect.collidepoint(pygame.mouse.get_pos())
                    pygame.draw.rect(screen, HOVER_BOX if hover else PANEL_COLOR, rect, border_radius=8)
                    TEXT(screen, label, font_medium, TEXT_COLOR, rect.centerx, rect.centery, "center")
                TEXT(screen, value_text, font_small, value_color, box_rect.right - 87, box_rect.centery, "center")

            box_y += box_h + gap

        tip = "방향키/마우스 조작 가능 · ENTER 선택 · ESC 뒤로"
        TEXT(screen, tip, font_small, DIM_TEXT, panel.centerx, panel.bottom - 20, "midbottom")

    def draw_help_page(self, screen, panel, font_small, font_medium):
        self.item_rects = []
        self.left_arrow_rects = {}
        self.right_arrow_rects = {}
        self.content_rect = pygame.Rect(panel.x + 28, panel.y + 92, panel.width - 56, panel.height - 150)

        help_paragraphs = [
            "게임 목표: 떨어지는 블록을 쌓아서 가로줄을 완성하고 지워 점수를 올린다.",
            "",
            "조작",
            "← / → : 좌우 이동",
            "↓ : 소프트 드롭",
            "R : 시계방향 회전",
            "Q : 반시계방향 회전",
            "SPACE : 하드 드롭",
            "ESC : 메뉴 열기 / 닫기",
            "ENTER : 게임오버 시 다시 시작",
            "설정에서 허용하면 게임 중에도 ENTER로 즉시 리셋 가능",
            "",
            "난이도 설명",
            "쉬움 : 블록이 바닥이나 다른 블록에 닿은 뒤 0.5초 동안 좌우 이동 가능",
            "보통 : 블록이 닿는 즉시 고정",
            "어려움 : 보통과 같지만 예상 착지 위치(고스트 블록)를 보여주지 않음",
            "",
            "레벨 증가 방식",
            "일반적인 테트리스처럼 10줄을 지울 때마다 레벨이 1 오르고 자동 낙하 속도가 빨라진다.",
            "시작 레벨은 메뉴 → 난이도에서 미리 정할 수 있다.",
            "",
            "마우스 메뉴 조작",
            "메뉴 항목 클릭으로 선택 가능",
            "좌우 화살표 버튼 클릭으로 속도, 시작 레벨, 난이도 변경 가능",
            "도움말이 길면 마우스 휠로 스크롤 가능",
        ]

        wrapped_lines = []
        max_width = self.content_rect.width - 18
        for paragraph in help_paragraphs:
            if paragraph == "":
                wrapped_lines.append(("", DIM_TEXT))
                continue
            color = ACCENT if paragraph in {"조작", "난이도 설명", "레벨 증가 방식", "마우스 메뉴 조작"} else TEXT_COLOR
            for line in WRAP(paragraph, font_small, max_width):
                wrapped_lines.append((line, color))

        line_h = 26
        total_height = len(wrapped_lines) * line_h
        max_scroll = max(0, total_height - self.content_rect.height + 8)
        self.scroll = max(0, min(self.scroll, max_scroll))

        old_clip = screen.get_clip()
        screen.set_clip(self.content_rect)
        y = self.content_rect.y - self.scroll + 4
        for line, color in wrapped_lines:
            if line == "":
                y += line_h
                continue
            TEXT(screen, line, font_small, color, self.content_rect.x + 4, y)
            y += line_h
        screen.set_clip(old_clip)

        pygame.draw.rect(screen, SUB_BOX, self.content_rect, 1, border_radius=10)

        if total_height > self.content_rect.height:
            track = pygame.Rect(self.content_rect.right - 8, self.content_rect.y + 6, 6, self.content_rect.height - 12)
            pygame.draw.rect(screen, PANEL_COLOR, track, border_radius=6)
            thumb_h = max(32, int(track.height * (self.content_rect.height / total_height)))
            thumb_y = track.y + int((track.height - thumb_h) * (self.scroll / max_scroll if max_scroll else 0))
            thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_h)
            pygame.draw.rect(screen, ACCENT, thumb, border_radius=6)

        self.back_rect = pygame.Rect(panel.centerx - 70, panel.bottom - 46, 140, 32)
        pygame.draw.rect(screen, HOVER_BOX if self.back_rect.collidepoint(pygame.mouse.get_pos()) else SUB_BOX, self.back_rect, border_radius=10)
        TEXT(screen, "뒤로", font_small, TEXT_COLOR, self.back_rect.centerx, self.back_rect.centery, "center")
        TEXT(screen, "마우스 휠로 스크롤 가능", font_small, DIM_TEXT, panel.x + 30, panel.bottom - 28)

    def draw(self, screen, font_small, font_medium, font_big):
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill(MENU_OVERLAY)
        screen.blit(overlay, (0, 0))

        panel = pygame.Rect(96, 56, SCREEN_W - 192, SCREEN_H - 112)
        pygame.draw.rect(screen, (26, 28, 38), panel, border_radius=18)
        pygame.draw.rect(screen, ACCENT, panel, 2, border_radius=18)

        self.close_rect = pygame.Rect(panel.right - 44, panel.y + 14, 28, 28)
        pygame.draw.rect(screen, HOVER_BOX if self.close_rect.collidepoint(pygame.mouse.get_pos()) else SUB_BOX, self.close_rect, border_radius=8)
        TEXT(screen, "X", font_small, TEXT_COLOR, self.close_rect.centerx, self.close_rect.centery, "center")
        TEXT(screen, self.page_title(), font_big, ACCENT, panel.centerx, panel.y + 22, "midtop")

        if self.page == "help":
            self.draw_help_page(screen, panel, font_small, font_medium)
        else:
            self.back_rect = pygame.Rect(0, 0, 0, 0)
            self.draw_item_page(screen, panel, font_small, font_medium)


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("테트리스")
    clock = pygame.time.Clock()

    font_small = pygame.font.SysFont("malgungothic", 18)
    font_medium = pygame.font.SysFont("malgungothic", 24)
    font_big = pygame.font.SysFont("malgungothic", 36, bold=True)

    game = TetrisGame()
    menu = MenuSystem(game)

    held = {"left": False, "right": False, "down": False}
    next_repeat = {"left": 0, "right": 0, "down": 0}
    initial_delay = 150

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        now = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.MOUSEMOTION and menu.open:
                menu.handle_mouse_motion(event.pos)

            elif event.type == pygame.MOUSEBUTTONDOWN and menu.open:
                if event.button == 1:
                    menu.handle_mouse_click(event.pos)
                elif event.button == 4:
                    menu.handle_wheel(1, event.pos)
                elif event.button == 5:
                    menu.handle_wheel(-1, event.pos)

            elif event.type == pygame.MOUSEWHEEL and menu.open:
                menu.handle_wheel(event.y, pygame.mouse.get_pos())

            elif event.type == pygame.KEYDOWN:
                if menu.open:
                    if event.key == pygame.K_ESCAPE:
                        menu.back()
                    elif event.key == pygame.K_UP:
                        menu.move_cursor(-1)
                    elif event.key == pygame.K_DOWN:
                        menu.move_cursor(1)
                    elif event.key == pygame.K_LEFT:
                        menu.on_left()
                    elif event.key == pygame.K_RIGHT:
                        menu.on_right()
                    elif event.key == pygame.K_PAGEUP:
                        menu.scroll_help(-120)
                    elif event.key == pygame.K_PAGEDOWN:
                        menu.scroll_help(120)
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_SPACE):
                        menu.select()
                    continue

                if event.key == pygame.K_ESCAPE:
                    menu.open_menu()
                elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if game.game_over or game.allow_reset_during_play:
                        game.reset()
                elif not game.game_over:
                    if event.key == pygame.K_LEFT:
                        game.move(-1, 0)
                        held["left"] = True
                        next_repeat["left"] = now + initial_delay
                    elif event.key == pygame.K_RIGHT:
                        game.move(1, 0)
                        held["right"] = True
                        next_repeat["right"] = now + initial_delay
                    elif event.key == pygame.K_DOWN:
                        game.soft_drop_step()
                        held["down"] = True
                        next_repeat["down"] = now + initial_delay
                    elif event.key == pygame.K_r:
                        game.rotate(1)
                    elif event.key == pygame.K_q:
                        game.rotate(-1)
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()

            elif event.type == pygame.KEYUP and not menu.open:
                if event.key == pygame.K_LEFT:
                    held["left"] = False
                elif event.key == pygame.K_RIGHT:
                    held["right"] = False
                elif event.key == pygame.K_DOWN:
                    held["down"] = False

        if not menu.open and not game.game_over:
            lr_interval = MOVE_SPEED_OPTIONS[game.move_speed_index][1]
            down_interval = SOFT_DROP_OPTIONS[game.soft_drop_speed_index][1]

            if held["left"] and now >= next_repeat["left"]:
                while now >= next_repeat["left"]:
                    game.move(-1, 0)
                    next_repeat["left"] += lr_interval

            if held["right"] and now >= next_repeat["right"]:
                while now >= next_repeat["right"]:
                    game.move(1, 0)
                    next_repeat["right"] += lr_interval

            if held["down"] and now >= next_repeat["down"]:
                while now >= next_repeat["down"]:
                    game.soft_drop_step()
                    next_repeat["down"] += down_interval
                    if game.game_over:
                        break

            game.update(dt)

        screen.fill(BG_COLOR)
        draw_board(screen, game)
        draw_side_panel(screen, game, font_small, font_medium, font_big)

        if game.game_over:
            draw_game_over(screen, font_big, font_small)

        if menu.open:
            menu.draw(screen, font_small, font_medium, font_big)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
