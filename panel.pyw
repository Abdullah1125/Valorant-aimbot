import os
import queue
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import mss

from aimbot_core import AimBot, SerialPortNotFoundError, TemplateLoadError


class AimbotPanel:
    def __init__(self, root):
        self.root = root
        root.title("Aimbot Kontrol Paneli")
        root.resizable(False, False)

        self.bot = None
        self.log_queue = queue.Queue()

        self.template_path = tk.StringVar()
        self.min_distance = tk.DoubleVar(value=30)
        self.max_step = tk.DoubleVar(value=40)
        self.aim_gain = tk.DoubleVar(value=1.0)
        self.fire_cooldown = tk.DoubleVar(value=0.25)
        self.status_text = tk.StringVar(value="Durum: Durduruldu")

        self._build_ui()
        self.root.after(100, self._poll_log)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self):
        pad = {'padx': 8, 'pady': 4}

        frm_template = ttk.LabelFrame(self.root, text="Hedef Şablonu")
        frm_template.grid(row=0, column=0, sticky="ew", **pad)
        ttk.Entry(frm_template, textvariable=self.template_path, width=42).grid(row=0, column=0, padx=4, pady=4)
        ttk.Button(frm_template, text="Gözat...", command=self._browse_template).grid(row=0, column=1, padx=4)

        frm_settings = ttk.LabelFrame(self.root, text="Ayarlar")
        frm_settings.grid(row=1, column=0, sticky="ew", **pad)
        self._add_slider(frm_settings, 0, "Min. Mesafe (px)", self.min_distance, 5, 150)
        self._add_slider(frm_settings, 1, "Max Adım (px)", self.max_step, 5, 100)
        self._add_slider(frm_settings, 2, "Aim Gain", self.aim_gain, 0.1, 3.0)
        self._add_slider(frm_settings, 3, "Ateş Bekleme (sn)", self.fire_cooldown, 0.05, 1.0)

        frm_controls = ttk.Frame(self.root)
        frm_controls.grid(row=2, column=0, sticky="ew", **pad)
        self.btn_start = ttk.Button(frm_controls, text="Başlat", command=self._start)
        self.btn_start.grid(row=0, column=0, padx=4)
        self.btn_stop = ttk.Button(frm_controls, text="Durdur", command=self._stop, state="disabled")
        self.btn_stop.grid(row=0, column=1, padx=4)
        ttk.Label(frm_controls, textvariable=self.status_text).grid(row=0, column=2, padx=12)

        frm_log = ttk.LabelFrame(self.root, text="Günlük")
        frm_log.grid(row=3, column=0, sticky="ew", **pad)
        self.log_text = tk.Text(frm_log, width=64, height=12, state="disabled")
        self.log_text.grid(row=0, column=0)
        scrollbar = ttk.Scrollbar(frm_log, command=self.log_text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.config(yscrollcommand=scrollbar.set)

    def _add_slider(self, parent, row, label, var, lo, hi):
        ttk.Label(parent, text=label, width=16).grid(row=row, column=0, sticky="w", padx=4, pady=2)
        value_label = ttk.Label(parent, width=6)
        scale = ttk.Scale(
            parent, from_=lo, to=hi, variable=var, orient="horizontal", length=220,
            command=lambda _v: self._apply_live_settings(),
        )
        scale.grid(row=row, column=1, padx=4)
        value_label.grid(row=row, column=2, padx=4)

        def refresh(*_):
            value_label.config(text=f"{var.get():.2f}")

        var.trace_add("write", refresh)
        refresh()

    def _apply_live_settings(self):
        if self.bot is not None:
            self.bot.min_distance = self.min_distance.get()
            self.bot.max_step = self.max_step.get()
            self.bot.aim_gain = self.aim_gain.get()
            self.bot.fire_cooldown = self.fire_cooldown.get()

    def _browse_template(self):
        path = filedialog.askopenfilename(
            title="Hedef şablonu seç",
            filetypes=[("Görsel dosyaları", "*.png *.jpg *.jpeg *.bmp"), ("Tüm dosyalar", "*.*")],
        )
        if path:
            self.template_path.set(path)

    def _log(self, message):
        self.log_queue.put(message)

    def _poll_log(self):
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state="normal")
                self.log_text.insert("end", message + "\n")
                self.log_text.see("end")
                self.log_text.config(state="disabled")
        except queue.Empty:
            pass
        self.root.after(100, self._poll_log)

    def _set_status(self, text):
        self.root.after(0, lambda: self.status_text.set(text))

    def _set_buttons(self, start_state, stop_state):
        def _apply():
            self.btn_start.config(state=start_state)
            self.btn_stop.config(state=stop_state)
        self.root.after(0, _apply)

    def _start(self):
        if not self.template_path.get():
            messagebox.showwarning("Eksik bilgi", "Önce bir hedef şablonu seçmelisin.")
            return
        if not os.path.isfile(self.template_path.get()):
            messagebox.showerror("Hata", "Seçilen şablon dosyası bulunamadı.")
            return

        self.btn_start.config(state="disabled")
        self.status_text.set("Durum: Başlatılıyor...")
        threading.Thread(target=self._run_bot, daemon=True).start()

    def _run_bot(self):
        try:
            game_window = mss.mss().monitors[1]
            bot = AimBot(game_window, self.template_path.get(), log=self._log)
        except (SerialPortNotFoundError, TemplateLoadError) as e:
            self._log(f"[Hata] {e}")
            self._set_status("Durum: Durduruldu")
            self._set_buttons("normal", "disabled")
            return
        except Exception as e:
            self._log(f"[Hata] Beklenmeyen hata: {e}")
            self._set_status("Durum: Durduruldu")
            self._set_buttons("normal", "disabled")
            return

        self.bot = bot
        self._apply_live_settings()
        self._log("Aimbot başlatıldı.")
        self._set_status("Durum: Çalışıyor")
        self._set_buttons("disabled", "normal")

        bot.run()

        self._log("Aimbot durduruldu.")
        self._set_status("Durum: Durduruldu")
        self._set_buttons("normal", "disabled")
        self.bot = None

    def _stop(self):
        if self.bot is not None:
            self.bot.stop()
        self.btn_stop.config(state="disabled")

    def _on_close(self):
        self._stop()
        self.root.after(300, self.root.destroy)


def main():
    root = tk.Tk()
    AimbotPanel(root)
    root.mainloop()


if __name__ == "__main__":
    main()
