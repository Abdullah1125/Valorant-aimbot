// For a native-USB board only (Arduino Leonardo / Pro Micro / Micro -
// anything with an ATmega32U4). Presents itself to the PC as a genuine
// second USB mouse. Reads "click\n" from Serial (sent by aimbot.pyw)
// and performs a real HID left-click.
#include <Mouse.h>

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
    }
  }
}
