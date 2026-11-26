import sys
import mss

from aimbot_core import AimBot, SerialPortNotFoundError, TemplateLoadError


def main():
    game_window = mss.mss().monitors[1]
    template_file = sys.argv[1] if len(sys.argv) > 1 else None
    if template_file is None:
        print('[Info] No template image given; pass one as an argument: python aimbot.pyw <template.png>')
    try:
        bot = AimBot(game_window, template_file)
    except (SerialPortNotFoundError, TemplateLoadError) as e:
        print(f'[Error] {e}')
        sys.exit(1)
    bot.run()


if __name__ == '__main__':
    main()
