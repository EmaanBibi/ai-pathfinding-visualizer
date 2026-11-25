"""
AI Pathfinding & Maze Visualizer
================================
An interactive Pygame app that shows how four classic AI search
algorithms (BFS, DFS, Dijkstra, A*) find a path through a grid maze.

Run:   python main.py
"""

import heapq
import random
import sys
import time
from collections import deque

import pygame

# ----------------------------------------------------------------------
# 1. SETTINGS
# ----------------------------------------------------------------------
ROWS = 40                  # number of grid rows
COLS = 40                  # number of grid columns
CELL = 16                  # size of one cell in pixels
GRID_W = COLS * CELL       # width of the grid area
GRID_H = ROWS * CELL       # height of the grid area
PANEL_W = 310              # width of the side panel (stats + help)
WIN_W = GRID_W + PANEL_W
WIN_H = GRID_H
FPS = 60

WALL_DENSITY = 0.28        # chance that a cell becomes a wall in a random maze
SPEEDS = [1, 2, 5, 10, 25, 50, 100]   # algorithm steps per frame
DEFAULT_SPEED_INDEX = 2

# Cell states (just numbers, so the grid is a simple 2D list of ints)
EMPTY, WALL, START, END, FRONTIER, EXPLORED, PATH = range(7)

# Colors (R, G, B)
COLORS = {
    EMPTY: (255, 255, 255),
    WALL: (30, 30, 40),
    START: (46, 204, 113),      # green
    END: (231, 76, 60),         # red
    FRONTIER: (255, 221, 87),   # yellow  -> waiting to be explored
    EXPLORED: (135, 206, 250),  # sky blue -> already explored
    PATH: (155, 89, 182),       # purple  -> final shortest path
}
GRID_LINE = (220, 220, 225)
PANEL_BG = (245, 246, 250)
TEXT = (40, 40, 50)
ACCENT = (52, 73, 94)


# ----------------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ----------------------------------------------------------------------
def get_neighbors(grid, cell):
    """Yield the up/down/left/right neighbors that are inside the grid
    and are not walls."""
    row, col = cell
    for d_row, d_col in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        n_row, n_col = row + d_row, col + d_col
        if 0 <= n_row < ROWS and 0 <= n_col < COLS:
            if grid[n_row][n_col] != WALL:
                yield (n_row, n_col)


def mark(grid, cell, state):
    """Change a cell's state for drawing, but never overwrite Start/End."""
    row, col = cell
    if grid[row][col] not in (START, END):
        grid[row][col] = state


