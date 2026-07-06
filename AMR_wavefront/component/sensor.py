from utils.utils import *


class Sensors(object):

    def __init__(self, position=[0, 0]):
        self.pos = position

    def setPos(self, position):
        self.pos = position

    def isWall(self, map, current_mposition):
        """Kiểm tra xem vị trí hiện tại có phải là vị trí biên không."""
        return (current_mposition[0] == 0) | (current_mposition[0] == len(map) - 1) | \
               (current_mposition[1] == 0) | (current_mposition[1] == len(map[0]) - 1)

    def getOutput(self, input, width, height):
        """Tìm tất cả hướng không có vật cản xung quanh vị trí hiện tại."""
        nodePos = turn2node(input, width, height, self.pos[0], self.pos[1])
        output = []
        if input[nodePos[0] - 1][nodePos[1]] == 0:
            output.append(270)
        if input[nodePos[0] + 1][nodePos[1]] == 0:
            output.append(90)
        if input[nodePos[0]][nodePos[1] - 1] == 0:
            output.append(180)
        if input[nodePos[0]][nodePos[1] + 1] == 0:
            output.append(0)
        return output
