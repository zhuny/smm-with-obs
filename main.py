import sys

from PySide6 import QtWidgets
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QLineEdit, QLabel, QTextEdit, QFormLayout, QVBoxLayout, QWidget, QGroupBox, QPushButton
import obsws_python as obs
from obsws_python.error import OBSSDKError, OBSSDKRequestError


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

        self.socket: obs.ReqClient | None = None
        self.timeout.connect(self.handle)

    def start_timer(self):
        parent = self.parent()
        if self._connect_to_obs(**parent.get_input_value()):
            parent.push_log("인식 시작")
            self.start(1000)
        elif self.socket is not None:
            self.socket.disconnect()
            self.socket = None
            parent.push_log("연결 해제 - 재시도 필요")

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

    def handle(self):
        pass


if __name__ == "__main__":
    app = QtWidgets.QApplication([])

    widget = MyWidget()
    widget.resize(400, 450)
    widget.show()

    sys.exit(app.exec())
