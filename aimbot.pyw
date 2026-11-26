import serial
import serial.tools.list_ports
import time
import cv2
import numpy as np
import mss
import pytesseract
import sys
from pynput.mouse import Button, Controller


class ArduinoMouse:
    def __init__(self):
        self.serial_port = None
        self.serial_port_name = self.find_serial_port()
        if self.serial_port_name:
            self.serial_port = serial.Serial()
            self.serial_port.baudrate = 9600
            self.serial_port.timeout = 1
            self.serial_port.port = self.serial_port_name
            try:
                self.serial_port.open()
            except serial.SerialException:
                print('[Error] Valorant is already open or serial port in use by another app. Close Valorant and other apps before retrying.')
                time.sleep(5)
                sys.exit()

    def find_serial_port(self):
        port = next((port for port in serial.tools.list_ports.comports() if "Arduino" in port.description), None)
        if port is not None:
            return port.device
        print('[Error] Unable to find serial port or the Arduino device is with different name. Please check its connection and try again.')
        time.sleep(5)
        sys.exit()

    def move(self, x, y):
        command = f'move {x} {y}\n'
        self.serial_port.write(command.encode())

    def click(self, button):
        if button not in ('left', 'right'):
            raise ValueError('Button must be either "left" or "right".')
        command = f'click {button}\n'
        self.serial_port.write(command.encode())

    def close(self):
        if self.serial_port:
            self.serial_port.close()

    def __del__(self):
        self.close()


class Aimbot:
    def __init__(self, game_window, template_file=None):
        self.game_window = game_window
        self.mouse = ArduinoMouse()
        self.sct = mss.mss()
        self.scale = 2
        self.debug = False
        self.font = cv2.FONT_HERSHEY_SIMPLEX
        self.color = (0, 255, 0)
        self.thickness = 2
        self.min_confidence = 50
        self.min_distance = 30
        self.mouse_delay = 0.001
        self.center_x = self.game_window['width'] // 2
        self.center_y = self.game_window['height'] // 2
        self.template = self.get_template(template_file) if template_file else None

    def __del__(self):
        if hasattr(self, 'mouse'):
            del self.mouse
        if hasattr(self, 'sct'):
            del self.sct

    def get_screenshot(self):
        sct_img = self.sct.grab(self.game_window)
        return np.array(sct_img)

    def get_template(self, template_file):
        template_img = cv2.imread(template_file, cv2.IMREAD_GRAYSCALE)
        return cv2.resize(template_img, (0, 0), fx=self.scale, fy=self.scale)

    def find_template(self, template_img, gray_img):
        res = cv2.matchTemplate(gray_img, template_img, cv2.TM_CCOEFF_NORMED)
        loc = np.where(res >= 0.7)
        return loc

    def get_center_of_mass(self, gray_img):
        m = cv2.moments(gray_img)
        if m['m00'] == 0:
            return None
        x = int(m['m10'] / m['m00'])
        y = int(m['m01'] / m['m00'])
        return x, y

    def get_text(self, gray_img):
        return pytesseract.image_to_string(gray_img)

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

    def interpolate_coordinates_from_center(self, point):
        x, y = int(point[0]), int(point[1])
        x_range = abs(x - self.center_x)
        y_range = abs(y - self.center_y)
        max_range = max(x_range, y_range)
        if max_range == 0:
            yield self.center_x, self.center_y
            return
        increment = 1.0 / max_range
        for i in range(max_range):
            progress = increment * i
            new_x = int(self.center_x + progress * (x - self.center_x))
            new_y = int(self.center_y + progress * (y - self.center_y))
            yield new_x, new_y

    def aim_at_target(self, target):
        for rel_x, rel_y in self.interpolate_coordinates_from_center(target):
            self.mouse.move(rel_x, rel_y)
            time.sleep(self.mouse_delay)
        self.mouse.click('left')

    def run(self):
        while True:
            try:
                img = self.get_screenshot()
                gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
                scaled_gray = cv2.resize(gray, (0, 0), fx=self.scale, fy=self.scale)
                target = self.find_target(scaled_gray)
                if target is not None:
                    self.aim_at_target(target)
            except Exception as e:
                print(e)
            time.sleep(self.mouse_delay)


if __name__ == '__main__':
    game_window = mss.mss().monitors[1]
    template_file = sys.argv[1] if len(sys.argv) > 1 else None
    if template_file is None:
        print('[Info] No template image given; pass one as an argument: python aimbot.pyw <template.png>')
    aimbot = Aimbot(game_window, template_file)
    aimbot.run()
