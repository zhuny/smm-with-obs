import enum

from app.image import PillowImageWrapper


class DetectorState(enum.Enum):
    WAITING = 1  # 클리어 했는지 대기
    CLEARED = 2  # 클리어 확인, 클리어 결과 창 대기
    RESULT = 3  # 클리어 결과 창 확인, 어디서 클리어 했는지 확인


class Detector:
    def detect(self, screen):
        raise NotImplementedError


class ColorDetector(Detector):
    def __init__(self, color, threshold, mode):
        self.color = color
        self.threshold = threshold
        self.mode = mode

    def detect(self, screen: PillowImageWrapper):
        screen_image = screen.get_by_mode(self.mode)
        histogram = self._split(screen_image.histogram(), 256)
        channel_count = 0
        total_count = 0

        for color, dist in zip(self.color, histogram):
            if color < 0:
                continue

            total_count += self._dist(dist, color)
            channel_count += 1

        total_count *= 100
        threshold = self.threshold * channel_count * screen.total_pixel()

        # threshold 정하기 위한 값 확인 용
        # may_threshold = total_count // (channel_count * screen.total_pixel())
        # print(self, self.color, total_count, may_threshold)

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

    def _split(self, it, size):
        result = []
        for i in it:
            if not (result and len(result[-1]) < size):
                result.append([])
            result[-1].append(i)
        return result


class RGBColorDetector(ColorDetector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, mode='RGBA', **kwargs)


class HueColorDetector(ColorDetector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, mode='HSV', **kwargs)


class ImageDetector(Detector):
    def __init__(self, image):
        self.image = image

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
                RGBColorDetector((254, 215, 0), 95)
            ),
            ActionHandler(
                '어마챌 Easy 클리어',
                DetectorState.CLEARED, DetectorState.WAITING,
                HueColorDetector([121], 50),
                handler=self.clear_endless
            ),
            ActionHandler(
                '어마챌 Normal 클리어',
                DetectorState.CLEARED, DetectorState.WAITING,
                HueColorDetector([58], 50),
                handler=self.clear_endless
            ),
            ActionHandler(
                '어마챌 Expert 클리어',
                DetectorState.CLEARED, DetectorState.WAITING,
                HueColorDetector([22], 50),
                handler=self.clear_endless
            ),
            ActionHandler(
                '어마챌 Super Expert 클리어',
                DetectorState.CLEARED, DetectorState.WAITING,
                HueColorDetector([180], 50),
                handler=self.clear_endless
            ),
            # ActionHandler(
            #     '어마챌 밖에서 클리어',
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
