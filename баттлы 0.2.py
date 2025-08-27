import pygame
import random
import sys
import numpy as np
from collections import deque # Импортируем deque

# Инициализация Pygame
pygame.init()

# Цвета
BACKGROUND = (20, 20, 35)
GRID_COLOR = (40, 40, 60)
# PLAYER_COLORS определены в классе Game
HIGHLIGHT = (255, 255, 0, 180)
TEXT_COLOR = (230, 230, 230)
UI_BG = (30, 30, 45)
UI_BORDER = (70, 130, 180)
SELECTED_COLOR = (100, 200, 255)
WARNING_COLOR = (255, 100, 100)
WIN_COLOR = (255, 215, 0)

# Настройки окна
WIDTH, HEIGHT = 1200, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Прямоугольные битвы")
font = pygame.font.SysFont('Arial', 24)
title_font = pygame.font.SysFont('Arial', 40, bold=True)

class Game:
    def __init__(self):
        self.state = "menu"
        self.board_size = 0
        self.cell_size = 0
        self.board = None
        self.players = []
        self.current_player = 0
        self.dice_result = (0, 0)
        self.current_rect = None
        self.game_mode = ""
        self.offset_x = 0
        self.offset_y = 0
        self.rotation = 0
        self.placed_rects = {0: [], 1: []}
        self.valid_positions = set()
        self.selected_size = 50
        self.selected_mode = ""
        self.first_move = {0: True, 1: True}
        self.skip_turn_available = False
        self.game_over = False
        self.winner = None
        self.player_scores = [0, 0]
        self.frontier_lines = []  # Для хранения линий передового контура
        self.premature_endgame = False
        self.blocked_cells = set()  # Клетки, заблокированные передовым контуром
        self.piece_queue = []  # Очередь из 3 следующих фигур
        self.max_queue_size = 3
        self.num_players = 2  # 2, 3 или 4
        self.player_colors = [
            (0, 255, 170),    # Зеленый
            (255, 100, 100),  # Красный
            (100, 150, 255),  # Синий
            (255, 200, 100)   # Желтый
        ]

    def start_game(self):
        self.cell_size = min((HEIGHT - 100) // self.board_size, 16)  # Уменьшаем размер для вмещения
        self.board = np.zeros((self.board_size, self.board_size), dtype=int)
        
        # Создаем нужное количество игроков
        self.players = [Player(i) for i in range(self.num_players)]
        self.current_player = 0
        self.dice_result = (0, 0)
        self.current_rect = None
        self.offset_x = 0
        self.offset_y = 0
        self.rotation = 0
        self.placed_rects = {i: [] for i in range(self.num_players)}
        self.valid_positions = set()
        self.state = "playing"
        self.first_move = {i: True for i in range(self.num_players)}
        self.skip_turn_available = False
        self.game_over = False
        self.winner = None
        self.player_scores = [0] * self.num_players
        self.piece_queue = []
        self.premature_endgame = False
        self.blocked_cells = set()
        self.frontier_lines = []
        self.generate_piece_queue()
        self.roll_dice()

    def generate_piece_queue(self):
        """Генерирует очередь из 3 следующих фигур"""
        while len(self.piece_queue) < self.max_queue_size:
            dice_result = (random.randint(1, 6), random.randint(1, 6))
            self.piece_queue.append(dice_result)

    def roll_dice(self):
        # Берем первую фигуру из очереди
        if self.piece_queue:
            self.dice_result = self.piece_queue.pop(0)
        else:
            self.dice_result = (random.randint(1, 6), random.randint(1, 6))
            
        self.create_current_rect()
        self.update_valid_positions()
        
        # Добавляем новую фигуру в очередь
        self.generate_piece_queue()
        
        # Если нет доступных ходов, предлагаем пропустить ход
        if not self.valid_positions:
            self.skip_turn_available = True

    def create_current_rect(self):
        w, h = self.dice_result
        if self.rotation == 1:
            w, h = h, w
        self.current_rect = pygame.Rect(0, 0, w, h)

    def update_valid_positions(self):
        self.valid_positions.clear()
        
        # Для первого хода - углы для каждого игрока
        if self.first_move[self.current_player]:
            corner_positions = {
                0: (0, 0),                                    # Левый верхний
                1: (self.board_size - self.current_rect.width, 
                    self.board_size - self.current_rect.height),  # Правый нижний
            }
            
            # Для 3-4 игроков добавляем еще углы
            if self.num_players >= 3:
                corner_positions[2] = (self.board_size - self.current_rect.width, 0)  # Правый верхний
            if self.num_players >= 4:
                corner_positions[3] = (0, self.board_size - self.current_rect.height)  # Левый нижний
                
            self.valid_positions = {corner_positions.get(self.current_player, (0, 0))}
            return

        for y in range(self.board_size - self.current_rect.height + 1):
            for x in range(self.board_size - self.current_rect.width + 1):
                if self.can_place(x, y):
                    self.valid_positions.add((x, y))

    def can_place(self, x, y):
        # Проверка выхода за границы
        if x < 0 or y < 0 or x + self.current_rect.width > self.board_size or y + self.current_rect.height > self.board_size:
            return False
        
        # Проверка пересечения с другими фигурами
        for i in range(y, y + self.current_rect.height):
            for j in range(x, x + self.current_rect.width):
                if self.board[i][j] != 0:
                    return False
        
        # Для первого хода каждого игрока разрешаем ставить без примыкания
        if self.first_move[self.current_player]:
            return True
        
        # Новая механика: как минимум одна сторона должна полностью перекрываться с уже стоящими фигурами
        has_overlapping_side = False
        
        # Проверка левой границы - должна перекрываться полностью
        if x > 0:
            full_overlap = True
            for i in range(y, y + self.current_rect.height):
                if self.board[i][x-1] != self.current_player + 1:
                    full_overlap = False
                    break
            if full_overlap:
                has_overlapping_side = True
        
        # Проверка правой границы - должна перекрываться полностью
        if x + self.current_rect.width < self.board_size:
            full_overlap = True
            for i in range(y, y + self.current_rect.height):
                if self.board[i][x + self.current_rect.width] != self.current_player + 1:
                    full_overlap = False
                    break
            if full_overlap:
                has_overlapping_side = True
        
        # Проверка верхней границы - должна перекрываться полностью
        if y > 0:
            full_overlap = True
            for j in range(x, x + self.current_rect.width):
                if self.board[y-1][j] != self.current_player + 1:
                    full_overlap = False
                    break
            if full_overlap:
                has_overlapping_side = True
        
        # Проверка нижней границы - должна перекрываться полностью
        if y + self.current_rect.height < self.board_size:
            full_overlap = True
            for j in range(x, x + self.current_rect.width):
                if self.board[y + self.current_rect.height][j] != self.current_player + 1:
                    full_overlap = False
                    break
            if full_overlap:
                has_overlapping_side = True
        
        return has_overlapping_side

    def place_rect(self, x, y):
        if (x, y) not in self.valid_positions:
            return False
        
        # Занимаем клетки
        for i in range(y, y + self.current_rect.height):
            for j in range(x, x + self.current_rect.width):
                self.board[i][j] = self.current_player + 1
        
        # Сохраняем прямоугольник
        rect_data = (x, y, self.current_rect.width, self.current_rect.height)
        self.placed_rects[self.current_player].append(rect_data)
        
        # Сбрасываем флаг первого хода после размещения
        if self.first_move[self.current_player]:
            self.first_move[self.current_player] = False
        
        # Переход хода к следующему игроку
        self.current_player = (self.current_player + 1) % self.num_players
        self.rotation = 0
        self.skip_turn_available = False
        self.roll_dice()
        
        return True

    def skip_turn(self):
        """Пропустить ход"""
        self.current_player = (self.current_player + 1) % self.num_players
        self.rotation = 0
        self.skip_turn_available = False
        self.roll_dice()
        
        # Проверяем, может ли следующий игрок сделать ход
        if not self.valid_positions:
            self.skip_turn_available = True

    def check_premature_endgame(self):
        """Проверяет, есть ли преждевременный эндгейм"""
        # Для каждого игрока проверяем, соединяет ли он две противоположные стороны
        # Пока работает только для 2 игроков
        if self.num_players == 2:
            for player_id in [1, 2]:
                if self.connects_opposite_sides(player_id):
                    return True
        return False

    def connects_opposite_sides(self, player_id):
        """Проверяет, соединяет ли игрок две противоположные стороны поля"""
        # Создаем карту занятых клеток для игрока
        player_map = np.zeros((self.board_size, self.board_size), dtype=bool)
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.board[i][j] == player_id:
                    player_map[i][j] = True
        
        # Проверяем соединение противоположных сторон
        # Верх-низ
        if self.connects_sides(player_map, 'top', 'bottom'):
            self.find_frontier_lines(player_id, 'horizontal')
            return True
        
        # Лево-право
        if self.connects_sides(player_map, 'left', 'right'):
            self.find_frontier_lines(player_id, 'vertical')
            return True
            
        return False

    def connects_sides(self, player_map, side1, side2):
        """Проверяет, соединены ли две стороны через фигуры игрока"""
        visited = np.zeros((self.board_size, self.board_size), dtype=bool)
        queue = deque()
        
        # Добавляем начальные точки
        if side1 == 'top':
            for j in range(self.board_size):
                if player_map[0][j] and not visited[0][j]:
                    queue.append((0, j))
                    visited[0][j] = True
        elif side1 == 'left':
            for i in range(self.board_size):
                if player_map[i][0] and not visited[i][0]:
                    queue.append((i, 0))
                    visited[i][0] = True
        
        # BFS для поиска пути
        while queue:
            x, y = queue.popleft()
            
            # Проверяем, достигли ли мы целевой стороны
            if side2 == 'bottom' and x == self.board_size - 1:
                return True
            elif side2 == 'right' and y == self.board_size - 1:
                return True
            
            # Проверяем соседей
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.board_size and 0 <= ny < self.board_size and 
                    player_map[nx][ny] and not visited[nx][ny]):
                    visited[nx][ny] = True
                    queue.append((nx, ny))
        
        return False

    def find_frontier_lines(self, player_id, orientation):
        """Находит линии передового контура"""
        self.frontier_lines = []
        
        if orientation == 'horizontal':
            # Ищем горизонтальные линии контура
            for i in range(self.board_size):
                for j in range(self.board_size):
                    if self.board[i][j] == player_id:
                        # Проверяем верхнюю границу
                        if i == 0 or self.board[i-1][j] != player_id:
                            self.frontier_lines.append(((j, i), (j+1, i)))
                        # Проверяем нижнюю границу
                        if i == self.board_size - 1 or self.board[i+1][j] != player_id:
                            self.frontier_lines.append(((j, i+1), (j+1, i+1)))
                        # Проверяем левую границу
                        if j == 0 or self.board[i][j-1] != player_id:
                            self.frontier_lines.append(((j, i), (j, i+1)))
                        # Проверяем правую границу
                        if j == self.board_size - 1 or self.board[i][j+1] != player_id:
                            self.frontier_lines.append(((j+1, i), (j+1, i+1)))
        
        elif orientation == 'vertical':
            # Ищем вертикальные линии контура
            for i in range(self.board_size):
                for j in range(self.board_size):
                    if self.board[i][j] == player_id:
                        # Проверяем границы аналогично
                        if i == 0 or self.board[i-1][j] != player_id:
                            self.frontier_lines.append(((j, i), (j+1, i)))
                        if i == self.board_size - 1 or self.board[i+1][j] != player_id:
                            self.frontier_lines.append(((j, i+1), (j+1, i+1)))
                        if j == 0 or self.board[i][j-1] != player_id:
                            self.frontier_lines.append(((j, i), (j, i+1)))
                        if j == self.board_size - 1 or self.board[i][j+1] != player_id:
                            self.frontier_lines.append(((j+1, i), (j+1, i+1)))

    def find_blocked_cells(self, blocking_player):
        """Находит клетки, доступ к которым заблокирован"""
        self.blocked_cells = set()
        opponent_id = 3 - blocking_player  # 1->2, 2->1
        
        # Создаем карту доступных клеток для противника с помощью BFS
        accessible = np.zeros((self.board_size, self.board_size), dtype=bool)
        visited = np.zeros((self.board_size, self.board_size), dtype=bool)
        queue = deque()
        
        # Начальные точки - края поля, не занятые блокирующим игроком
        # Верхний край
        for j in range(self.board_size):
            if self.board[0][j] != blocking_player:
                queue.append((0, j))
                if self.board[0][j] == 0:
                    accessible[0][j] = True
        
        # Левый край
        for i in range(self.board_size):
            if self.board[i][0] != blocking_player:
                queue.append((i, 0))
                if self.board[i][0] == 0:
                    accessible[i][0] = True
        
        # BFS для поиска доступных клеток
        while queue:
            x, y = queue.popleft()
            if visited[x][y]:
                continue
            visited[x][y] = True
            
            # Проверяем соседей
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nx, ny = x + dx, y + dy
                if (0 <= nx < self.board_size and 0 <= ny < self.board_size and 
                    not visited[nx][ny] and self.board[nx][ny] != blocking_player):
                    if self.board[nx][ny] == 0:
                        accessible[nx][ny] = True
                    queue.append((nx, ny))
        
        # Все незанятые клетки, которые не доступны, считаются заблокированными
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.board[i][j] == 0 and not accessible[i][j]:
                    self.blocked_cells.add((i, j))

    def handle_premature_endgame(self):
        """Обрабатывает преждевременный эндгейм"""
        self.premature_endgame = True
        
        # Определяем, какой игрок вызвал эндгейм
        blocking_player = self.current_player + 1
        
        # Находим заблокированные клетки
        self.find_blocked_cells(blocking_player)
        
        # Присваиваем заблокированные клетки блокирующему игроку
        for i, j in self.blocked_cells:
            self.board[i][j] = blocking_player
        
        # Завершаем игру
        self.end_game()

    def end_game(self):
        """Завершение игры и подсчет очков"""
        self.game_over = True
        
        # Подсчет очков: занятые клетки
        for i in range(self.num_players):
            self.player_scores[i] = np.sum(self.board == i + 1)
        
        # Определение победителя
        max_score = max(self.player_scores)
        winners = [i for i, score in enumerate(self.player_scores) if score == max_score]
        
        if len(winners) == 1:
            self.winner = winners[0]
        else:
            self.winner = None  # Ничья

    def bot_move(self):
        if not self.valid_positions:
            # Если нет валидных позиций, пропускаем ход
            self.skip_turn()
            return False
        
        # Улучшенная стратегия бота
        best_pos = None
        best_score = -1
        
        # Оцениваем каждую возможную позицию
        for pos in self.valid_positions:
            x, y = pos
            score = self.evaluate_position(x, y)
            if score > best_score:
                best_score = score
                best_pos = pos
        
        if best_pos:
            x, y = best_pos
            self.offset_x = x
            self.offset_y = y
            self.place_rect(x, y)
            return True
        else:
            # Если не нашли хорошую позицию, ставим в случайное место
            x, y = random.choice(list(self.valid_positions))
            self.offset_x = x
            self.offset_y = y
            self.place_rect(x, y)
            return True

    def evaluate_position(self, x, y):
        """Оценивает качество позиции для бота"""
        score = 0
        
        # Бонус за близость к противнику
        distance_to_opponent = self.get_distance_to_opponent(x, y)
        score += max(0, 100 - distance_to_opponent * 2)
        
        # Бонус за контроль центра
        center_x, center_y = self.board_size // 2, self.board_size // 2
        distance_to_center = abs(x - center_x) + abs(y - center_y)
        score += max(0, 50 - distance_to_center)
        
        # Бонус за размер фигуры (чем больше, тем лучше)
        area = self.current_rect.width * self.current_rect.height
        score += area * 3
        
        # Штраф за слишком близкое расположение к краям
        if x < 2 or y < 2 or x + self.current_rect.width > self.board_size - 2 or y + self.current_rect.height > self.board_size - 2:
            score -= 20
        
        return score

    def get_distance_to_opponent(self, x, y):
        """Вычисляет минимальное расстояние до фигур противника"""
        # Для многопользовательской игры нужно учитывать всех противников
        # Пока используем логику для 2 игроков
        opponent_id = 2 if self.current_player == 0 else 1
        min_dist = float('inf')
        
        # Проверяем расстояние до всех клеток противника
        for i in range(self.board_size):
            for j in range(self.board_size):
                if self.board[i][j] == opponent_id:
                    dist = abs(x - j) + abs(y - i)  # Манхэттенское расстояние
                    min_dist = min(min_dist, dist)
        
        return min_dist if min_dist != float('inf') else 0

    def draw(self, screen):
        screen.fill(BACKGROUND)
        
        if self.state == "menu":
            self.draw_menu(screen)
        elif self.state == "playing":
            self.draw_board(screen)
            self.draw_ui(screen)

    def draw_menu(self, screen):
        title = title_font.render("ПРЯМОУГОЛЬНЫЕ БИТВЫ", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        # Кнопки выбора размера (3 кнопки)
        sizes = [("Малый (50x50)", 50), ("Средний (100x100)", 100), ("Большой (150x150)", 150)]
        for i, (text, size) in enumerate(sizes):
            rect = pygame.Rect(WIDTH//2 - 150, 130 + i*70, 300, 60)
            color = SELECTED_COLOR if size == self.selected_size else UI_BORDER
            pygame.draw.rect(screen, UI_BG, rect, border_radius=12)
            pygame.draw.rect(screen, color, rect, 2, border_radius=12)
            text_surf = font.render(text, True, TEXT_COLOR)
            screen.blit(text_surf, (rect.centerx - text_surf.get_width()//2, rect.centery - text_surf.get_height()//2))
        
        # Кнопки выбора режима
        modes = [("Игрок vs Игрок", "pvp"), ("Игрок vs Компьютер", "pvc")]
        for i, (text, mode) in enumerate(modes):
            rect = pygame.Rect(WIDTH//2 - 150, 360 + i*70, 300, 60)
            color = SELECTED_COLOR if mode == self.selected_mode else UI_BORDER
            pygame.draw.rect(screen, UI_BG, rect, border_radius=12)
            pygame.draw.rect(screen, color, rect, 2, border_radius=12)
            text_surf = font.render(text, True, TEXT_COLOR)
            screen.blit(text_surf, (rect.centerx - text_surf.get_width()//2, rect.centery - text_surf.get_height()//2))
        
        # Кнопки выбора количества игроков (только для PvP) - в одну строку
        if self.selected_mode == "pvp":
            player_counts = [("2", 2), ("3", 3), ("4", 4)]
            for i, (text, count) in enumerate(player_counts):
                # Располагаем в одну строку по центру
                rect = pygame.Rect(WIDTH//2 - 150 + i*100, 520, 80, 60)
                color = SELECTED_COLOR if count == self.num_players else UI_BORDER
                pygame.draw.rect(screen, UI_BG, rect, border_radius=12)
                pygame.draw.rect(screen, color, rect, 2, border_radius=12)
                text_surf = font.render(f"{text} игрока", True, TEXT_COLOR)
                screen.blit(text_surf, (rect.centerx - text_surf.get_width()//2, rect.centery - text_surf.get_height()//2))
            
            # Подпись к выбору игроков
            players_label = font.render("Количество игроков:", True, TEXT_COLOR)
            screen.blit(players_label, (WIDTH//2 - players_label.get_width()//2, 490))
        
        # Кнопка старта
        if self.selected_size and self.selected_mode:
            start_rect = pygame.Rect(WIDTH//2 - 100, 620, 200, 60)
            pygame.draw.rect(screen, (50, 150, 50), start_rect, border_radius=12)
            pygame.draw.rect(screen, (0, 200, 0), start_rect, 2, border_radius=12)
            start_text = font.render("Начать игру", True, TEXT_COLOR)
            screen.blit(start_text, (start_rect.centerx - start_text.get_width()//2, start_rect.centery - start_text.get_height()//2))

    def draw_board(self, screen):
        board_width = self.board_size * self.cell_size
        board_rect = pygame.Rect(50, 50, board_width, board_width)
        
        # Рисуем сетку
        for i in range(self.board_size + 1):
            pygame.draw.line(
                screen, GRID_COLOR,
                (50, 50 + i * self.cell_size),
                (50 + board_width, 50 + i * self.cell_size)
            )
            pygame.draw.line(
                screen, GRID_COLOR,
                (50 + i * self.cell_size, 50),
                (50 + i * self.cell_size, 50 + board_width)
            )
        
        # Рисуем заблокированные клетки (если есть)
        if self.premature_endgame:
            for i, j in self.blocked_cells:
                pygame.draw.rect(
                    screen, (*self.player_colors[self.current_player], 100),
                    (50 + j * self.cell_size, 50 + i * self.cell_size, self.cell_size, self.cell_size)
                )
        
        # Рисуем размещенные фигуры
        for player_idx in range(self.num_players): # Используем range(self.num_players)
            for rect_data in self.placed_rects[player_idx]:
                x, y, w, h = rect_data
                pygame.draw.rect(
                    screen, self.player_colors[player_idx], # Используем self.player_colors
                    (50 + x * self.cell_size, 50 + y * self.cell_size, w * self.cell_size, h * self.cell_size)
                )
                # Границы фигур
                pygame.draw.rect(
                    screen, (0, 0, 0),
                    (50 + x * self.cell_size, 50 + y * self.cell_size, w * self.cell_size, h * self.cell_size),
                    1
                )
        
        # Рисуем текущий прямоугольник
        if self.current_rect and not self.game_over:
            x, y = self.offset_x, self.offset_y
            # Используем полупрозрачный цвет для текущего игрока
            color = self.player_colors[self.current_player] # Используем self.player_colors
            rect_surf = pygame.Surface((self.current_rect.width * self.cell_size, self.current_rect.height * self.cell_size), pygame.SRCALPHA)
            rect_surf.fill((*color, 100))  # Полупрозрачный цвет
            pygame.draw.rect(rect_surf, HIGHLIGHT[:3], (0, 0, self.current_rect.width * self.cell_size, self.current_rect.height * self.cell_size), 2)
            screen.blit(rect_surf, (50 + x * self.cell_size, 50 + y * self.cell_size))
            
            # Центр фигуры
            center_x = 50 + (x + self.current_rect.width/2) * self.cell_size
            center_y = 50 + (y + self.current_rect.height/2) * self.cell_size
            pygame.draw.circle(screen, (255, 255, 255), (int(center_x), int(center_y)), 4)
        
        # Подсветка валидных позиций
        if not self.game_over:
            for pos in self.valid_positions:
                x, y = pos
                pygame.draw.rect(
                    screen, HIGHLIGHT,
                    (50 + x * self.cell_size, 50 + y * self.cell_size, 
                     self.current_rect.width * self.cell_size, self.current_rect.height * self.cell_size),
                    2
                )
        
        # Рисуем передовой контур (если есть)
        if self.premature_endgame and self.frontier_lines:
            for start, end in self.frontier_lines:
                start_x = 50 + start[0] * self.cell_size
                start_y = 50 + start[1] * self.cell_size
                end_x = 50 + end[0] * self.cell_size
                end_y = 50 + end[1] * self.cell_size
                pygame.draw.line(screen, WIN_COLOR, (start_x, start_y), (end_x, end_y), 3)
        
        # Экран окончания игры
        if self.game_over:
            overlay = pygame.Surface((board_width, board_width), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            screen.blit(overlay, (50, 50))
            
            if self.winner is not None:
                win_text = title_font.render(f"Победил Игрок {self.winner + 1}!", True, WIN_COLOR)
                reason_text = font.render("Преждевременный эндгейм" if self.premature_endgame else "Конец игры", True, TEXT_COLOR)
            else:
                win_text = title_font.render("Ничья!", True, WIN_COLOR)
                reason_text = font.render("", True, TEXT_COLOR)
            
            screen.blit(win_text, (WIDTH//2 - win_text.get_width()//2, HEIGHT//2 - 70))
            if self.premature_endgame:
                screen.blit(reason_text, (WIDTH//2 - reason_text.get_width()//2, HEIGHT//2 - 20))
            
            # Отображение счета для всех игроков
            score_y = HEIGHT//2 + 20
            for i in range(self.num_players):
                score_text = font.render(f"Игрок {i+1}: {self.player_scores[i]} клеток", True, self.player_colors[i])
                screen.blit(score_text, (WIDTH//2 - score_text.get_width()//2, score_y))
                score_y += 30
            
            restart_text = font.render("Нажмите ESC для возврата в меню", True, TEXT_COLOR)
            screen.blit(restart_text, (WIDTH//2 - restart_text.get_width()//2, score_y + 20))

    def draw_ui(self, screen):
        board_width = self.board_size * self.cell_size
        
        # Панель информации (уменьшена высота)
        info_rect = pygame.Rect(60 + board_width, 50, WIDTH - board_width - 70, 350)
        pygame.draw.rect(screen, UI_BG, info_rect, border_radius=12)
        pygame.draw.rect(screen, UI_BORDER, info_rect, 2, border_radius=12)
        
        # Информация о игроках
        for i in range(self.num_players):
            player_score = np.sum(self.board == i + 1)
            player_text = font.render(f"Игрок {i + 1}: {player_score} клеток", True, self.player_colors[i])
            screen.blit(player_text, (info_rect.x + 20, info_rect.y + 20 + i * 40))
        
        # Текущий игрок
        if not self.game_over:
            current_text = font.render(f"Сейчас ходит: Игрок {self.current_player + 1}", True, self.player_colors[self.current_player])
            screen.blit(current_text, (info_rect.x + 20, info_rect.y + 20 + self.num_players * 40))
            
            # Режим игры
            mode_text = font.render(f"Режим: {self.game_mode}", True, TEXT_COLOR)
            screen.blit(mode_text, (info_rect.x + 20, info_rect.y + 50 + self.num_players * 40))
            
            # Результаты кубиков
            dice_text = font.render(f"Кубики: {self.dice_result[0]} и {self.dice_result[1]}", True, TEXT_COLOR)
            screen.blit(dice_text, (info_rect.x + 20, info_rect.y + 80 + self.num_players * 40))
            
            # Размер прямоугольника
            rect_text = font.render(f"Фигура: {self.current_rect.width} x {self.current_rect.height}", True, TEXT_COLOR)
            screen.blit(rect_text, (info_rect.x + 20, info_rect.y + 110 + self.num_players * 40))
            
            # Предложение пропустить ход
            if self.skip_turn_available:
                skip_text = font.render("Нет ходов! SPACE чтобы пропустить", True, WARNING_COLOR)
                screen.blit(skip_text, (info_rect.x + 20, info_rect.y + 140 + self.num_players * 40))
            
            # Кнопка вращения
            rotate_rect = pygame.Rect(info_rect.x + 20, info_rect.y + 170 + self.num_players * 40, info_rect.width - 40, 40)
            pygame.draw.rect(screen, UI_BG, rotate_rect, border_radius=8)
            pygame.draw.rect(screen, UI_BORDER, rotate_rect, 2, border_radius=8)
            rotate_text = font.render("Повернуть (R или колесо мыши)", True, TEXT_COLOR)
            screen.blit(rotate_text, (rotate_rect.centerx - rotate_text.get_width()//2, rotate_rect.centery - rotate_text.get_height()//2))
        
        # Очередь фигур
        queue_rect = pygame.Rect(60 + board_width, 420, WIDTH - board_width - 70, 180)
        pygame.draw.rect(screen, UI_BG, queue_rect, border_radius=12)
        pygame.draw.rect(screen, UI_BORDER, queue_rect, 2, border_radius=12)
        
        queue_title = font.render("Следующие фигуры:", True, TEXT_COLOR)
        screen.blit(queue_title, (queue_rect.x + 20, queue_rect.y + 10))
        
        # Отображаем следующие фигуры
        for i, (w, h) in enumerate(self.piece_queue[:3]):  # Показываем только 3 фигуры
            preview_x = queue_rect.x + 20 + i * 80
            preview_y = queue_rect.y + 50
            
            # Рисуем мини-прямоугольник
            pygame.draw.rect(
                screen, self.player_colors[(self.current_player + i + 1) % self.num_players],
                (preview_x, preview_y, w * 8, h * 8)
            )
            pygame.draw.rect(
                screen, (255, 255, 255),
                (preview_x, preview_y, w * 8, h * 8),
                1
            )
            
            # Подпись с размером
            size_text = font.render(f"{w}×{h}", True, TEXT_COLOR)
            screen.blit(size_text, (preview_x, preview_y + h * 8 + 5))

class Player:
    def __init__(self, player_id):
        self.id = player_id
        self.score = 0

def main():
    game = Game()
    clock = pygame.time.Clock()
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if game.state == "playing":
                    if game.game_over:
                        if event.key == pygame.K_ESCAPE:
                            game.state = "menu"
                    else:
                        # Управление в игре
                        if event.key == pygame.K_UP and game.offset_y > 0:
                            game.offset_y -= 1
                        elif event.key == pygame.K_DOWN and game.offset_y < game.board_size - game.current_rect.height:
                            game.offset_y += 1
                        elif event.key == pygame.K_LEFT and game.offset_x > 0:
                            game.offset_x -= 1
                        elif event.key == pygame.K_RIGHT and game.offset_x < game.board_size - game.current_rect.width:
                            game.offset_x += 1
                        elif event.key == pygame.K_r:
                            game.rotation = 1 - game.rotation
                            game.create_current_rect()
                            game.update_valid_positions()
                        elif event.key == pygame.K_SPACE:
                            if game.skip_turn_available:
                                game.skip_turn()
                            else:
                                game.roll_dice()
                        elif event.key == pygame.K_RETURN:
                            if game.place_rect(game.offset_x, game.offset_y):
                                # Ход компьютера в PvC режиме
                                if game.game_mode == "pvc" and game.current_player == 1 and not game.game_over:
                                    pygame.time.set_timer(pygame.USEREVENT, 500)
                        elif event.key == pygame.K_ESCAPE:
                            game.state = "menu"
            
            # Обработка мыши в меню
            if event.type == pygame.MOUSEBUTTONDOWN and game.state == "menu":
                # Обработка выбора размера
                sizes = [("Малый (50x50)", 50), ("Средний (100x100)", 100), ("Большой (150x150)", 150)]
                for i, (text, size) in enumerate(sizes):
                    rect = pygame.Rect(WIDTH//2 - 150, 130 + i*70, 300, 60) # Исправлены координаты
                    if rect.collidepoint(event.pos):
                        game.selected_size = size
                
                # Обработка выбора режима
                modes = [("Игрок vs Игрок", "pvp"), ("Игрок vs Компьютер", "pvc")]
                for i, (text, mode) in enumerate(modes):
                    rect = pygame.Rect(WIDTH//2 - 150, 360 + i*70, 300, 60) # Исправлены координаты
                    if rect.collidepoint(event.pos):
                        game.selected_mode = mode
                
                # Обработка выбора количества игроков (только для PvP)
                if game.selected_mode == "pvp":
                    player_counts = [("2", 2), ("3", 3), ("4", 4)]
                    for i, (text, count) in enumerate(player_counts):
                        rect = pygame.Rect(WIDTH//2 - 150 + i*100, 520, 80, 60) # Исправлены координаты
                        if rect.collidepoint(event.pos):
                            game.num_players = count
                
                # Кнопка старта
                if game.selected_size and game.selected_mode:
                    start_rect = pygame.Rect(WIDTH//2 - 100, 620, 200, 60) # Исправлены координаты
                    if start_rect.collidepoint(event.pos):
                        game.board_size = game.selected_size
                        game.game_mode = game.selected_mode
                        game.start_game()
            
            # Обработка мыши в игре
            if event.type == pygame.MOUSEBUTTONDOWN and game.state == "playing" and not game.game_over:
                if event.button == 1:  # Левая кнопка мыши
                    # Проверяем клик на поле
                    board_start_x, board_start_y = 50, 50
                    board_end_x = board_start_x + game.board_size * game.cell_size
                    board_end_y = board_start_y + game.board_size * game.cell_size
                    
                    if (board_start_x <= mouse_pos[0] < board_end_x and 
                        board_start_y <= mouse_pos[1] < board_end_y):
                        
                        # Вычисляем координаты клетки
                        rel_x = mouse_pos[0] - board_start_x
                        rel_y = mouse_pos[1] - board_start_y
                        
                        # Привязка к клетке
                        cell_x = int(rel_x // game.cell_size)
                        cell_y = int(rel_y // game.cell_size)
                        
                        # Устанавливаем фигуру
                        game.offset_x = max(0, min(cell_x, game.board_size - game.current_rect.width))
                        game.offset_y = max(0, min(cell_y, game.board_size - game.current_rect.height))
                        
                        # Пытаемся поставить фигуру
                        if game.place_rect(game.offset_x, game.offset_y):
                            # Ход компьютера в PvC режиме
                            if game.game_mode == "pvc" and game.current_player == 1 and not game.game_over:
                                pygame.time.set_timer(pygame.USEREVENT, 500)
                
                # Поворот колесом мыши
                elif event.button == 4:  # Колесо вверх
                    game.rotation = 1 - game.rotation
                    game.create_current_rect()
                    game.update_valid_positions()
                elif event.button == 5:  # Колесо вниз
                    game.rotation = 1 - game.rotation
                    game.create_current_rect()
                    game.update_valid_positions()
            
            # Перемещение фигуры мышью
            if event.type == pygame.MOUSEMOTION and game.state == "playing" and not game.game_over:
                board_start_x, board_start_y = 50, 50
                board_end_x = board_start_x + game.board_size * game.cell_size
                board_end_y = board_start_y + game.board_size * game.cell_size
                
                if (board_start_x <= mouse_pos[0] < board_end_x and 
                    board_start_y <= mouse_pos[1] < board_end_y):
                    
                    # Вычисляем координаты клетки под курсором
                    rel_x = mouse_pos[0] - board_start_x
                    rel_y = mouse_pos[1] - board_start_y
                    
                    # Привязка к клетке
                    cell_x = int(rel_x // game.cell_size)
                    cell_y = int(rel_y // game.cell_size)
                    
                    # Устанавливаем фигуру
                    game.offset_x = max(0, min(cell_x, game.board_size - game.current_rect.width))
                    game.offset_y = max(0, min(cell_y, game.board_size - game.current_rect.height))
            
            # Ход компьютера по таймеру
            if event.type == pygame.USEREVENT and game.state == "playing":
                if game.game_mode == "pvc" and game.current_player == 1 and not game.game_over:
                    game.bot_move()
                    pygame.time.set_timer(pygame.USEREVENT, 0)  # Отключаем таймер
        
        # Автоматический ход компьютера
        if (game.state == "playing" and game.game_mode == "pvc" and 
            game.current_player == 1 and not game.game_over and 
            not any(event.type == pygame.USEREVENT for event in pygame.event.get())):
            pygame.time.set_timer(pygame.USEREVENT, 500)
        
        # Отрисовка
        game.draw(screen)
        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()