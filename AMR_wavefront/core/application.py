"""core/application.py - Lớp ứng dụng chính điều phối vòng lặp mô phỏng AMR."""

import pygame
import sys
import atexit
import random
import time
from core.input import Input
from core.map import Maps
from core.graphic import Graphics
from core.amr import Amrs
from component.sensor import Sensors
from component.processor import Processors
from component.actuator import Actuators
from utils.utils import *

# 4 vùng góc bản đồ (hàng/cột theo nghĩa thị giác)
ZONES = [('low', 'low'), ('low', 'high'), ('high', 'low'), ('high', 'high')]


class Application(object):

    def __init__(self, screenSize=None):
        pygame.init()
        if screenSize is None:
            info = pygame.display.Info()
            screenSize = [int(info.current_w * 0.85), int(info.current_h * 0.85)]

        self.graphic  = Graphics(screenSize)
        self.running  = True
        self.clock    = pygame.time.Clock()
        self.lastTime = pygame.time.get_ticks()
        self.input    = Input()
        self.processor = Processors()

        self._setup_map_and_goal()

        startPixelPos = list(turn2pixel(
            self.map.map,
            self.graphic.screen.get_height(),
            self.graphic.screen.get_width(),
            self.startRow, self.startCol
        ))
        self.amr    = Amrs(position=startPixelPos[:])
        self.sensor = Sensors(position=startPixelPos[:])

        self.reachedGoal = False
        self.actuator    = Actuators()
        atexit.register(self._shutdown)

    def _shutdown(self):
        self.actuator.close()

    def _pickZonePoint(self):
        """Chọn ngẫu nhiên một trong 4 góc bản đồ."""
        rows = len(self.map.map)
        cols = len(self.map.map[0])
        corners = [
            (1, 1),
            (1, cols - 2),
            (rows - 2, 1),
            (rows - 2, cols - 2)
        ]
        return random.choice(corners)

    def _pointInZone(self, rowSide, colSide):
        rows = len(self.map.map)
        cols = len(self.map.map[0])
        rMid, cMid = rows // 2, cols // 2

        def span(size, mid, side):
            if side == 'low':
                return (1, max(1, mid - 2))
            else:
                return (min(size - 2, mid + 2), size - 2)

        r0, r1 = span(rows, rMid, rowSide)
        c0, c1 = span(cols, cMid, colSide)
        return (random.randint(r0, r1), random.randint(c0, c1))

    def _pointInOtherZone(self, refRow, refCol):
        """Chọn điểm ở vùng góc khác với điểm tham chiếu."""
        rows = len(self.map.map)
        cols = len(self.map.map[0])
        refRowSide = 'low' if refRow < rows // 2 else 'high'
        refColSide = 'low' if refCol < cols // 2 else 'high'
        otherZones = [z for z in ZONES if z != (refRowSide, refColSide)]
        rowSide, colSide = random.choice(otherZones)
        return self._pointInZone(rowSide, colSide)

    def _pickDistinctZonePoint(self, refRow, refCol):
        """Chọn điểm đích ở góc khác với điểm bắt đầu."""
        rows = len(self.map.map)
        cols = len(self.map.map[0])
        corners = [(1, 1), (1, cols - 2), (rows - 2, 1), (rows - 2, cols - 2)]
        other_corners = [c for c in corners if c != (refRow, refCol)]
        return random.choice(other_corners)

    def _setup_map_and_goal(self):
        """Tạo bản đồ ngẫu nhiên và chọn START/GOAL đảm bảo có đường đi đầy đủ."""
        self.map = Maps(mapSize=[18, 18])
        self.map.randomSimpleMap(0.10)

        self.startRow, self.startCol = self._pickZonePoint()
        self.goalRow,  self.goalCol  = self._pickDistinctZonePoint(self.startRow, self.startCol)

        maxAttempts = 200
        attempt = 0
        for attempt in range(maxAttempts):
            self.map.map[self.startRow][self.startCol] = 0
            self.map.map[self.goalRow][self.goalCol]   = 0
            field = self.processor.computeWavefront(self.map.map, self.goalRow, self.goalCol)
            if field[self.startRow][self.startCol] != -1 and \
               self._pathHasFullVariety(self.startRow, self.startCol, self.goalRow, self.goalCol):
                break
            self.map.randomSimpleMap(0.12)

        distToGoal = self.processor.potentialField[self.startRow][self.startCol]
        print(f'[Wavefront] Sinh bản đồ thành công sau {attempt + 1} lần thử.')
        print(f'[Wavefront] START=({self.startRow},{self.startCol})  GOAL=({self.goalRow},{self.goalCol})')
        print(f'[Wavefront] Khoảng cách ngắn nhất START→GOAL: {distToGoal} bước lưới')

    def _nearestFreeCell(self, row, col, maxRadius=6):
        """Tìm ô trống gần nhất với (row, col) trong bán kính maxRadius."""
        rows, cols = len(self.map.map), len(self.map.map[0])
        if 0 <= row < rows and 0 <= col < cols and self.map.map[row][col] == 0:
            return (row, col)
        for radius in range(1, maxRadius + 1):
            candidates = []
            for dr in range(-radius, radius + 1):
                for dc in range(-radius, radius + 1):
                    if max(abs(dr), abs(dc)) != radius:
                        continue
                    nr, nc = row + dr, col + dc
                    if 0 <= nr < rows and 0 <= nc < cols and self.map.map[nr][nc] == 0:
                        candidates.append((dr * dr + dc * dc, nr, nc))
            if candidates:
                candidates.sort()
                return (candidates[0][1], candidates[0][2])
        return None

    def _pathHasFullVariety(self, startRow, startCol, goalRow, goalCol):
        """Kiểm tra đường đi có chứa cả rẽ trái (180) lẫn quay đầu (270) không."""
        rows, cols = len(self.map.map), len(self.map.map[0])
        r, c = startRow, startCol
        seen = set()
        steps = 0
        maxSteps = rows * cols * 2
        while (r, c) != (goalRow, goalCol) and steps < maxSteps:
            steps += 1
            best = None
            for heading, (dr, dc) in ((270, (-1, 0)), (90, (1, 0)), (180, (0, -1)), (0, (0, 1))):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and self.map.map[nr][nc] == 0:
                    val = self.processor.potentialField[nr][nc]
                    if val != -1 and (best is None or val < best[0]):
                        best = (val, heading, nr, nc)
            if best is None:
                return False
            seen.add(best[1])
            r, c = best[2], best[3]
        return (180 in seen) and (270 in seen)

    def unitDistance(self):
        row_segment = len(self.map.map) - 1
        col_segment = len(self.map.map[0]) - 1
        row_distance = self.graphic.screen.get_height() / row_segment
        col_distance = self.graphic.screen.get_width()  / col_segment
        return (row_distance, col_distance)

    def _handleGoalClick(self, mousePos):
        """Xử lý click chuột để đổi đích ngay lập tức."""
        mapWidth = self.graphic.screen.get_width()
        if mousePos[0] >= mapWidth:
            return

        clickRow, clickCol = turn2node(
            self.map.map, mapWidth, self.graphic.screen.get_height(),
            mousePos[0], mousePos[1]
        )

        rows = len(self.map.map)
        cols = len(self.map.map[0])
        clickRow = max(0, min(rows - 1, clickRow))
        clickCol = max(0, min(cols - 1, clickCol))

        target = self._nearestFreeCell(clickRow, clickCol)
        if target is None:
            print(f'[Wavefront] Không tìm thấy ô trống gần ({clickRow},{clickCol}) - thử click chỗ khác.')
            return
        if target != (clickRow, clickCol):
            print(f'[Wavefront] Ô ({clickRow},{clickCol}) là vật cản → tự động chọn ô trống gần nhất {target}')

        self.goalRow, self.goalCol = target
        self.processor.computeWavefront(self.map.map, self.goalRow, self.goalCol)
        self.reachedGoal = False
        print(f'[Wavefront] ĐÍCH MỚI: {target} → AMR đổi hướng ngay lập tức!')

    def initialize(self):
        pass

    def update(self):
        pass

    def run(self):
        self.initialize()

        last_motor_cmd_time = time.time()
        motor_cmd_interval  = 0.1  # 100ms

        while self.running:
            self.input.update()
            if self.input.quit:
                self.running = False

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self._handleGoalClick(event.pos)

            self.sensor.setPos(self.amr.pos)
            sensory = self.sensor.getOutput(
                self.map.map,
                self.graphic.screen.get_width(),
                self.graphic.screen.get_height()
            )

            currentRow, currentCol = turn2node(
                self.map.map,
                self.graphic.screen.get_width(),
                self.graphic.screen.get_height(),
                self.amr.pos[0], self.amr.pos[1]
            )
            currentPotential = self.processor.potentialField[currentRow][currentCol]
            remainingSteps   = currentPotential if currentPotential != -1 else 0

            solution = None
            if (currentRow, currentCol) == (self.goalRow, self.goalCol):
                if not self.reachedGoal:
                    print(f'[Wavefront] AMR đã đến ĐÍCH tại hàng {self.goalRow}, cột {self.goalCol}!')
                    print('[Wavefront] Click vào bản đồ để chọn đích tiếp theo.')
                self.reachedGoal = True
            elif sensory:
                self.processor.staticObstacleAvoidanceSolution(sensory)
                solution = self.processor.makeDecisionWavefront(currentRow, currentCol)
                if solution is not None:
                    if solution in [90, 270]:
                        self.amr.speed = self.unitDistance()[0]
                    elif solution in [0, 180]:
                        self.amr.speed = self.unitDistance()[1]
                    self.amr.heading = solution
                    self.amr.moveForward(self.amr.speed)

            # Gửi lệnh motor theo chu kỳ 100ms (heartbeat)
            now = time.time()
            if now - last_motor_cmd_time >= motor_cmd_interval:
                self.actuator.set_motors(solution)
                last_motor_cmd_time = now

            self.graphic.fullScreen.fill((255, 255, 255))
            self.graphic.drawMap(self.map.map, (220, 220, 220))
            self.graphic.drawAxis(self.map.map)
            self.graphic.drawGoal(self.map.map, self.goalRow, self.goalCol)
            self.graphic.drawAmr(self.amr)
            self.graphic.drawStatusPanel(
                solution, currentRow, currentCol,
                remainingSteps, self.reachedGoal,
                self.actuator, self.startRow, self.startCol
            )

            pygame.display.flip()
            self.clock.tick(1)

        pygame.quit()
        sys.exit()