def heuristic(a, b):
    """Manhattan distance: |row1 - row2| + |col1 - col2|.
    Used by A* as its 'guess' of how far the goal is."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from, start, end):
    """Walk backwards from End to Start using the came_from dictionary."""
    path = [end]
    current = end
    while current != start:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


# ----------------------------------------------------------------------
# 3. SEARCH ALGORITHMS
# ----------------------------------------------------------------------
# Each algorithm is a *generator*: it does ONE step of work, then
# `yield`s so the screen can redraw. This is what makes the animation
# smooth and step-by-step.
#
# `result` is a dictionary the algorithm fills in:
#   result["found"]      -> True / False
#   result["came_from"]  -> {cell: previous_cell} used to rebuild the path
#   result["explored"]   -> number of nodes explored so far
# ----------------------------------------------------------------------
def bfs(grid, start, end, result):
    """Breadth-First Search: explores level by level using a QUEUE (FIFO).
    Guarantees the shortest path when every step costs the same."""
    queue = deque([start])
    visited = {start}
    came_from = {}

    while queue:
        current = queue.popleft()
        result["explored"] += 1

        if current == end:
            result["found"], result["came_from"] = True, came_from
            return

        for neighbor in get_neighbors(grid, current):
            if neighbor not in visited:
                visited.add(neighbor)
                came_from[neighbor] = current
                queue.append(neighbor)
                mark(grid, neighbor, FRONTIER)

        mark(grid, current, EXPLORED)
        yield

    result["found"] = False


def dfs(grid, start, end, result):
    """Depth-First Search: goes as deep as possible first using a STACK (LIFO).
    Finds A path, but NOT necessarily the shortest one."""
    stack = [(start, None)]
    visited = set()
    came_from = {}

    while stack:
        current, parent = stack.pop()
        if current in visited:
            continue
        visited.add(current)
        came_from[current] = parent
        result["explored"] += 1

        if current == end:
            result["found"], result["came_from"] = True, came_from
            return

        for neighbor in get_neighbors(grid, current):
            if neighbor not in visited:
                stack.append((neighbor, current))
                mark(grid, neighbor, FRONTIER)

        mark(grid, current, EXPLORED)
        yield

    result["found"] = False


def dijkstra(grid, start, end, result):
    """Dijkstra's Algorithm: always expands the node with the smallest
    distance from the Start (using a PRIORITY QUEUE).
    Every step costs 1 here, so it behaves much like BFS, but it also
    works when steps have different costs."""
    counter = 0                       # tie-breaker so the heap never compares cells
    heap = [(0, counter, start)]
    distance = {start: 0}
    came_from = {}
    done = set()

    while heap:
        dist, _, current = heapq.heappop(heap)
        if current in done:
            continue
        done.add(current)
        result["explored"] += 1

        if current == end:
            result["found"], result["came_from"] = True, came_from
            return

        for neighbor in get_neighbors(grid, current):
            new_dist = dist + 1       # cost of one step
            if new_dist < distance.get(neighbor, float("inf")):
                distance[neighbor] = new_dist
                came_from[neighbor] = current
                counter += 1
                heapq.heappush(heap, (new_dist, counter, neighbor))
                mark(grid, neighbor, FRONTIER)

        mark(grid, current, EXPLORED)
        yield

    result["found"] = False


def a_star(grid, start, end, result):
    """A* Search: like Dijkstra, but guided by a heuristic.
    f(n) = g(n) + h(n)
        g(n) = real cost from Start to n
        h(n) = Manhattan distance from n to End (the 'guess')
    It explores far fewer nodes than Dijkstra while still finding the
    shortest path."""
    counter = 0
    heap = [(heuristic(start, end), counter, start)]
    g_score = {start: 0}
    came_from = {}
    done = set()

    while heap:
        _, _, current = heapq.heappop(heap)
        if current in done:
            continue
        done.add(current)
        result["explored"] += 1

        if current == end:
            result["found"], result["came_from"] = True, came_from
            return

        for neighbor in get_neighbors(grid, current):
            new_g = g_score[current] + 1
            if new_g < g_score.get(neighbor, float("inf")):
                g_score[neighbor] = new_g
                came_from[neighbor] = current
                f_score = new_g + heuristic(neighbor, end)
                counter += 1
                heapq.heappush(heap, (f_score, counter, neighbor))
                mark(grid, neighbor, FRONTIER)

        mark(grid, current, EXPLORED)
        yield

    result["found"] = False


# Name shown on screen + the function that runs it
ALGORITHMS = [
    ("BFS", bfs),
    ("DFS", dfs),
    ("Dijkstra", dijkstra),
    ("A* Search", a_star),
]


# ----------------------------------------------------------------------
# 4. THE VISUALIZER (window, input, drawing)
# ----------------------------------------------------------------------
class Visualizer:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("AI Pathfinding & Maze Visualizer")
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        self.clock = pygame.time.Clock()

        self.font = pygame.font.SysFont("arial", 16)
        self.font_small = pygame.font.SysFont("arial", 14)
        self.font_title = pygame.font.SysFont("arial", 22, bold=True)

        self.algorithm_index = 0
        self.speed_index = DEFAULT_SPEED_INDEX
        self.clear_all()

    # ---------------- state management ----------------
    def clear_all(self):
        """Reset everything: grid, start, end, stats."""
        self.grid = [[EMPTY] * COLS for _ in range(ROWS)]
        self.start = None
        self.end = None
        self.clear_search()
        self.message = "Left-click to place Start."

    def clear_search(self):
        """Remove explored/frontier/path colors but keep walls, start, end."""
        for r in range(ROWS):
            for c in range(COLS):
                if self.grid[r][c] in (FRONTIER, EXPLORED, PATH):
                    self.grid[r][c] = EMPTY
        self.mode = "idle"          # idle -> searching -> drawing_path -> done
        self.generator = None
        self.result = None
        self.path = []
        self.path_index = 0
        self.drag_tool = None
        self.stats = {"explored": 0, "path_length": None, "time_ms": 0.0}
        if self.start and self.end:
            self.message = "Press SPACE to run."

    def random_maze(self):
        """Fill the grid with random walls (Start/End are kept)."""
        self.clear_search()
        for r in range(ROWS):
            for c in range(COLS):
                if (r, c) in (self.start, self.end):
                    continue
                self.grid[r][c] = WALL if random.random() < WALL_DENSITY else EMPTY
        self.message = "Random maze created."

    def run_search(self):
        """Start the selected algorithm."""
        if self.mode in ("searching", "drawing_path"):
            return
        if not (self.start and self.end):
            self.message = "Place a Start and an End first!"
            return
        self.clear_search()
        name, function = ALGORITHMS[self.algorithm_index]
        self.result = {"found": False, "came_from": {}, "explored": 0}
        self.generator = function(self.grid, self.start, self.end, self.result)
        self.mode = "searching"
        self.message = f"Running {name}..."

    # ---------------- animation update ----------------
    def update(self):
        if self.mode == "searching":
            for _ in range(SPEEDS[self.speed_index]):
                # We time only the algorithm's work (not the drawing).
                t0 = time.perf_counter()
                try:
                    next(self.generator)
                    finished = False
                except StopIteration:
                    finished = True
                self.stats["time_ms"] += (time.perf_counter() - t0) * 1000
                self.stats["explored"] = self.result["explored"]
                if finished:
                    self.finish_search()
                    break

        elif self.mode == "drawing_path":
            for _ in range(2):      # draw 2 path cells per frame
                if self.path_index < len(self.path):
                    mark(self.grid, self.path[self.path_index], PATH)
                    self.path_index += 1
                else:
                    self.mode = "done"
                    self.message = "Done! Press C or X to reset."
                    break

    def finish_search(self):
        """Called when the algorithm has stopped."""
        if self.result["found"]:
            self.path = reconstruct_path(self.result["came_from"], self.start, self.end)
            self.stats["path_length"] = len(self.path) - 1   # number of steps
            self.path_index = 0
            self.mode = "drawing_path"
            self.message = "Path found! Drawing it..."
        else:
            self.mode = "done"
            self.message = "No path exists!"

    # ---------------- input handling ----------------
    def cell_at(self, pos):
        """Convert a mouse position into a (row, col) cell, or None."""
        x, y = pos
        if 0 <= x < GRID_W and 0 <= y < GRID_H:
            return (y // CELL, x // CELL)
        return None

    def is_busy(self):
        return self.mode in ("searching", "drawing_path")

    def mouse_down(self, button, pos):
        if self.is_busy():
            return
        cell = self.cell_at(pos)
        if cell is None:
            return
        if self.mode == "done":
            self.clear_search()
        row, col = cell

        if button == 1:                         # LEFT click: place things
            if self.start is None and cell != self.end:
                self.start = cell
                self.grid[row][col] = START
                self.message = "Now place the End."
            elif self.end is None and cell != self.start:
                self.end = cell
                self.grid[row][col] = END
                self.message = "Draw walls, then press SPACE."
            elif cell not in (self.start, self.end):
                self.grid[row][col] = WALL
                self.drag_tool = "wall"
        elif button == 3:                       # RIGHT click: erase
            self.erase(cell)
            self.drag_tool = "erase"

    def mouse_drag(self, pos):
        if self.is_busy() or self.drag_tool is None:
            return
        cell = self.cell_at(pos)
        if cell is None:
            return
        if self.drag_tool == "wall" and cell not in (self.start, self.end):
            self.grid[cell[0]][cell[1]] = WALL
        elif self.drag_tool == "erase":
            self.erase(cell)

    def erase(self, cell):
        row, col = cell
        if cell == self.start:
            self.start = None
        elif cell == self.end:
            self.end = None
        self.grid[row][col] = EMPTY

    def key_down(self, key):
        if key == pygame.K_ESCAPE:
            self.quit()
        elif key in (pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4):
            self.algorithm_index = key - pygame.K_1
            self.clear_search()
            self.message = f"Selected {ALGORITHMS[self.algorithm_index][0]}."
        elif key in (pygame.K_SPACE, pygame.K_RETURN):
            self.run_search()
        elif key == pygame.K_c:
            self.clear_all()
        elif key == pygame.K_x:
            self.clear_search()
        elif key == pygame.K_r:
            self.random_maze()
        elif key == pygame.K_UP:
            self.speed_index = min(self.speed_index + 1, len(SPEEDS) - 1)
        elif key == pygame.K_DOWN:
            self.speed_index = max(self.speed_index - 1, 0)

    @staticmethod
    def quit():
        pygame.quit()
        sys.exit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.quit()
            elif event.type == pygame.KEYDOWN:
                self.key_down(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down(event.button, event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                self.drag_tool = None
            elif event.type == pygame.MOUSEMOTION:
                self.mouse_drag(event.pos)

    # ---------------- drawing ----------------
    def draw_grid(self):
        for r in range(ROWS):
            for c in range(COLS):
                rect = (c * CELL, r * CELL, CELL, CELL)
                pygame.draw.rect(self.screen, COLORS[self.grid[r][c]], rect)
        for i in range(ROWS + 1):
            pygame.draw.line(self.screen, GRID_LINE, (0, i * CELL), (GRID_W, i * CELL))
        for i in range(COLS + 1):
            pygame.draw.line(self.screen, GRID_LINE, (i * CELL, 0), (i * CELL, GRID_H))

    def text(self, string, x, y, font=None, color=TEXT):
        surface = (font or self.font).render(string, True, color)
        self.screen.blit(surface, (x, y))

    def draw_panel(self):
        x0 = GRID_W + 15
        pygame.draw.rect(self.screen, PANEL_BG, (GRID_W, 0, PANEL_W, WIN_H))
        pygame.draw.line(self.screen, GRID_LINE, (GRID_W, 0), (GRID_W, WIN_H), 2)

        self.text("AI Pathfinder", x0, 12, self.font_title, ACCENT)

        # Algorithm list (selected one is highlighted)
        self.text("Algorithm", x0, 48, self.font_small, (120, 120, 130))
        for i, (name, _) in enumerate(ALGORITHMS):
            y = 68 + i * 26
            if i == self.algorithm_index:
                pygame.draw.rect(self.screen, ACCENT, (x0 - 5, y - 2, PANEL_W - 30, 24), border_radius=5)
                self.text(f"{i + 1}  {name}", x0, y, color=(255, 255, 255))
            else:
                self.text(f"{i + 1}  {name}", x0, y)

        # Stats
        self.text("Stats", x0, 182, self.font_small, (120, 120, 130))
        length = self.stats["path_length"]
        self.text(f"Nodes explored: {self.stats['explored']}", x0, 202)
        self.text(f"Path length: {length if length is not None else '-'}", x0, 224)
        self.text(f"Time: {self.stats['time_ms']:.3f} ms", x0, 246)
        self.text(f"Speed: {SPEEDS[self.speed_index]} steps/frame", x0, 268)

        # Status message
        self.text(self.message, x0, 298, self.font_small, (192, 57, 43))

        # Legend (2 columns)
        legend = [("Start", START), ("End", END), ("Wall", WALL),
                  ("Frontier", FRONTIER), ("Explored", EXPLORED), ("Path", PATH)]
        for i, (name, state) in enumerate(legend):
            lx = x0 + (i % 2) * 140
            ly = 330 + (i // 2) * 22
            pygame.draw.rect(self.screen, COLORS[state], (lx, ly, 14, 14))
            pygame.draw.rect(self.screen, GRID_LINE, (lx, ly, 14, 14), 1)
            self.text(name, lx + 22, ly - 2, self.font_small)

        # Controls
        self.text("Controls", x0, 408, self.font_small, (120, 120, 130))
        controls = [
            ("Left click", "Start > End > Walls"),
            ("Right click", "Erase"),
            ("SPACE", "Run algorithm"),
            ("1 - 4", "Choose algorithm"),
            ("R", "Random maze"),
            ("X", "Clear path only"),
            ("C", "Clear everything"),
            ("Up / Down", "Change speed"),
            ("ESC", "Quit"),
        ]
        for i, (key, action) in enumerate(controls):
            self.text(key, x0, 428 + i * 18, self.font_small, ACCENT)
            self.text(action, x0 + 90, 428 + i * 18, self.font_small)

    def draw(self):
        self.draw_grid()
        self.draw_panel()
        pygame.display.flip()

    # ---------------- main loop ----------------
    def run(self):
        while True:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)


def main():
    Visualizer().run()


if __name__ == "__main__":
    main()
