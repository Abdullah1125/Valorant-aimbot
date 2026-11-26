import time
import cv2
import numpy as np
import mss
import serial
import serial.tools.list_ports


class SerialPortNotFoundError(RuntimeError):
    pass


class TemplateLoadError(RuntimeError):
    pass


class HidMouse:
    """Talks to a native-USB board (Leonardo/Pro Micro/Micro) running
    arduino/hid_mouse/hid_mouse.ino, which presents itself to the PC as
    a real second USB mouse and performs genuine HID move/click commands."""

    def __init__(self, log=print):
        self.log = log
        self.serial_port = None
        serial_port_name = self.find_serial_port()
        self.serial_port = serial.Serial(serial_port_name, 9600, timeout=1)
        time.sleep(2)  # the board resets when the serial port opens

    def find_serial_port(self):
        keywords = ("Arduino", "Leonardo", "SparkFun", "Pro Micro")
        port = next(
            (p for p in serial.tools.list_ports.comports()
             if any(k.lower() in (p.description or '').lower() for k in keywords)),
            None,
        )
        if port is not None:
            return port.device
        raise SerialPortNotFoundError(
            'HID kartı bulunamadı. USB bağlantısını kontrol edip tekrar dene.'
        )

    def move(self, dx, dy):
        if dx == 0 and dy == 0:
            return
        self.serial_port.write(f'move {dx} {dy}\n'.encode())

    def click(self):
        self.serial_port.write(b'click\n')

    def close(self):
        if self.serial_port:
            self.serial_port.close()

    def __del__(self):
        self.close()


class AimBot:
    def __init__(self, game_window, template_file=None, log=print):
        self.game_window = game_window
        self.log = log
        self.hid = HidMouse(log=log)
        self.sct = mss.mss()
        self.scale = 2
        self.min_distance = 30      # px within which we consider the crosshair "on target"
        self.max_step = 40          # px moved towards the target per frame (smoothing)
        self.aim_gain = 1.0         # scales screen-space error to mouse-move units
        self.fire_cooldown = 0.25
        self.center_x = self.game_window['width'] // 2
        self.center_y = self.game_window['height'] // 2
        self.template = self.get_template(template_file) if template_file else None
        self._last_fire = 0.0
        self._running = False

    def __del__(self):
        if hasattr(self, 'hid'):
            del self.hid
        if hasattr(self, 'sct'):
            del self.sct

    def get_screenshot(self):
        return np.array(self.sct.grab(self.game_window))

    def get_template(self, template_file):
        template_img = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
        if template_img is None:
            raise TemplateLoadError(f'Şablon görseli okunamadı: {template_file}')
        return cv2.resize(template_img, (0, 0), fx=self.scale, fy=self.scale)

    def find_template(self, template_img, gray_img):
        res = cv2.matchTemplate(gray_img, template_img, cv2.TM_CCOEFF_NORMED)
        return np.where(res >= 0.7)

    def find_target(self, scaled_gray_img):
        if self.template is None:
            return None
        loc = self.find_template(self.template, scaled_gray_img)
        points = list(zip(*loc[::-1]))
        if not points:
            return None
        best_x, best_y = points[0]
        th, tw = self.template.shape
        target_x = (best_x + tw // 2) / self.scale
        target_y = (best_y + th // 2) / self.scale
        return target_x, target_y

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        while self._running:
            try:
                img = self.get_screenshot()
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                scaled_gray = cv2.resize(gray, (0, 0), fx=self.scale, fy=self.scale)
                target = self.find_target(scaled_gray)
                now = time.time()

                if target is not None:
                    dx = target[0] - self.center_x
                    dy = target[1] - self.center_y
                    distance = (dx ** 2 + dy ** 2) ** 0.5

                    if distance <= self.min_distance:
                        if now - self._last_fire > self.fire_cooldown:
                            self.hid.click()
                            self._last_fire = now
                    else:
                        step_x = int(max(-self.max_step, min(self.max_step, dx * self.aim_gain)))
                        step_y = int(max(-self.max_step, min(self.max_step, dy * self.aim_gain)))
                        self.hid.move(step_x, step_y)
            except Exception as e:
                self.log(str(e))
            time.sleep(0.01)
