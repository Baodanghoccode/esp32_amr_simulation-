from random import choice
from collections import deque


class Processors(object):

    # Ánh xạ heading (độ) -> độ lệch (dRow, dCol) trên lưới
    # Quy ước: row tăng = đi LÊN màn hình
    HEADING_DELTA = {
        90:  (1, 0),
        270: (-1, 0),
        180: (0, -1),
        0:   (0, 1),
    }

    def __init__(self, obstacleSolution=()):
        self.obstacleSolution = obstacleSolution
        self.path = []
        self.lastDecision = 90
        self.potentialField = None

    def rule1(self):
        pass

    def staticObstacleAvoidanceSolution(self, sensorInput) -> tuple:
        self.obstacleSolution = tuple(sensorInput)

    def pathPlanning(self, path):
        self.path = path

    def makeDecision(self) -> int:
        """Chọn hướng ngẫu nhiên trong danh sách hướng an toàn (thuật toán gốc)."""
        bestSolution = None
        if (solutionNumber := len(self.obstacleSolution)) > 0:
            if solutionNumber > 1:
                obstacleSolution = list(self.obstacleSolution)
                if self.lastDecision in obstacleSolution:
                    obstacleSolution.remove(self.lastDecision)
                bestSolution = int(choice(obstacleSolution))
            else:
                bestSolution = int(self.obstacleSolution[0])
        self.lastDecision = bestSolution + 180
        if self.lastDecision >= 360:
            self.lastDecision %= 360
        return bestSolution

    def output(self):
        pass

    def computeWavefront(self, mapGrid, goalRow, goalCol):
        """Lan truyền sóng BFS từ ô đích ra toàn bản đồ."""
        rows = len(mapGrid)
        cols = len(mapGrid[0]) if rows else 0
        potential = [[-1] * cols for _ in range(rows)]

        if not (0 <= goalRow < rows and 0 <= goalCol < cols):
            self.potentialField = potential
            return potential

        if mapGrid[goalRow][goalCol] == 1:
            self.potentialField = potential
            return potential

        potential[goalRow][goalCol] = 0
        queue = deque([(goalRow, goalCol)])

        while queue:
            r, c = queue.popleft()
            currentVal = potential[r][c]
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    if mapGrid[nr][nc] == 0 and potential[nr][nc] == -1:
                        potential[nr][nc] = currentVal + 1
                        queue.append((nr, nc))

        self.potentialField = potential
        return potential

    def makeDecisionWavefront(self, currentRow, currentCol) -> int:
        """Chọn hướng có thế năng Wavefront thấp nhất trong số hướng cảm biến xác nhận an toàn.
        Ưu tiên giữ nguyên hướng đang đi khi nhiều hướng bằng nhau (giảm zigzag)."""
        if len(self.obstacleSolution) == 0:
            return None

        if self.potentialField is None:
            return self.makeDecision()

        rows = len(self.potentialField)
        cols = len(self.potentialField[0]) if rows else 0

        prevHeading = (self.lastDecision + 180) % 360
        bestSolution = bestValue = None
        bestIsStraight = False

        for heading in self.obstacleSolution:
            delta = self.HEADING_DELTA.get(heading)
            if delta is None:
                continue
            nr, nc = currentRow + delta[0], currentCol + delta[1]

            if not (0 <= nr < rows and 0 <= nc < cols):
                continue

            val = self.potentialField[nr][nc]
            if val == -1:
                continue

            isStraight = (heading == prevHeading)
            betterValue = bestValue is None or val < bestValue
            tieButStraighter = (val == bestValue and isStraight and not bestIsStraight)
            if betterValue or tieButStraighter:
                bestValue      = val
                bestSolution   = heading
                bestIsStraight = isStraight

        if bestSolution is None:
            return self.makeDecision()

        self.lastDecision = (bestSolution + 180) % 360
        return bestSolution

    def findShortestPath(self, startRow, startCol):
        """Trả về list[(row, col)] là đường đi ngắn nhất từ START đến ĐÍCH,
        hoặc None nếu chưa tính trường thế năng / không có đường đi."""
        if self.potentialField is None:
            return None

        rows = len(self.potentialField)
        cols = len(self.potentialField[0]) if rows else 0
        if not (0 <= startRow < rows and 0 <= startCol < cols):
            return None
        if self.potentialField[startRow][startCol] == -1:
            return None

        path = [(startRow, startCol)]
        r, c = startRow, startCol
        prevHeading = (self.lastDecision + 180) % 360

        guard, maxGuard = 0, rows * cols + 1
        while self.potentialField[r][c] != 0 and guard <= maxGuard:
            guard += 1
            currentVal = self.potentialField[r][c]

            candidates = []
            for heading, (dr, dc) in self.HEADING_DELTA.items():
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and \
                   self.potentialField[nr][nc] == currentVal - 1:
                    candidates.append((heading, nr, nc))

            if not candidates:
                return None

            heading, nr, nc = next(
                (cand for cand in candidates if cand[0] == prevHeading),
                candidates[0]
            )
            prevHeading = heading
            r, c = nr, nc
            path.append((r, c))

        self.pathPlanning(path)
        return path
