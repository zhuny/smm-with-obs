import enum
import functools
from dataclasses import dataclass

from PIL import Image


class DetectorState(enum.Enum):
    WAITING = 1  # 클리어 했는지 대기
    CLEARED = 2  # 클리어 확인, 클리어 결과 창 대기
    RESULT = 3  # 클리어 결과 창 확인, 어디서 클리어 했는지 확인


class Detector:
    def detect(self, screen):
        raise NotImplementedError


@dataclass
class DetectorResult:
    detector: Detector  # final detector
    result: bool


class ColorDetector(Detector):
    def __init__(self, color, threshold):
        self.color = color
        self.threshold = threshold

    def detect(self, screen: Image.Image):
        histogram = screen.histogram()
        red_count = self._dist(histogram[:256], self.color[0])
        green_count = self._dist(histogram[256:512], self.color[1])
        blue_count = self._dist(histogram[512:], self.color[2])
        total_count = (red_count + green_count + blue_count) * 100
        threshold = self.threshold * screen.size[0] * screen.size[1] * 3

        return total_count > threshold

    def _dist(self, histogram, index):
        index_start = index - 3
        index_end = index + 4

        delta = 0

        if index_start < 0:
            delta = -index_start
        elif len(histogram) < index_end:
            delta = len(histogram) - index_end

        index_start += delta
        index_end += delta

        return sum(histogram[index_start:index_end])


class ImageDetector(Detector):
    def __init__(self, image):
        self.image = image

    def detect(self, screen):
        pass


class TrueDetector(Detector):
    def detect(self, screen):
        return True


class TimeoutDetector(Detector):
    def __init__(self, child, timeout):
        self.child = child
        self.timeout = timeout

    def detect(self, screen):
        pass


class NotDetector(Detector):
    def __init__(self, child):
        self.child = child

    def detect(self, screen):
        pass


class ActionHandler:
    def __init__(self, name, source, target, detector, handler=None):
        self.name = name
        self.source = source
        self.target = target
        self.detector = detector
        self.handler = handler
    
    def run(self, screen, root):
        if self.detector.detect(screen):
            if self.handler:
                self.handler(root)
            root.push_log(self.name)
            return True
        return False


class SMM2Detector:
    def __init__(self):
        self.action_detector = [
            ActionHandler(
                '맵 클리어',
                DetectorState.WAITING, DetectorState.CLEARED,
                ColorDetector((254, 215, 0), 95)
            ),
            ActionHandler(  # debuging
                'Clear to Waiting',
                DetectorState.CLEARED, DetectorState.WAITING,
                TrueDetector()
            ),
            # ActionHandler(
            #     '어마챌 Easy 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     ColorDetector((0, 0, 0), 70),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Normal 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     ColorDetector((0, 0, 0), 70),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Expert 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     ColorDetector((0, 0, 0), 70),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Super Expert 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     ColorDetector((0, 0, 0), 70),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 외에서 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     TimeoutDetector(ImageDetector('clear_frame.png'), 3)
            # )
        ]
        self.current_state = DetectorState.WAITING

    def run(self, screen, root):
        for action in self.action_detector:
            if action.source == self.current_state:
                if action.run(screen, root):
                    self.current_state = action.target
                    return True
        return False

    def clear_endless(self, root):
        root.add_clear_number()
