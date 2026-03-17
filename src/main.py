import sys
import os
from PyQt5.QtWidgets import QApplication
from main_window import MainWindow


def main():
    # Ensure config directory exists next to the executable (or script)
    if getattr(sys, 'frozen', False):
        config_dir = os.path.join(os.path.dirname(sys.executable), 'config')
    else:
        config_dir = os.path.join(os.path.dirname(__file__), 'config')

    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    app = QApplication(sys.argv)
    window = MainWindow()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
