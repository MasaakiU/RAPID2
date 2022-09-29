# -*- coding: utf-8 -*-

import numpy as np
from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QSpinBox, 
    QLabel, 
    QAbstractSpinBox, 
    QPushButton, 
)
from PyQt6.QtCore import (
    pyqtSignal, 
    Qt, 
)
from PyQt6.QtGui import (
    QIcon, 
    QFocusEvent
)

from ..import general_functions as gf
from . import my_widgets as mw

class NavigationBar(QWidget):
    margin = 5
    btn_width = 27
    # signal
    mz_related_box_changed = pyqtSignal(float, float)   # mz, mz_range
    RT_related_box_changed = pyqtSignal(float, float)   # RT, RT_range
    btn_status_changed_s = pyqtSignal(str, bool)
    btn_status_changed_c = pyqtSignal(str, bool)
    btn_status_changed_i = pyqtSignal(str, bool)
    def __init__(self, *args, **kwargs):
        image_on = kwargs.get("image_on", False)
        super().__init__()
        # spinbox
        self.mz_box = MzSpinBox()
        self.mz_range_box = MzRangeBox()
        self.RT_box = RTSpinBox()
        self.RT_range_box = RTRangeBox()
        self.mz_box.setValue(gf.default_mz_value)
        self.mz_range_box.setValue(gf.default_mz_range)
        self.RT_box.setValue(gf.default_RT_value)
        self.RT_range_box.setValue(gf.default_RT_range)
        # btn_c
        self.btn_linkY_c = mw.MyPushButton()
        self.btn_autoY_c = mw.MyPushButton()
        self.btn_reset_X_range_c = mw.MyPushButton()
        self.btn_linkY_c.setIcons(QIcon(str(gf.settings.btn_icon_path / "link-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "link-solid_white.svg")))
        self.btn_autoY_c.setIcons(QIcon(str(gf.settings.btn_icon_path / "up-down-solid_arrow-down-a-z-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "up-down-solid_arrow-down-a-z-solid_white.svg")))
        self.btn_reset_X_range_c.setIcons(QIcon(str(gf.settings.btn_icon_path / "left-right-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "left-right-solid_white.svg")))
        self.btn_linkY_c.setFixedWidth(self.btn_width)
        self.btn_autoY_c.setFixedWidth(self.btn_width)
        self.btn_reset_X_range_c.setFixedWidth(self.btn_width)
        self.btn_linkY_c.setToolTip("Link Y")
        self.btn_autoY_c.setToolTip("Auto Y")
        self.btn_reset_X_range_c.setToolTip("Reset X Range")
        self.btn_linkY_c.setCheckable(True)
        self.btn_autoY_c.setCheckable(True)
        self.btn_linkY_c.setChecked(True)
        self.btn_autoY_c.setChecked(True)
        # btn_s
        self.btn_TIC = BtnTIC()
        self.btn_TIC.setChecked(True)
        self.btn_linkY_s = mw.MyPushButton()
        self.btn_autoY_s = mw.MyPushButton()
        self.btn_reset_X_range_s = mw.MyPushButton()
        self.btn_linkY_s.setIcons(QIcon(str(gf.settings.btn_icon_path / "link-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "link-solid_white.svg")))
        self.btn_autoY_s.setIcons(QIcon(str(gf.settings.btn_icon_path / "up-down-solid_arrow-down-a-z-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "up-down-solid_arrow-down-a-z-solid_white.svg")))
        self.btn_reset_X_range_s.setIcons(QIcon(str(gf.settings.btn_icon_path / "left-right-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "left-right-solid_white.svg")))
        self.btn_linkY_s.setFixedWidth(self.btn_width)
        self.btn_autoY_s.setFixedWidth(self.btn_width)
        self.btn_reset_X_range_s.setFixedWidth(self.btn_width)
        self.btn_linkY_s.setToolTip("Link Y")
        self.btn_autoY_s.setToolTip("Auto Y")
        self.btn_reset_X_range_s.setToolTip("Reset X Range")
        self.btn_linkY_s.setCheckable(True)
        self.btn_autoY_s.setCheckable(True)
        self.btn_linkY_s.setChecked(True)
        self.btn_autoY_s.setChecked(True)
        # image
        self.btn_reset_XY_range_i = mw.MyPushButton()
        self.btn_reset_XY_range_i.setIcons(QIcon(str(gf.settings.btn_icon_path / "up-right-and-down-left-from-center-solid_mod.svg")), QIcon(str(gf.settings.btn_icon_path / "up-right-and-down-left-from-center-solid_mod_white.svg")))
        self.btn_reset_XY_range_i.setFixedWidth(self.btn_width)
        self.btn_auto_contrast_i = BtnAutoContrast()
        self.btn_auto_contrast_i.setChecked(True)
        # disabled (no files to display) or enabled
        self.is_bar_enabled = None
        self.set_bar_enable(False)

        ##########
        # LAYOUT #
        ##########
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(self.margin, self.margin, self.margin, self.margin)
        self.layout().setSpacing(self.margin)
        # self.layout().addStretch(1)
        # RT
        self.layout().addWidget(QLabel("RT [min]:"))
        self.layout().addWidget(self.RT_box)
        self.layout().addWidget(QLabel("±"))
        self.layout().addWidget(self.RT_range_box)
        self.layout().addWidget(self.btn_linkY_c)
        self.layout().addWidget(self.btn_autoY_c)
        self.layout().addWidget(self.btn_reset_X_range_c)
        self.layout().addStretch(2)
        # mz
        self.layout().addWidget(self.btn_TIC)
        self.layout().addWidget(QLabel("m/z:"))
        self.layout().addWidget(self.mz_box)
        self.layout().addWidget(QLabel("±"))
        self.layout().addWidget(self.mz_range_box)
        self.layout().addWidget(self.btn_linkY_s)
        self.layout().addWidget(self.btn_autoY_s)
        self.layout().addWidget(self.btn_reset_X_range_s)
        self.layout().addStretch(2)
        # mz_RT_image
        if image_on:
            self.layout().addWidget(self.btn_reset_XY_range_i)
            self.layout().addWidget(self.btn_auto_contrast_i)
            self.layout().addStretch(1)
        # イベントコネクト
        self.mz_box.valueChanged.connect(lambda mz: self.mz_related_box_changed.emit(mz, self.mz_range_box.value()))
        self.RT_box.valueChanged.connect(lambda RT: self.RT_related_box_changed.emit(RT, self.RT_range_box.value()))
        self.mz_range_box.valueChanged.connect(lambda mz_range: self.mz_related_box_changed.emit(self.mz_box.value(), mz_range))
        self.RT_range_box.valueChanged.connect(lambda RT_range: self.RT_related_box_changed.emit(self.RT_box.value(), RT_range))
        self.btn_TIC.clicked.connect(lambda is_checked: self.btn_status_changed_c.emit("TIC", is_checked))  # update chromatogram
        self.btn_linkY_s.clicked.connect(lambda is_checked: self.btn_status_changed_s.emit("linkY_s", is_checked))
        self.btn_autoY_s.clicked.connect(lambda is_checked: self.btn_status_changed_s.emit("autoY_s", is_checked))
        self.btn_linkY_c.clicked.connect(lambda is_checked: self.btn_status_changed_c.emit("linkY_c", is_checked))
        self.btn_autoY_c.clicked.connect(lambda is_checked: self.btn_status_changed_c.emit("autoY_c", is_checked))
        self.btn_reset_X_range_s.clicked.connect(lambda is_checked: self.btn_status_changed_s.emit("reset_X_range_s", is_checked))
        self.btn_reset_X_range_c.clicked.connect(lambda is_checked: self.btn_status_changed_c.emit("reset_X_range_c", is_checked))
        self.btn_reset_XY_range_i.clicked.connect(lambda is_checked: self.btn_status_changed_i.emit("reset_XY_range_i", is_checked))
        self.btn_auto_contrast_i.clicked.connect(lambda is_checked: self.btn_status_changed_i.emit("auto_contrast_i", is_checked))
    def set_bar_enable(self, enable):
        self.RT_box.setEnabled(enable)
        self.RT_range_box.setEnabled(enable)
        self.btn_linkY_s.setEnabled(enable)
        self.btn_linkY_c.setEnabled(enable)
        self.btn_autoY_c.setEnabled(enable)
        self.btn_autoY_s.setEnabled(enable)
        self.btn_reset_X_range_c.setEnabled(enable)
        self.btn_reset_X_range_s.setEnabled(enable)
        self.btn_TIC.setEnabled(enable)
        self.enable_mz_related_box(not self.is_TIC())
        self.btn_reset_XY_range_i.setEnabled(enable)
        self.btn_auto_contrast_i.setEnabled(enable)
        self.is_bar_enabled = enable
    def enable_mz_related_box(self, enable):
        self.mz_box.setEnabled(enable)
        self.mz_range_box.setEnabled(enable)
    def is_TIC(self):
        return self.btn_TIC.isChecked()
    def set_mz(self, mz, mz_range=None):
        self.mz_box.setValue(mz)
        if mz_range is not None:
            self.mz_range_box.setValue(mz_range)
    def set_RT(self, RT, RT_range=None):
        self.RT_box.setValue(RT)
        if RT_range is not None:
            self.RT_range_box.setValue(RT_range)
    def get_mz_info(self):
        return self.mz_box.value(), self.mz_range_box.value()
    def get_RT_info(self):
        return self.RT_box.value(), self.RT_range_box.value()
    def get_mz_top_bottom(self):
        mz_btm = self.mz_box.value() - self.mz_range_box.value()
        mz_top = self.mz_box.value() + self.mz_range_box.value()
        return mz_btm, mz_top
    def get_RT_top_bottom(self):
        RT_btm = self.RT_box.value() - self.RT_range_box.value()
        RT_top = self.RT_box.value() + self.RT_range_box.value()
        return RT_btm, RT_top
    def get_y_scale_status_s(self):
        return f"L{int(self.btn_linkY_s.isChecked())}A{int(self.btn_autoY_s.isChecked())}_s"
    def get_y_scale_status_c(self):
        return f"L{int(self.btn_linkY_c.isChecked())}A{int(self.btn_autoY_c.isChecked())}_c"
    def get_contrast_status_i(self):
        if self.btn_auto_contrast_i.isChecked():
            return "auto" 
        else:
            return "manual"

class BtnAutoContrast(mw.MyPushButton):
    def __init__(self):
        super().__init__()
        self.setIcons(QIcon(str(gf.settings.btn_icon_path / "circle-half-stroke-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "circle-half-stroke-solid_white.svg")))
        self.setFixedWidth(NavigationBar.btn_width)
        self.setToolTip("auto contrast")
        self.setCheckable(True)

class BtnTIC(mw.MyPushButton):
    def __init__(self):
        super().__init__()
        self.setIcons(QIcon(str(gf.settings.btn_icon_path / "t-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "t-solid_white.svg")))
        self.setFixedWidth(NavigationBar.btn_width)
        self.setToolTip("TIC")
        self.setCheckable(True)

class MySpinBox(QDoubleSpinBox):
    mz_decimal = 4
    mz_max_value = 999999
    RT_decimal = 4
    RT_max_value = 999
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self.setKeyboardTracking(False)    # 文字入力が終了して初めてシグナル発火させる
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus) # wheel でフォーカスさせない
    def wheelEvent(self, event):
        event.ignore()

class MzSpinBox(MySpinBox):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setMaximum(self.mz_max_value)
        self.setDecimals(self.mz_decimal)

class MzRangeBox(MySpinBox):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setMaximum(self.mz_max_value / 2)
        self.setDecimals(self.mz_decimal)

class RTSpinBox(MySpinBox):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setMaximum(self.RT_max_value)
        self.setDecimals(self.RT_decimal)

class RTRangeBox(MySpinBox):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setMaximum(self.RT_max_value / 2)
        self.setDecimals(self.RT_decimal)


