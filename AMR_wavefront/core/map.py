from random import choice, random


class Maps(object):

    def __init__(self, mapSize=[30, 30]):
        """Khởi tạo ma trận bản đồ, đánh dấu viền ngoài là vật cản."""
        self.map = []
        for row in range(mapSize[0]):
            new_row = []
            for col in range(mapSize[1]):
                new_node = 1 if (row == 0 or row == mapSize[0] - 1 or
                                  col == 0 or col == mapSize[1] - 1) else 0
                new_row.append(new_node)
            self.map.append(new_row)

    def randomMap(self):
        """Tạo vật cản ngẫu nhiên mật độ cao (~32%)."""
        if self.map is not None:
            for row in range(1, len(self.map) - 1):
                for col in range(1, len(self.map[row]) - 1):
                    obstacle = choice((0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 0, 1, 0, 1, 0))
                    self.map[row][col] = obstacle
        else:
            print("Vui lòng khởi tạo bản đồ trước.")

    def randomSimpleMap(self, density=0.15):
        """Tạo vật cản ngẫu nhiên với mật độ thưa (mặc định 15%)."""
        if self.map is None:
            print("Vui lòng khởi tạo bản đồ trước.")
            return
        rows, cols = len(self.map), len(self.map[0])
        for row in range(1, rows - 1):
            for col in range(1, cols - 1):
                self.map[row][col] = 1 if random() < density else 0

    def simpleMap(self):
        """Bản đồ hành lang cố định (dùng để tham khảo/kiểm tra)."""
        if self.map is None:
            print("Vui lòng khởi tạo bản đồ trước.")
            return

        rows, cols = len(self.map), len(self.map[0])

        # Xoá hết vật cản cũ (chỉ giữ viền ngoài)
        for row in range(1, rows - 1):
            for col in range(1, cols - 1):
                self.map[row][col] = 0

        def tuong_doc(col, row_start, row_end):
            for r in range(row_start, row_end + 1):
                self.map[r][col] = 1

        def tuong_ngang(row, col_start, col_end):
            for c in range(col_start, col_end + 1):
                self.map[row][c] = 1

        # 2 tường dọc ngăn 3 hành lang, khe hở xen kẽ TRÊN/DƯỚI
        tuong_doc(4, 1, 8)
        tuong_doc(8, 3, 10)

        # 1 tường ngang ngắn tạo đoạn rẽ trái
        tuong_ngang(5, 2, 3)
