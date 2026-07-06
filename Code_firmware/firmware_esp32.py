import network
import socket
from machine import Pin, PWM
import time
import gc

# ============================================================
# CAU HINH CHAN GPIO - DONG CO
# ============================================================
ENA = PWM(Pin(13), freq=1000)
IN1 = Pin(12, Pin.OUT)
IN2 = Pin(14, Pin.OUT)

ENB = PWM(Pin(15), freq=1000)
IN3 = Pin(4,  Pin.OUT)
IN4 = Pin(2,  Pin.OUT)

# Thoi gian cho lenh (ms) - qua thoi gian nay khong co lenh -> dung xe
TIMEOUT_MS = 2000   
TURN_DURATION_MS = 800  # <--- ĐÃ GIẢM XUỐNG 800ms ĐỂ TRÁNH LỆCH HEADING

# ============================================================
# ENCODER (dem suon len, khong phan biet chieu)
# ============================================================
ENC_R = Pin(22, Pin.IN, Pin.PULL_UP)   
ENC_L = Pin(26, Pin.IN, Pin.PULL_UP)   

encR_count = 0
encL_count = 0
_lastIrqR  = 0
_lastIrqL  = 0
DEBOUNCE_MS = 2

def _isrR(pin):
    global encR_count, _lastIrqR
    now = time.ticks_ms()
    if time.ticks_diff(now, _lastIrqR) >= DEBOUNCE_MS:
        encR_count += 1
        _lastIrqR = now

def _isrL(pin):
    global encL_count, _lastIrqL
    now = time.ticks_ms()
    if time.ticks_diff(now, _lastIrqL) >= DEBOUNCE_MS:
        encL_count += 1
        _lastIrqL = now

ENC_R.irq(trigger=Pin.IRQ_RISING, handler=_isrR)
ENC_L.irq(trigger=Pin.IRQ_RISING, handler=_isrL)

# ============================================================
# DIEU KHIEN TOC DO BANG PI
# ============================================================
V_FULL = 22.0   

KP_PI = 15.0
KI_PI = 15.0

CONTROL_INTERVAL_MS = 30
EMA_B       = 0.6
PWM_MIN_RUN = 300
PWM_SLEW    = 60

target_A = 0.0   
target_B = 0.0   

vA_ema = 0.0
vB_ema = 0.0
piA_i  = 0.0
piB_i  = 0.0
pwmA_prev = 0
pwmB_prev = 0

_lastEncR_ctrl = 0
_lastEncL_ctrl = 0
_lastCtrlMs    = 0

turn_start_time = 0
is_auto_straight_pending = False

def _shape_pwm(target, prev):
    s = int(target)
    if 0 < s < PWM_MIN_RUN:
        s = PWM_MIN_RUN
    d = s - prev
    if d >  PWM_SLEW: s = prev + PWM_SLEW
    elif d < -PWM_SLEW: s = prev - PWM_SLEW
    if s < 0:    s = 0
    if s > 1023: s = 1023
    return s

def _pi_step_A(v_target, v_meas, dt_s):
    global piA_i
    err    = abs(v_target) - abs(v_meas)
    piA_i += KI_PI * err * dt_s
    if piA_i < 0.0:    piA_i = 0.0
    if piA_i > 1023.0: piA_i = 1023.0
    u = KP_PI * err + piA_i
    if u < 0:    u = 0
    if u > 1023: u = 1023
    return int(u)

def _pi_step_B(v_target, v_meas, dt_s):
    global piB_i
    err    = abs(v_target) - abs(v_meas)
    piB_i += KI_PI * err * dt_s
    if piB_i < 0.0:    piB_i = 0.0
    if piB_i > 1023.0: piB_i = 1023.0
    u = KP_PI * err + piB_i
    if u < 0:    u = 0
    if u > 1023: u = 1023
    return int(u)

def _stop_motorA():
    global piA_i, vA_ema, pwmA_prev
    piA_i = 0.0; vA_ema = 0.0; pwmA_prev = 0
    IN1.value(0); IN2.value(0); ENA.duty(0)

def _stop_motorB():
    global piB_i, vB_ema, pwmB_prev
    piB_i = 0.0; vB_ema = 0.0; pwmB_prev = 0
    IN3.value(0); IN4.value(0); ENB.duty(0)

def dieu_chinh_pi():
    global encR_count, encL_count, _lastEncR_ctrl, _lastEncL_ctrl, _lastCtrlMs
    global vA_ema, vB_ema, pwmA_prev, pwmB_prev

    now  = time.ticks_ms()
    dt_s = time.ticks_diff(now, _lastCtrlMs) / 1000.0
    _lastCtrlMs = now
    if dt_s <= 0: return

    dR = encR_count - _lastEncR_ctrl
    dL = encL_count - _lastEncL_ctrl
    _lastEncR_ctrl = encR_count
    _lastEncL_ctrl = encL_count

    if target_A == 0.0 and target_B == 0.0:
        _stop_motorA(); _stop_motorB()
        return

    if target_A == 0.0:
        _stop_motorA()          
    else:
        signA   = 1.0 if target_A > 0 else -1.0
        vA_meas = (dR / dt_s) * signA
        vA_ema  = EMA_B * vA_ema + (1.0 - EMA_B) * vA_meas
        pwmA_cmd = _shape_pwm(_pi_step_A(target_A, vA_ema, dt_s), pwmA_prev)
        pwmA_prev = pwmA_cmd
        IN1.value(1 if target_A > 0 else 0); IN2.value(0 if target_A > 0 else 1)
        ENA.duty(pwmA_cmd)

    if target_B == 0.0:
        _stop_motorB()          
    else:
        signB   = 1.0 if target_B > 0 else -1.0
        vB_meas = (dL / dt_s) * signB
        vB_ema  = EMA_B * vB_ema + (1.0 - EMA_B) * vB_meas
        pwmB_cmd = _shape_pwm(_pi_step_B(target_B, vB_ema, dt_s), pwmB_prev)
        pwmB_prev = pwmB_cmd
        IN3.value(1 if target_B > 0 else 0); IN4.value(0 if target_B > 0 else 1)
        ENB.duty(pwmB_cmd)

