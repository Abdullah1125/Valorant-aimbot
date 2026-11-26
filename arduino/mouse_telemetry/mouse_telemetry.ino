// Reads the real mouse plugged into the USB Host Shield and relays its
// movement/button events to the PC over Serial as plain text lines:
//   mouse <dx> <dy>
//   button left down / button left up
//
// Requires the "USB Host Shield Library 2.0" (circuitsathome) installed
// via the Arduino IDE Library Manager.
#include <hidboot.h>
#include <usbhub.h>

class MouseRptParser : public MouseReportParser
{
protected:
  void OnMouseMove(MOUSEINFO *mi) override;
  void OnLeftButtonUp(MOUSEINFO *mi) override;
  void OnLeftButtonDown(MOUSEINFO *mi) override;
};

void MouseRptParser::OnMouseMove(MOUSEINFO *mi) {
  Serial.print("mouse ");
  Serial.print(mi->dX);
  Serial.print(" ");
  Serial.println(mi->dY);
}

void MouseRptParser::OnLeftButtonDown(MOUSEINFO *mi) {
  Serial.println("button left down");
}

void MouseRptParser::OnLeftButtonUp(MOUSEINFO *mi) {
  Serial.println("button left up");
}

USB Usb;
USBHub Hub(&Usb);
HIDBoot<USB_HID_PROTOCOL_MOUSE> HidMouse(&Usb);
MouseRptParser Prs;

void setup() {
  Serial.begin(9600);
  if (Usb.Init() == -1) {
    Serial.println("[Error] USB Host Shield did not start.");
  }
  delay(200);
  HidMouse.SetReportParser(0, &Prs);
}

void loop() {
  Usb.Task();
}
