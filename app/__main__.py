import argparse
import sys
import traceback

from PyQt6.QtWidgets import QApplication

from .app import Controller
from .gui import MainWindow


def new_excepthook(type, value, tb):
    # by default, Qt does not seem to output any errors, this prevents that
    traceback.print_exception(type, value, tb)


sys.excepthook = new_excepthook


def main():
    parser = argparse.ArgumentParser()

    tuning_keypad = Controller()

    qapp = QApplication(sys.argv)
    gui = MainWindow(tuning_keypad)
    gui.show()
    sys.exit(qapp.exec())


if __name__ == '__main__':
    main()
