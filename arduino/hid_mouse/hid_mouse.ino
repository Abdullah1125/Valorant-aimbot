// For a native-USB board only (Arduino Leonardo / Pro Micro / Micro -
// anything with an ATmega32U4). Presents itself to the PC as a genuine
// second USB mouse. Reads commands from Serial (sent by aimbot.pyw):
//   move <dx> <dy>   - relative HID mouse movement (any integer size;
//                      split internally into small steps since a single
//                      USB HID report only carries -127..127 per axis)
//   click            - a real HID left-click
#include <Mouse.h>

const int MAX_STEP = 20;

void moveBy(int dx, int dy) {
  while (dx != 0 || dy != 0) {
    int stepX = constrain(dx, -MAX_STEP, MAX_STEP);
    int stepY = constrain(dy, -MAX_STEP, MAX_STEP);
    Mouse.move(stepX, stepY, 0);
    dx -= stepX;
    dy -= stepY;
    delay(1);
  }
}

void setup() {
  Serial.begin(9600);
  Mouse.begin();
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line == "click") {
      Mouse.click(MOUSE_LEFT);
    } else if (line.startsWith("move ")) {
      int spaceIdx = line.indexOf(' ', 5);
      if (spaceIdx > 0) {
        int dx = line.substring(5, spaceIdx).toInt();
        int dy = line.substring(spaceIdx + 1).toInt();
        moveBy(dx, dy);
      }
    }
  }
}