# ============================================================
# HAM DIEU KHIEN MOTOR 
# ============================================================
def dung():
    global target_A, target_B, is_auto_straight_pending
    target_A = 0.0; target_B = 0.0
    is_auto_straight_pending = False

def tien():
    global target_A, target_B, is_auto_straight_pending
    target_A = V_FULL; target_B = V_FULL
    is_auto_straight_pending = False

def lui():
    global target_A, target_B, is_auto_straight_pending
    target_A = -V_FULL; target_B = -V_FULL
    is_auto_straight_pending = False

def re_trai():
    global target_A, target_B, turn_start_time, is_auto_straight_pending
    target_A = 0.0         
    target_B = V_FULL      
    turn_start_time = time.ticks_ms()
    is_auto_straight_pending = True

def re_phai():
    global target_A, target_B, turn_start_time, is_auto_straight_pending
    target_A = V_FULL         
    target_B = 0.0
    turn_start_time = time.ticks_ms()
    is_auto_straight_pending = True

LENH = {b'F': tien, b'B': lui, b'L': re_trai, b'R': re_phai, b'S': dung}
TEN  = {b'F': 'TIEN', b'B': 'LUI', b'L': 'RE TRAI', b'R': 'RE PHAI', b'S': 'DUNG'}

# ============================================================
# KHOI DONG WIFI AP
# ============================================================
def start_ap():
    ap = network.WLAN(network.AP_IF)
    ap.active(False); time.sleep(0.5); gc.collect(); ap.active(True)
    ap.config(essid='AMR_Robot', password='12345678', authmode=3, channel=1, hidden=False)
    print('=' * 44)
    print(f'  IP: {ap.ifconfig()[0]}  |  Port: 5005 | Sẵn sàng!')
    print('=' * 44)
    return ap

def create_socket():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(('0.0.0.0', 5005))
    s.settimeout(0.05)
    return s

# KHỞI ĐỘNG HỆ THỐNG
dung()
ap   = start_ap()
sock = create_socket()
gc.collect()

last_cmd_time  = time.ticks_ms()
last_ctrl_time = time.ticks_ms()
last_dbg_time  = time.ticks_ms()
ap_check_count = 0
is_stopped     = True
_lastCtrlMs    = time.ticks_ms()
prev_cmd       = b'S'   

print('San sang nhan lenh...')

# ============================================================
# VÒNG LẶP CHÍNH (MAIN LOOP)
# ============================================================
while True:
    try:
        data, addr = sock.recvfrom(16)
        lenh = data.strip()

        if lenh in LENH:
            if is_auto_straight_pending and (lenh == b'L' or lenh == b'R'):
                last_cmd_time = time.ticks_ms() 
                continue 

            if lenh != prev_cmd:
                piA_i = 0.0;  piB_i = 0.0
                pwmA_prev = 0; pwmB_prev = 0
                prev_cmd = lenh
            last_cmd_time = time.ticks_ms()
            LENH[lenh]()
            is_stopped = (lenh == b'S')
            print(f'[Motor] Lệnh: {TEN.get(lenh, "?")}')
    except OSError:
        pass

    if is_auto_straight_pending:
        if time.ticks_diff(time.ticks_ms(), turn_start_time) >= TURN_DURATION_MS:
            is_auto_straight_pending = False
            tien()          
            prev_cmd = b'F'  
            last_cmd_time = time.ticks_ms() 
            print(f'[Auto-Logic] Đã rẽ đủ {TURN_DURATION_MS}ms -> TỰ ĐỘNG CHUYỂN ĐI THẲNG')

    if time.ticks_diff(time.ticks_ms(), last_ctrl_time) >= CONTROL_INTERVAL_MS:
        dieu_chinh_pi()
        last_ctrl_time = time.ticks_ms()

    if not is_stopped:
        if time.ticks_diff(time.ticks_ms(), last_dbg_time) >= 500:
            print(f'[PI] A: tgt={target_A:+.1f} pwm={pwmA_prev:4d} | B: tgt={target_B:+.1f} pwm={pwmB_prev:4d}')
            last_dbg_time = time.ticks_ms()

    if not is_auto_straight_pending and not is_stopped:
        if time.ticks_diff(time.ticks_ms(), last_cmd_time) > TIMEOUT_MS:
            dung()
            is_stopped = True
            prev_cmd = b'S'   
            print(f'[Safety] Hết timeout -> DỪNG XE')

    ap_check_count += 1
    if ap_check_count >= 200:
        ap_check_count = 0
        gc.collect()
        if ap is None or not ap.active():
            dung(); is_stopped = True; prev_cmd = b'S'
            try: sock.close()
            except: pass
            ap = start_ap(); sock = create_socket()