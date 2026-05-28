import time
from PyQt6.QtCore import QThread, pyqtSignal

class WinKeyMonitor(QThread):
    """Поток для глобального отслеживания зажатия клавиши Win."""
    trigger_window = pyqtSignal()

    def __init__(self, hold_seconds: float = 3.0, check_interval: float = 0.1, parent=None):
        super().__init__(parent)
        self.hold_seconds = hold_seconds
        self.check_interval = check_interval

    def run(self):
        import keyboard
        win_pressed_time = None
        is_triggered = False

        while True:
            if keyboard.is_pressed('left windows') or keyboard.is_pressed('right windows'):
                if win_pressed_time is None:
                    win_pressed_time = time.time()
                elif (time.time() - win_pressed_time > self.hold_seconds) and not is_triggered:
                    self.trigger_window.emit()
                    is_triggered = True
            else:
                win_pressed_time = None
                is_triggered = False
            time.sleep(self.check_interval)