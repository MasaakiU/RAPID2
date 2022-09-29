# -*- coding: utf-8 -*-
import numpy as np

from PyQt6.QtWidgets import (
    QWidget, 
    QStyleOption, 
    QStyle, 
    QPushButton, 
    QStyleOption, 
    QStyle, 
    QLabel, 
    QTextEdit, 
    QFrame, 
    QSizePolicy, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QSpinBox, 
    QAbstractSpinBox, 
)
from PyQt6.QtGui import (
    QIcon, 
    QPainter, 
    QFont, 
    QFontMetrics, 
    QFontDatabase, 
    QTextOption, 
    QPalette, 
)
from PyQt6.QtCore import (
    QEvent, 
    Qt, 
    pyqtSignal, 
)
from .. import general_functions as gf

class MyPushButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.normal_icon = None
        self.pressed_icon = None
        self.toggled.connect(self.toggled_)
        self.pressed.connect(self.pressed_)
        self.released.connect(self.released_)
        self.is_pressed = False
        self.ignore_event = False
        self.setMouseTracking(True)
    def setIcons(self, icon0, icon1) -> None:
        self.normal_icon = icon0
        self.pressed_icon = icon1
        if self.isChecked():
            return super().setIcon(self.pressed_icon)
        else:
            return super().setIcon(self.normal_icon)
    def toggled_(self):
        if self.isChecked():
            super().setIcon(self.pressed_icon)
        else:
            super().setIcon(self.normal_icon)
    def pressed_(self):
        self.is_pressed = True
        super().setIcon(self.pressed_icon)
    def released_(self):
        self.is_pressed = False
        if not self.isCheckable():
            super().setIcon(self.normal_icon)
    def mouseMoveEvent(self, ev):
        if self.is_pressed and (not self.isChecked()):
            if self.hitButton(ev.pos()):
                self.setIcon(self.pressed_icon)
            else:
                self.setIcon(self.normal_icon)
        super().mouseMoveEvent(ev)
    def setEnabled(self, enable):
        if enable and self.isChecked():
            self.setIcon(self.pressed_icon)
        else:
            self.setIcon(self.normal_icon)
        super().setEnabled(enable)

class PaintableQWidget(QWidget):
    # サブクラスのバックグラウンドの色を設定するのに、implement する必要がある
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.initFrom(self)
        painter = QPainter(self)
        self.style().drawPrimitive(QStyle.PrimitiveElement.PE_Widget, opt, painter, self)

# font_monospace = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
# font_monospace.setStyleHint(QFont.StyleHint.Monospace)
# boldBigFont = QFont()
# boldBigFont.setBold(True)
# boldBigFont.setPointSize(16)

def get_font(font_type):
    if font_type == "monospace":
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        font.setStyleHint(QFont.StyleHint.Monospace)
    elif font_type == "boldfont":
        font = QFont()
        font.setBold(True)
    else:
        raise Exception(f"unknown font_type: {font_type}")
    return font

# フォント付きラベル
class MyLabel(QTextEdit):
    def __init__(self, text=None, font_type=None):
        super().__init__(text)
        self.setReadOnly(True)
        self.setFrameStyle(QFrame.Shape.NoFrame)
        pal = self.palette()
        pal.setColor(QPalette.ColorRole.Base, Qt.GlobalColor.transparent)
        self.setPalette(pal)
        self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.setWordWrapMode(QTextOption.WrapMode.WrapAnywhere)
        # self.document().contentsChanged.connect(self.sizeChange)
        self.document().documentLayout().documentSizeChanged.connect(self.wrapHeightToContents)
        # font
        if font_type is not None:
            font = get_font(font_type)
            self.setFont(font)

    def wrapHeightToContents(self):
        docHeight = self.document().size().height()
        self.setFixedHeight(int(docHeight))

class RichLabel(QLabel):
    def __init__(self, text=None, font_type=None):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);
        # font
        if font_type is not None:
            font = get_font(font_type)
            self.setFont(font)

class ExpoDoubleSpinBox(QWidget):
    valueChanged = pyqtSignal(float)
    decimal = 4
    def __init__(self):
        super().__init__()
        # Widgets
        self.box_value = QDoubleSpinBox()
        self.box_value.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.box_value.setKeyboardTracking(False)    # 文字入力が終了して初めてシグナル発火させる
        self.box_value.setDecimals(self.decimal)
        self.box_value.setMaximum(10)
        self.box_value.setMinimum(-10)
        self.box_exp = QSpinBox()
        self.box_exp.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.box_exp.setKeyboardTracking(False)    # 文字入力が終了して初めてシグナル発火させる
        self.box_exp.setMinimum(-99)
        # レイアウト
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
        self.layout().addWidget(self.box_value, 1)
        self.layout().addWidget(QLabel("e"))
        self.layout().addWidget(self.box_exp, 1)
        # イベントコネクト
        self.box_value.valueChanged.connect(self.valueChanged_value)
        self.box_exp.valueChanged.connect(self.valueChanged_exp)
    def setValue(self, v):
        if v != 0:
            exp = np.floor(np.log10(abs(v))).astype(int).astype(float)
            value = v / (10 ** exp)
        else:
            exp = 0
            value = 0
        self.box_exp.setValue(int(exp))
        self.box_value.setValue(value)
    def valueChanged_value(self, value):
        self.valueChanged.emit(value * 10 ** self.box_exp.value())
    def valueChanged_exp(self, exp):
        self.valueChanged.emit(self.box_value.value() * 10 ** exp)
    def value(self):
        return self.box_value.value() * 10 ** self.box_exp.value()

