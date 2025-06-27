import enum
import math
import re
import time
from dataclasses import dataclass

from PIL import ImageChops, ImageStat

from app.image import PillowImageWrapper
from app.installer_util import get_asset


class DetectorState(enum.Enum):
    WAITING = 1  # 클리어 했는지 대기
    CLEARED = 2  # 클리어 확인, 클리어 결과 창 대기
    RESULT = 3  # 클리어 결과 창 확인, 어디서 클리어 했는지 확인


@dataclass
class DetectorResult:
    is_detected: bool
    percentile: int

    def __bool__(self):
        return self.is_detected


class Detector:
    def detect(self, screen, root) -> DetectorResult:
        raise NotImplementedError

    def _split(self, it, size):
        result = []
        for i in it:
            if not (result and len(result[-1]) < size):
                result.append([])
            result[-1].append(i)
        return result


class OneColorDetector(Detector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.prev_color = None

    def detect(self, screen, root) -> DetectorResult:
        screen_image = screen.get_by_mode('RGBA')
        stat = ImageStat.Stat(screen_image)
        stddev = self._to_stv(stat.stddev)
        if stddev < 50 and self._is_not_black(stat.mean) and self._is_not_similar_prev(stat.mean):
            h = self._to_hex(stat.mean)
            rgb = ', '.join(map(self._int_str, stat.mean[:3]))
            log_text = (
                f'<span>{h} ({stddev:.03})</span>'
                ' <span style="'
                    'display:inline-block; '
                    'width:12px; height:12px; '
                    f'background-color:rgb({rgb}); '
                    'border:1px solid #aaa; '
                    'margin-left:4px;'
                f'">색</span>'
            )
            root.push_log(log_text, is_rich=True)
        self.prev_color = stat.mean

        return DetectorResult(
            is_detected=False,
            percentile=0
        )

    def _int_str(self, v):
        return str(int(v))

    def _to_hex(self, color):
        result = ['#']
        for c in color[:3]:
            result.append(f'{int(c):02x}')
        return ''.join(result)

    def _to_stv(self, value):
        answer = 0
        for v in value:
            answer += v * v
        return math.sqrt(answer)

    def _is_not_black(self, value):
        for v in value[:3]:
            if int(v) > 40:
                return True
        return False

    def _is_not_similar_prev(self, color):
        if self.prev_color is None:
            return True

        diff = 0
        for x, y in zip(self.prev_color, color):
            diff += abs(x - y) ** 2

        return diff > 10


class ColorDetector(Detector):
    def __init__(self, color, threshold, mode, box=None):
        self.color = color
        self.threshold = threshold
        self.mode = mode
        self.box = box

    def detect(self, screen: PillowImageWrapper, root):
        screen_image = screen.get_by_mode(self.mode)
        if self.box:
            screen_image = screen_image.crop(self.box)
        histogram = self._split(screen_image.histogram(), 256)
        total_pixel = screen_image.size[0] * screen_image.size[1]
        channel_count = 0
        total_count = 0

        for color, dist in zip(self.color, histogram):
            if color < 0:
                continue

            total_count += self._dist(dist, color)
            channel_count += 1

        total_count *= 100
        threshold = self.threshold * channel_count * total_pixel

        return DetectorResult(
            is_detected=total_count > threshold,
            percentile=total_count // (channel_count * total_pixel)
        )

    def _dist(self, histogram, index):
        gap = 7
        index_start = index - gap
        index_end = index + gap + 1

        delta = 0

        if index_start < 0:
            delta = -index_start
        elif len(histogram) < index_end:
            delta = len(histogram) - index_end

        index_start += delta
        index_end += delta

        return sum(histogram[index_start:index_end])


class RGBColorDetector(ColorDetector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, mode='RGBA', **kwargs)


class DynamicColorDetector(ColorDetector):
    def __init__(self, key, *args, **kwargs):
        self.key = key

        super().__init__(*args, **kwargs)

    def detect(self, screen: PillowImageWrapper, root):
        info = root.get_input_value()
        self.color = self.convert_text(info.get(self.key, ''))
        return super().detect(screen, root)

    def convert_text(self, value: str):
        raise NotImplementedError(self)


class DynamicRGBColorDetector(DynamicColorDetector, RGBColorDetector):
    def __init__(self, *args, **kwargs):
        super().__init__(color=(0, 0, 0), *args, **kwargs)

    def convert_text(self, value: str):
        one_hex = '[0-9a-f]'
        two_hex = f'({one_hex}{one_hex})'
        color_pattern = '#?' + two_hex * 3
        pattern = re.compile(color_pattern)
        g = pattern.fullmatch(value)
        if g is None:
            return 0, 0, 0

        return tuple(
            int(v, 16)
            for v in g.groups()
        )


class HueColorDetector(ColorDetector):
    def __init__(self, *args, is_endless=True, **kwargs):
        super().__init__(
            *args,
            mode='HSV',
            box=(103, 127, 753, 389) if is_endless else None,  # 어마챌 색을 확인하는 범위
            **kwargs
        )


class ImageDetector(Detector):
    def __init__(self, image_path):
        self.image = PillowImageWrapper.load_from_assets(image_path)

    def detect(self, screen: PillowImageWrapper, root):
        img1 = self.image.get_by_mode('RGBA')
        img2 = screen.get_by_mode('RGBA')

        diff = ImageChops.difference(img1, img2)
        diff_scale = self._average_scale(diff)

        return DetectorResult(
            is_detected=diff_scale < 0.1,
            percentile=int((1 - diff_scale) * 100)
        )

    def _average_scale(self, image):
        total_sum, total_count = 0, 0

        for i, value in enumerate(image.histogram()):
            total_count += value
            total_sum += value * (i % 256)

        return total_sum / total_count / 255


class NotDetector(Detector):
    def __init__(self, child):
        self.child = child

    def detect(self, screen, root):
        return not self.child.detect(screen, root)


class ContinueDetector(Detector):
    def __init__(self, child):
        self.child = child
        self.prev_detected_time = []

    def detect(self, screen, root):
        current_time = time.time()

        if self.child.detect(screen, root):
            prev_detected_time = [
                t
                for t in self.prev_detected_time
                if current_time - 7 < t
            ]
            prev_detected_time.append(current_time)

            result = len(prev_detected_time) > 4
            self.prev_detected_time = prev_detected_time

            return result

        return False


class ActionHandler:
    def __init__(self, name, source, target, detector, handler=None):
        self.name = name
        self.source = source
        self.target = target
        self.detector = detector
        self.handler = handler
    
    def run(self, screen, root):
        detect_result: DetectorResult = self.detector.detect(screen, root)
        if detect_result.is_detected:
            if self.handler:
                self.handler(root)
            root.push_log(self.name)
            return True
        return False


class SMM2Detector:
    def __init__(self):
        self.action_detector = [
            ActionHandler(
                '색확인',
                DetectorState.WAITING, DetectorState.WAITING,
                OneColorDetector()
            ),
            ActionHandler(
                '맵 클리어',
                DetectorState.WAITING, DetectorState.WAITING,
                DynamicRGBColorDetector('clear_yellow', threshold=90),
                handler=self.clear_endless
            )
            # ActionHandler(
            #     '맵 클리어',
            #     DetectorState.WAITING, DetectorState.WAITING,
            #     HueColorDetector((254, 215, 0), 90, is_endless=False)
            # ),
            # ActionHandler(
            #     '어마챌 Easy 클리어 (클수 += 1)',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     HueColorDetector([121], 50),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Normal 클리어 (클수 += 1)',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     HueColorDetector([58], 50),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Expert 클리어 (클수 += 1)',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     HueColorDetector([22], 50),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 Super Expert 클리어 (클수 += 1)',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     HueColorDetector([180], 50),
            #     handler=self.clear_endless
            # ),
            # ActionHandler(
            #     '어마챌 밖에서 클리어',
            #     DetectorState.CLEARED, DetectorState.WAITING,
            #     ContinueDetector(
            #         NotDetector(
            #             ImageDetector(get_asset('assets/images/clear.png'))
            #         )
            #     )
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
