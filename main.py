import sys

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit, QLabel, QTextEdit, QFormLayout, QVBoxLayout, QWidget, QGroupBox, QPushButton


class InputPair:
    def __init__(self, name, title, *, mask=None):
        self.name = name
        self.title = title

        self.label = QLabel(self.title)
        self.edit = QLineEdit()

        if mask:
            self.edit.setInputMask(mask)

    @property
    def value(self):
        return self.edit.text()


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.create_input_list()
        self.create_start_button()
        self.create_log_edit()

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.input_widget)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.log_edit)

    def create_input_list(self):
        # 입력해 줘야 할 내용들
        self.input_list = [
            InputPair("websocket_port", "OBS WebSocket 서버 포트", mask="00000"),
            InputPair("websocket_password", "OBS WebSocket 서버 비밀번호"),
            InputPair("switch_layer", "스위치 화면 레이어"),
            InputPair("text_layer", "클리어 수 텍스트 레이어"),
            InputPair("smm_clear_number", "클리어 수", mask="00000")
        ]
        self.input_widget = QWidget()
        self.input_layout = QFormLayout(self.input_widget)
        for inp in self.input_list:
            self.input_layout.addRow(inp.label, inp.edit)

    def create_start_button(self):
        self.start_button = QPushButton("시작")
        self.start_button.clicked.connect(self.handle_start_button)
        self.timer = MyTimer(self)

    def create_log_edit(self):
        # 출력될 로고
        self.log_edit = QTextEdit(readOnly=True)
        self.log_list = ["프로그램 실행 됨"]
        self.log_edit.setPlainText("\n".join(self.log_list))

    def handle_start_button(self):
        self.timer.start_timer()

    def get_input_value(self):
        return {
            inp.name: inp.value
            for inp in self.input_list
        }

    def push_log(self, msg):
        self.log_list.insert(0, msg)
        self.log_edit.setPlainText("\n".join(self.log_list))


class MyTimer(QTimer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.socket = None
        self.timeout.connect(self.handle)

    def start_timer(self):
        if self.connect_to_obs():
            self.start(1000)

    def connect_to_obs(self):
        return self._connect_to_obs(**self.parent().get_input_value())

    def _connect_to_obs(self, websocket_port, **kwargs):
        parent: MyWidget = self.parent()

        parent.push_log(f"연결 시도 (포트: {websocket_port})")
        return False

    def handle(self):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 450)
    widget.show()

    sys.exit(app.exec())
