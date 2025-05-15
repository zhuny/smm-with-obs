import sys

from PySide6 import QtWidgets
from PySide6.QtGui import QIcon

from app.installer_util import get_asset
from app.widgets.canvas import MyWidget


def main():
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.setWindowTitle("슈마메2 어마챌 by zhuny")
    widget.setWindowIcon(QIcon(str(get_asset("assets/images/toadette.png"))))
    widget.resize(400, 450)
    widget.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
