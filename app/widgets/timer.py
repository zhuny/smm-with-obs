import base64
from io import BytesIO

import obsws_python as obs
from PIL import Image
from PySide6.QtCore import QTimer
from obsws_python.error import OBSSDKError, OBSSDKRequestError

from app.detector import SMM2Detector


class MyTimer(QTimer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.socket: obs.ReqClient | None = None
        self.detector = SMM2Detector()
        self.delay = 0

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
        if self.delay > 0:
            self.delay -= 1
            return

        info = self._get_input_value()
        screen_encoded = self.socket.get_source_screenshot(
            info['switch_layer'],
            'png', 960, 540, -1
        )
        image_data = screen_encoded.image_data.split(',', 1)[1]
        screen_data = base64.b64decode(image_data)
        screen = Image.open(BytesIO(screen_data))
        if self.detector.run(screen, self):
            self.delay = 2

    def send_clear_number(self, value):
        info = self._get_input_value()
        self.socket.set_input_settings(
            info['text_layer'],
            {
                'text': f'{value:,}클'
            },
            overlay=True
        )

    def push_log(self, msg):
        self.parent().push_log(msg)

    def _connect_to_obs(self,
                        websocket_port, websocket_password,
                        text_layer, switch_layer,
                        **kwargs):
        parent = self.parent()

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
