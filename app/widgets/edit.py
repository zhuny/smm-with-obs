from PySide6.QtWidgets import QLabel, QLineEdit, QSpinBox


class EditorWrapper:
    def __init__(self, child):
        self.child = child

    def bind(self, handler):
        raise NotImplementedError(self)

    def set_value(self, value):
        raise NotImplementedError(self)

    def get_value(self):
        raise NotImplementedError(self)

    def hide_input(self):
        self.child.setEchoMode(QLineEdit.EchoMode.Password)


class NumberEditor(EditorWrapper):
    def __init__(self):
        box = QSpinBox()
        box.setMaximum(1_000_000)
        box.setMinimum(0)

        super().__init__(box)

    def bind(self, handler):
        self.child.textChanged.connect(handler)

    def set_value(self, value):
        self.child.setValue(int(value))

    def get_value(self):
        return self.child.value()


class TextEditor(EditorWrapper):
    def __init__(self):
        super().__init__(QLineEdit())

    def bind(self, handler):
        self.child.textEdited.connect(handler)

    def get_value(self):
        return self.child.text()

    def set_value(self, value):
        self.child.setText(str(value))


class InputPair:
    def __init__(self, name, title, *, default=None, is_number=False, is_password=False):
        self.name = name
        self.title = title
        self.is_number = is_number
        self.is_password = is_password

        from app.widgets.canvas import MyWidget
        self.parent: MyWidget | None = None

        self.label = QLabel(self.title)
        if self.is_number:
            self.edit_wrap = NumberEditor()
        else:
            self.edit_wrap = TextEditor()

        self.edit_wrap.bind(self.on_edited)

        if is_password:
            self.edit_wrap.hide_input()
        if default:
            self.update_value(default)

    @property
    def value(self):
        return self.edit_wrap.get_value()

    @property
    def edit(self):
        return self.edit_wrap.child

    def update_value(self, value):
        self.edit_wrap.set_value(value)

    def on_edited(self):
        self.parent.update_value(self.name, self.value)
