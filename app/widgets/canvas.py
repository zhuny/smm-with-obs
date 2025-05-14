import collections
import json
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtWidgets import QVBoxLayout, QWidget, QFormLayout, QPushButton, QTextEdit

from app.widgets.edit import InputPair
from app.widgets.timer import MyTimer


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.create_input_list()
        self.create_start_button()
        self.create_log_edit()

        self.layout = QVBoxLayout(self)
        self.layout.addWidget(self.input_widget)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.screenshot_button)
        self.layout.addWidget(self.log_edit)

    def create_input_list(self):
        # 입력해 줘야 할 내용들
        self.input_list = [
            InputPair("websocket_port", "OBS WebSocket 서버 포트", is_number=True),
            InputPair("websocket_password", "OBS WebSocket 서버 비밀번호", is_password=True),
            InputPair("switch_layer", "스위치 화면 레이어"),
            InputPair("text_layer", "클리어 수 텍스트 레이어"),
            InputPair("smm_clear_number", "클리어 수", is_number=True)
        ]
        self.input_widget = QWidget()
        self.input_layout = QFormLayout(self.input_widget)
        self.input_bind = collections.defaultdict(list)

        for inp in self.input_list:
            inp.parent = self
            self.bind_value(inp.name, inp.update_value)
            self.input_layout.addRow(inp.label, inp.edit)

        self.input_backup = Path("~/.zhuny/backup.json").expanduser()
        self.input_backup.parent.mkdir(exist_ok=True, parents=True)
        if self.input_backup.is_file():
            info = json.loads(self.input_backup.read_text())
            for inp in self.input_list:
                if inp.name in info:
                    inp.update_value(info[inp.name])

    def create_start_button(self):
        self.start_button = QPushButton("OBS 연결")
        self.start_button.clicked.connect(self.handle_start_button)
        self.timer = MyTimer(self)

        self.screenshot_button = QPushButton("스크린샷")
        self.screenshot_button.clicked.connect(self.timer.screenshot)

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

    def update_value(self, name, value):
        for handler in self.input_bind[name]:
            handler(value)

        input_value = self.get_input_value()
        input_value = json.dumps(input_value)
        self.input_backup.write_text(input_value)

    def bind_value(self, name, handler):
        self.input_bind[name].append(handler)
