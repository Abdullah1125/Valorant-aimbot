import threading
import serial
import serial.tools.list_ports
import time
import cv2
import numpy as np
import mss
import sys
from pynput.mouse import Button, Controller


class MouseTelemetryReader:
    """Reads real-mouse movement/click events relayed by the Arduino
    (arduino/mouse_telemetry/mouse_telemetry.ino, via the USB Host Shield)
    over serial, in a background thread."""

    def __init__(self):
        self.serial_port = None
        self.last_line = ''
        self._stop = False
        self._thread = None
        serial_port_name = self.find_serial_port()
        self.serial_port = serial.Serial(serial_port_name, 9600, timeout=1)
        time.sleep(2)  # Arduino resets when the serial port opens
        self._thread = threading.Thread(target=self._read_loop, daemon=True)
        self._thread.start()

    def find_serial_port(self):
        port = next((p for p in serial.tools.list_ports.comports() if "Arduino" in p.description), None)
        if port is not None:
            return port.device
        print('[Error] Unable to find the Arduino. Check the USB connection and try again.')
        time.sleep(5)
        sys.exit()

    def _read_loop(self):
        while not self._stop:
            try:
                line = self.serial_port.readline().decode(errors='ignore').strip()
                if line:
                    self.last_line = line
            except serial.SerialException:
                break

    def close(self):
        self._stop = True
        if self.serial_port:
            self.serial_port.close()

    def __del__(self):
        self.close()


class TriggerBot:
    def __init__(self, game_window, template_file=None):
        self.game_window = game_window
        self.telemetry = MouseTelemetryReader()
        self.mouse = Controller()
        self.sct = mss.mss()
        self.scale = 2
        self.min_distance = 30
        self.fire_cooldown = 0.25
        self.center_x = self.game_window['width'] // 2
        self.center_y = self.game_window['height'] // 2
        self.template = self.get_template(template_file) if template_file else None
        self._last_fire = 0.0

    def __del__(self):
        if hasattr(self, 'telemetry'):
            del self.telemetry
        if hasattr(self, 'sct'):
            del self.sct

    def get_screenshot(self):
        return np.array(self.sct.grab(self.game_window))

    def get_template(self, template_file):
        template_img = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
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

    def is_on_crosshair(self, target):
        x, y = target
        distance = ((x - self.center_x) ** 2 + (y - self.center_y) ** 2) ** 0.5
        return distance <= self.min_distance

    def run(self):
        while True:
            try:
                img = self.get_screenshot()
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                scaled_gray = cv2.resize(gray, (0, 0), fx=self.scale, fy=self.scale)
                target = self.find_target(scaled_gray)
                now = time.time()
                if (target is not None
                        and self.is_on_crosshair(target)
                        and now - self._last_fire > self.fire_cooldown):
                    self.mouse.click(Button.left)
                    self._last_fire = now
            except Exception as e:
                print(e)
            time.sleep(0.01)


if __name__ == '__main__':
    game_window = mss.mss().monitors[1]
    template_file = sys.argv[1] if len(sys.argv) > 1 else None
    if template_file is None:
        print('[Info] No template image given; pass one as an argument: python aimbot.pyw <template.png>')
    bot = TriggerBot(game_window, template_file)
    bot.run()
