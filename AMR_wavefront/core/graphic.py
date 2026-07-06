import pygame
import math
import numpy
from utils.utils import *


class Graphics(object):

    def __init__(self, screenSize):
        pygame.init()
        displayFlags = pygame.RESIZABLE
        self.fullScreen = pygame.display.set_mode(screenSize, displayFlags)
        pygame.display.set_caption("AMR in Pygame")

        # Chia màn hình: Trái (72%) = bản đồ + AMR, Phải (28%) = panel thông tin
        totalW, totalH = screenSize
        mapW = int(totalW * 0.72)
        self.screen     = self.fullScreen.subsurface(pygame.Rect(0, 0, mapW, totalH))
        self.infoScreen = self.fullScreen.subsurface(pygame.Rect(mapW, 0, totalW - mapW, totalH))

    def drawDottedLine(self, color, start_pos, end_pos, dot_length=5, space_length=15):
        """Vẽ đường nét đứt giữa hai điểm."""
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        distance = math.hypot(dx, dy)
        dx /= distance
        dy /= distance
        num_dots = int(distance // (dot_length + space_length))
        for i in range(num_dots + 1):
            start_x = start_pos[0] + (dot_length + space_length) * i * dx
            start_y = start_pos[1] + (dot_length + space_length) * i * dy
            end_x = start_x + dot_length * dx
            end_y = start_y + dot_length * dy
            pygame.draw.line(self.screen, color, (start_x, start_y), (end_x, end_y), 2)

    def drawMap(self, map, color=(107, 107, 105)):
        """Vẽ lưới bản đồ và các vật cản (chấm đỏ)."""
        for row in range(len(map)):
            pixelPos1 = turn2pixel(map, self.screen.get_height(), self.screen.get_width(), row, 0)
            pixelPos2 = turn2pixel(map, self.screen.get_height(), self.screen.get_width(), row, len(map[row]) - 1)
            pygame.draw.line(self.screen, color, pixelPos1, pixelPos2, 1)
        for col in range(len(map[0])):
            pixelPos1 = turn2pixel(map, self.screen.get_height(), self.screen.get_width(), 0, col)
            pixelPos2 = turn2pixel(map, self.screen.get_height(), self.screen.get_width(), len(map) - 1, col)
            pygame.draw.line(self.screen, color, pixelPos1, pixelPos2, 1)
        for row in range(len(map)):
            for col in range(len(map[row])):
                if map[row][col] != 0:
                    pixelPos = turn2pixel(map, self.screen.get_height(), self.screen.get_width(), row, col)
                    pygame.draw.circle(self.screen, (255, 0, 0), pixelPos, 6)

    def drawAxis(self, mapGrid, step=5, color=(30, 110, 220)):
        """Vẽ trục X (cột) và trục Y (hàng) để đối chiếu tọa độ lưới."""
        height = self.screen.get_height()
        width  = self.screen.get_width()
        rows = len(mapGrid)
        cols = len(mapGrid[0])

        try:
            font = pygame.font.SysFont('Arial', 13, bold=True)
        except Exception:
            font = pygame.font.Font(None, 15)

        pygame.draw.line(self.screen, color, (0, height - 1), (width, height - 1), 2)
        for col in range(0, cols, step):
            x_pixel, _ = turn2pixel(mapGrid, height, width, 0, col)
            lbl = font.render(str(col), True, color)
            self.screen.blit(lbl, (min(max(0, x_pixel - 6), width - 14), height - 18))
        self.screen.blit(font.render('X', True, color), (width - 16, height - 18))

        pygame.draw.line(self.screen, color, (0, 0), (0, height), 2)
        for row in range(0, rows, step):
            _, y_pixel = turn2pixel(mapGrid, height, width, row, 0)
            lbl = font.render(str(row), True, color)
            self.screen.blit(lbl, (4, min(max(0, y_pixel - 14), height - 14)))
        self.screen.blit(font.render('Y', True, color), (4, 2))

    def drawAmr(self, amr):
        """Vẽ AMR (hình chữ nhật + trục tọa độ + vết đường đi)."""
        points = numpy.array([[-amr.width/2, -amr.height/2],
                               [ amr.width/2, -amr.height/2],
                               [ amr.width/2,  amr.height/2],
                               [-amr.width/2,  amr.height/2]])
        if amr.heading == 90:
            angle = 270
        elif amr.heading == 270:
            angle = 90
        else:
            angle = amr.heading
        tMatrix = transformationMatrix2d(rotation_deg=angle, translation=amr.pos)
        tPoints = apply_transformation(points, tMatrix)
        pygame.draw.lines(self.screen, (200, 100, 50), True, tPoints, 3)

        axisPoints = numpy.array([[0, 0], [amr.width, 0], [0, 0], [0, amr.height]])
        aPoints = apply_transformation(axisPoints, tMatrix)
        pygame.draw.line(self.screen, (255, 0, 0), aPoints[0], aPoints[1], 2)  # trục X
        pygame.draw.line(self.screen, (0, 255, 0), aPoints[2], aPoints[3], 2)  # trục Y
        pygame.draw.circle(self.screen, amr.color, amr.pos, 3)

        if len(amr.path_points) > 1:
            for index in range(len(amr.path_points) - 1):
                self.drawDottedLine((245, 149, 5), amr.path_points[index], amr.path_points[index + 1])

    def drawGoal(self, mapGrid, row, col):
        """Vẽ vòng tròn đánh dấu vị trí đích trên bản đồ."""
        pixelPos = turn2pixel(mapGrid, self.screen.get_height(), self.screen.get_width(), row, col)
        pygame.draw.circle(self.screen, (0, 170, 0), pixelPos, 12, 3)
        pygame.draw.circle(self.screen, (0, 170, 0), pixelPos, 3)

    def drawStatusPanel(self, heading, currentRow, currentCol, remainingSteps, reachedGoal, actuator, startRow, startCol):
        """Vẽ panel tổng hợp thông tin trạng thái AMR (bên phải màn hình)."""
        panelW = self.infoScreen.get_width() - 20
        panelH = self.infoScreen.get_height() - 20
        panelRect = pygame.Rect(10, 10, panelW, panelH)
        pygame.draw.rect(self.infoScreen, (15, 15, 25), panelRect, border_radius=10)
        pygame.draw.rect(self.infoScreen, (70, 140, 200), panelRect, 2, border_radius=10)

        try:
            fHeader   = pygame.font.SysFont('Arial', 16, bold=True)
            fSubtitle = pygame.font.SysFont('Arial', 14, bold=True)
            fBody     = pygame.font.SysFont('Arial', 12)
            fSmall    = pygame.font.SysFont('Arial', 11)
        except Exception:
            fHeader   = pygame.font.Font(None, 18)
            fSubtitle = pygame.font.Font(None, 15)
            fBody     = pygame.font.Font(None, 13)
            fSmall    = pygame.font.Font(None, 12)

        x0, y0 = 25, 20
        line_h = 18

        # Header
        self.infoScreen.blit(fHeader.render('==== MÔ PHỎNG AMR ====', True, (100, 180, 255)), (x0, y0))
        y0 += line_h + 5

        # Vị trí + Điểm xuất phát (2 cột)
        self.infoScreen.blit(fSubtitle.render('Vị trí', True, (150, 200, 100)), (x0, y0))
        self.infoScreen.blit(fSubtitle.render('Điểm xuất phát', True, (150, 200, 100)), (x0 + 110, y0))
        y0 += line_h
        self.infoScreen.blit(fBody.render(f'X : {currentCol}', True, (210, 210, 210)), (x0, y0))
        self.infoScreen.blit(fBody.render(f'X : {startCol}',   True, (210, 210, 210)), (x0 + 110, y0))
        y0 += line_h
        self.infoScreen.blit(fBody.render(f'Y : {currentRow}', True, (210, 210, 210)), (x0, y0))
        self.infoScreen.blit(fBody.render(f'Y : {startRow}',   True, (210, 210, 210)), (x0 + 110, y0))
        y0 += line_h + 3

        # Hướng đi
        heading_deg    = heading if heading is not None else 0
        heading_name   = {0: 'PHẢI', 90: 'LÊN', 180: 'TRÁI', 270: 'XUỐNG'}.get(heading, '?')
        heading_symbol = {0: '→', 90: '↑', 180: '←', 270: '↓'}.get(heading, '?')
        self.infoScreen.blit(fSubtitle.render('Hướng đi', True, (150, 200, 100)), (x0, y0))
        y0 += line_h
        self.infoScreen.blit(fBody.render(f'{heading_symbol} {heading_name} ({heading_deg}°)', True, (255, 200, 100)), (x0, y0))
        y0 += line_h + 3

        # Thuật toán
        self.infoScreen.blit(fSubtitle.render('Thuật toán', True, (150, 200, 100)), (x0, y0))
        y0 += line_h
        self.infoScreen.blit(fBody.render('  [Wavefront]', True, (120, 200, 255)), (x0, y0))
        y0 += line_h + 3

        # Trạng thái
        self.infoScreen.blit(fSubtitle.render('Trạng thái', True, (150, 200, 100)), (x0, y0))
        y0 += line_h
        if reachedGoal:
            self.infoScreen.blit(fBody.render('[ĐÃ ĐẾN ĐÍCH]', True, (100, 220, 100)), (x0, y0))
            y0 += line_h
            self.infoScreen.blit(fSmall.render('>> Click để chọn đích mới', True, (255, 165, 0)), (x0, y0))
        else:
            self.infoScreen.blit(fBody.render('[ĐANG CHẠY]', True, (255, 200, 100)), (x0, y0))
            y0 += line_h
            self.infoScreen.blit(fSmall.render(f'Còn lại: {remainingSteps} bước', True, (200, 200, 200)), (x0, y0))

    def drawNavigationPanel(self, heading, currentRow, currentCol, remainingSteps, reachedGoal):
        """Deprecated - dùng drawStatusPanel thay thế."""
        pass
