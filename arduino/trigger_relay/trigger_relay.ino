// Receives "click\n" over Serial from the PC vision script and pulses
// RELAY_PIN, closing a relay wired in parallel with the real mouse's
// left-click microswitch for CLICK_HOLD_MS milliseconds.
const int RELAY_PIN = 7;
const unsigned long CLICK_HOLD_MS = 60;

void setup() {
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  Serial.begin(9600);
}

void loop() {
  if (Serial.available()) {
    String line = Serial.readStringUntil('\n');
    line.trim();
    if (line == "click") {
      digitalWrite(RELAY_PIN, HIGH);
      delay(CLICK_HOLD_MS);
      digitalWrite(RELAY_PIN, LOW);
    }
  }
}
