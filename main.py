import sys

from PySide6 import QtWidgets

from app.widgets.canvas import MyWidget


def main():
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 450)
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
