import numpy as np


def turn2pixel(map, height, width, row_position, col_position):
    """Chuyển tọa độ lưới (hàng, cột) sang tọa độ pixel Pygame."""
    row_segment = len(map) - 1
    col_segment = len(map[0]) - 1
    row_distance = height / row_segment
    col_distance = width  / col_segment
    x_pixel = col_position * col_distance
    y_pixel = height - row_position * row_distance
    return (x_pixel, y_pixel)


def turn2node(map, width, height, x_pixel, y_pixel):
    """Chuyển tọa độ pixel Pygame sang tọa độ lưới (hàng, cột)."""
    row_segment = len(map) - 1
    col_segment = len(map[0]) - 1
    row_distance = height / row_segment
    col_distance = width  / col_segment
    row_pos = round((height - y_pixel) / row_distance)
    col_pos = round(x_pixel / col_distance)
    return (row_pos, col_pos)


def transformationMatrix2d(scale=(1.0, 1.0), rotation_deg=0.0, translation=(0.0, 0.0)):
    """Tạo ma trận biến đổi 2D (3x3) theo thứ tự: Tỉ lệ → Quay → Dịch chuyển."""
    sx, sy = scale
    tx, ty = translation
    theta  = np.deg2rad(rotation_deg)

    S = np.array([[sx, 0,  0],
                  [0,  sy, 0],
                  [0,  0,  1]])

    R = np.array([[np.cos(theta), -np.sin(theta), 0],
                  [np.sin(theta),  np.cos(theta), 0],
                  [0,              0,             1]])

    T = np.array([[1, 0, tx],
                  [0, 1, ty],
                  [0, 0, 1]])

    return T @ R @ S


def apply_transformation(points, matrix):
    """Áp dụng ma trận biến đổi 3x3 lên tập điểm Nx2."""
    if points.ndim != 2 or points.shape[1] != 2:
        raise ValueError("Mảng điểm phải có kích thước Nx2.")

    ones = np.ones((points.shape[0], 1))
    homogeneous_points = np.hstack([points, ones])
    transformed = homogeneous_points @ matrix.T
    return transformed[:, :2]
