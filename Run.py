import asyncio
import signal
import sys
import traceback

import qasync
from PyQt5.QtWidgets import QApplication

from _internal.LEDWindow import MainWidget


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("LED Controller")

    # One asyncio loop on top of Qt: BLE and GUI share the main thread
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    try:
        window = MainWidget()
        window.show()
        with loop:
            loop.run_forever()
    except Exception:
        print("\n" + "=" * 50)
        print("CRITICAL ERROR:")
        traceback.print_exc()
        print("=" * 50 + "\n")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()