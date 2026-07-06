"""component/actuator.py - Điều khiển motor AMR qua WiFi"""

import socket
import pygame
import time


class Actuators:
    ESP32_IP   = '192.168.4.1'
    ESP32_PORT = 5005

    HEADING_TO_CMD = {
        90 : b'F',
        270: b'B',
        0  : b'R',
        180: b'L',
    }

    HEADING_TO_NAME = {
        90 : 'TIẾN',
        270: 'LÙI',
        0  : 'RẼ PHẢI',
        180: 'RẼ TRÁI',
        None: 'DỪNG'
    }

    HEADING_TO_SPEEDS = {
        90 : (+100, +100),
        270: (-100, -100),
        0  : (+100,  +50),
        180: ( +50, +100),
        None: (0, 0)
    }

    def __init__(self):
        self.last_heading = None
        self.sim_mode     = True
        self.sock         = None

        self.turn_start_time = 0
        self.is_turning = False
        self.current_display_name = 'DỪNG'
        self.current_display_speeds = (0, 0)
        self.last_sent_cmd = None

        self._auto_detect()

    def _auto_detect(self):
        """Tự động phát hiện chế độ: phần cứng hoặc mô phỏng."""
        try:
            test_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            test_sock.settimeout(1.0)
            test_sock.sendto(b'S', (self.ESP32_IP, self.ESP32_PORT))
            test_sock.close()

            self.sock     = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(0.05)
            self.sim_mode = False
            print('[Actuator] CHẾ ĐỘ PHẦN CỨNG - Kết nối ESP32 thành công!')
            print(f'           IP: {self.ESP32_IP}:{self.ESP32_PORT}')

        except Exception:
            self.sim_mode = True
            print('[Actuator] CHẾ ĐỘ MÔ PHỎNG - Chạy độc lập (không cần phần cứng)')

    def set_motors(self, heading):
        """Gọi mỗi vòng lặp để cập nhật lệnh động cơ theo hướng hiện tại."""
        # Phát hiện khi thuật toán đổi sang hướng rẽ mới
        if heading != self.last_heading:
            if heading in [0, 180]:
                self.is_turning = True
                self.turn_start_time = time.time()
            else:
                self.is_turning = False
            self.last_heading = heading

        # Override: sau 1 giây rẽ, ép xe đi thẳng
        cmd_override = name_override = speeds_override = None
        if self.is_turning and (time.time() - self.turn_start_time) >= 1.0:
            cmd_override    = b'F'
            name_override   = 'RẼ → TIẾN THẲNG'
            speeds_override = (+100, +100)

        cmd    = cmd_override    or self.HEADING_TO_CMD.get(heading, b'S')
        name   = name_override   or self.HEADING_TO_NAME.get(heading, 'DỪNG')
        speeds = speeds_override or self.HEADING_TO_SPEEDS.get(heading, (0, 0))

        self.current_display_name   = name
        self.current_display_speeds = speeds
        headingTxt = f'{heading:3d}' if isinstance(heading, int) else '  -'

        if self.sim_mode:
            if cmd != self.last_sent_cmd:
                print(f'[SIM] Hướng={headingTxt}° -> {name:18s} | Trái={speeds[0]:+d}%  Phải={speeds[1]:+d}%')
                self.last_sent_cmd = cmd
        else:
            try:
                self.sock.sendto(cmd, (self.ESP32_IP, self.ESP32_PORT))
                if cmd != self.last_sent_cmd:
                    print(f'[HW]  Hướng={headingTxt}° -> {name:18s} | Trái={speeds[0]:+d}%  Phải={speeds[1]:+d}%')
                    self.last_sent_cmd = cmd
            except Exception:
                self.sim_mode = True
                print('[Actuator] Mất kết nối ESP32, chuyển sang CHẾ ĐỘ MÔ PHỎNG')

    def draw_panel(self, screen):
        """Vẽ panel hiển thị trạng thái động cơ lên màn hình Pygame."""
        panel = pygame.Rect(10, 10, 240, 120)
        pygame.draw.rect(screen, (20, 20, 20), panel, border_radius=8)
        pygame.draw.rect(screen, (80, 80, 80), panel, 1, border_radius=8)

        try:
            f_bold = pygame.font.SysFont('Arial', 13, bold=True)
            f_body = pygame.font.SysFont('Arial', 12)
            f_xs   = pygame.font.SysFont('Arial', 10)
        except Exception:
            f_bold = pygame.font.Font(None, 15)
            f_body = pygame.font.Font(None, 13)
            f_xs   = pygame.font.Font(None, 11)

        x0, y0 = 18, 16
        screen.blit(f_bold.render(f'Hướng : {self.current_display_name}', True, (255, 220, 50)), (x0, y0))

        l_spd, r_spd = self.current_display_speeds

        def spd_color(v):
            if v > 0:  return (50,  200, 100)
            if v < 0:  return (220, 80,  80)
            return (120, 120, 120)

        screen.blit(f_body.render(f'Motor Trái : {l_spd:+d}%', True, spd_color(l_spd)), (x0, y0 + 22))
        screen.blit(f_body.render(f'Motor Phải : {r_spd:+d}%', True, spd_color(r_spd)), (x0, y0 + 39))

        self._bar(screen, f_xs, x0,       y0 + 84, 'T', l_spd, spd_color(l_spd))
        self._bar(screen, f_xs, x0 + 115, y0 + 84, 'P', r_spd, spd_color(r_spd))

    def _bar(self, screen, font, x, y, label, pct, color):
        W = 90
        screen.blit(font.render(label, True, (180, 180, 180)), (x, y))
        pygame.draw.rect(screen, (50, 50, 50), (x+12, y+1, W, 7), border_radius=3)
        filled = int(abs(pct) / 100 * W)
        if filled:
            pygame.draw.rect(screen, color, (x+12, y+1, filled, 7), border_radius=3)

    def close(self):
        if not self.sim_mode and self.sock:
            try:
                self.sock.sendto(b'S', (self.ESP32_IP, self.ESP32_PORT))
            except Exception:
                pass
            finally:
                self.sock.close()
        print('[Actuator] Đã đóng.')
