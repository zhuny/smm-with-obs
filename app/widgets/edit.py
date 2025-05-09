from PySide6.QtGui import QIntValidator
from PySide6.QtWidgets import QLabel, QLineEdit


class InputPair:
    def __init__(self, name, title, *, is_number=False, is_password=False):
        self.name = name
        self.title = title
        self.is_number = is_number
        self.is_password = is_password

        from app.widgets.canvas import MyWidget
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
