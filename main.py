import collections
import json
import sys
from pathlib import Path

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QLineEdit, QLabel, QTextEdit, QFormLayout, QVBoxLayout, QWidget, QGroupBox, QPushButton
import obsws_python as obs
from obsws_python.error import OBSSDKError, OBSSDKRequestError


class InputPair:
    def __init__(self, name, title, *, is_number=False, is_password=False):
        self.name = name
        self.title = title
        self.is_number = is_number
        self.is_password = is_password

        self.parent: MyWidget | None = None

        self.label = QLabel(self.title)
        self.edit = QLineEdit()
        self.edit.textEdited.connect(self.on_edited)

        if is_number:
            self.edit.setValidator(QIntValidator())
        if is_password:
            self.edit.setEchoMode(QLineEdit.EchoMode.Password)

    @property
    def value(self):
        text_or_number = self.edit.text()
        if self.is_number:
            text_or_number = int(text_or_number or 0)
        return text_or_number

    def update_value(self, value):
        self.edit.setText(str(value))

    def on_edited(self):
        self.parent.update_value(self.name, self.value)


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

    def update_value(self, name, value):
        for handler in self.input_bind[name]:
            handler(value)

        input_value = self.get_input_value()
        input_value = json.dumps(input_value)
        self.input_backup.write_text(input_value)

    def bind_value(self, name, handler):
        self.input_bind[name].append(handler)


class MyTimer(QTimer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.socket: obs.ReqClient | None = None
        self.timeout.connect(self.handle)

    def start_timer(self):
        parent = self.parent()
        if self._connect_to_obs(**parent.get_input_value()):
            parent.push_log("인식 시작")
            self.parent().bind_value('smm_clear_number', self.send_clear_number)
            self.start(1000)
        elif self.socket is not None:
            self.socket.disconnect()
            self.socket = None
            parent.push_log("연결 해제 - 재시도 필요")

    def handle(self):
        number = self._get_input_value()['smm_clear_number']
        self.parent().update_value('smm_clear_number', number + 1)

    def send_clear_number(self, value):
        info = self._get_input_value()
        self.socket.set_input_settings(
            info['text_layer'],
            {
                'text': f'{value:,}클'
            },
            overlay=True
        )

    def _connect_to_obs(self,
                        websocket_port, websocket_password,
                        text_layer, switch_layer,
                        **kwargs):
        parent: MyWidget = self.parent()

        parent.push_log(f"연결 시도 (포트: {websocket_port})")
        if self._check_connect_socket(websocket_port, websocket_password):
            parent.push_log("연결 성공")
        else:
            parent.push_log("연결 실패 - 연결 설정 확인 필요")
            return False

        if self._check_obs_source(text_layer):
            parent.push_log(f"OBS 소스({text_layer}) 확인")
        else:
            parent.push_log(f"OBS 소스({text_layer}) 없음 - '클리어 수 텍스트 레이어' 확인 필요")
            return False

        if self._check_obs_source(switch_layer):
            parent.push_log(f"OBS 소스({switch_layer}) 확인")
        else:
            parent.push_log(f"OBS 소스({switch_layer}) 없음 - '스위치 화면 레이어' 확인 필요")
            return False

        return True

    def _check_connect_socket(self, websocket_port, websocket_password):
        try:
            self.socket = obs.ReqClient(
                host="localhost",
                port=websocket_port,
                password=websocket_password
            )
            return True
        except OBSSDKError:
            return False

    def _check_obs_source(self, source_name):
        try:
            self.socket.get_source_active(source_name)
            return True
        except OBSSDKRequestError:
            return False

    def _get_input_value(self):
        return self.parent().get_input_value()


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 450)
    widget.show()

    sys.exit(app.exec())
