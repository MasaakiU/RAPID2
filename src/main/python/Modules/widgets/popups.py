# -*- coding: utf-8 -*-

from collections import OrderedDict
from PyQt6.QtCore import (
    QCoreApplication, 
    Qt, 
    QThread, 
    QThreadPool, 
    pyqtSignal, 
)
from PyQt6.QtWidgets import (
    QMessageBox, 
    QVBoxLayout, 
    QHBoxLayout, 
    QGridLayout, 
    QDialog, 
    QLabel, 
    QWidget, 
    QTextEdit, 
    QProgressBar, 
    QCheckBox, 
    QPushButton, 
    QFileDialog, 
    QDoubleSpinBox, 
    QComboBox, 
)
from PyQt6.QtGui import (
    QFont, 
)

from .. import general_functions as gf
from . import my_widgets as mw
from . import my_plot_widget as mpw
from . import navigation_bar as nb

class About(QDialog):
    def __init__(self):
        super().__init__()
        widgets = [
            mw.MyLabel(gf.name, font_type="boldfont"), 
            QLabel(f"Version {gf.ver}"), 
            QLabel("Written by MasaakiU")
        ]
        layout = QVBoxLayout()
        for widget in widgets:
            widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(widget)
        self.setLayout(layout)
        self.setFixedSize(self.sizeHint())

class WarningPopup(QMessageBox):
    def __init__(self, message, title=None, p_type="Normal", icon="Warning"):
        super().__init__()
        self.setIcon(getattr(QMessageBox.Icon, icon))
        self.setWindowTitle(title)
        self.setText(message)
        # self.setInformativeText(invalid_str)
        # self.setDetailedText(formula_explanation)
        if p_type == "Normal":  # ok: 1024
            self.setStandardButtons(QMessageBox.StandardButton.Ok)
        elif p_type == "Cancel":    # cancel: 4194304, Yes: 16384
            self.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Yes)
        elif p_type == "Bool":      # No: 65536, Yes: 16384
            self.setStandardButtons(QMessageBox.StandardButton.No | QMessageBox.StandardButton.Yes)
        elif p_type == "Save":      # discard:8388608, cancel: 4194304, Yes: 16384
            self.setStandardButtons(QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save)
            self.setDefaultButton(QMessageBox.StandardButton.Cancel)
        # elif p_type == "Apply":     # reset:67108864, cancel: 4194304, Apply: 33554432
        #     self.setStandardButtons(QMessageBox.Reset | QMessageBox.Cancel | QMessageBox.Apply)
        #     self.setDefaultButton(QMessageBox.Cancel)
        else:
            raise Exception(f"unknown type\n{p_type}")
        # 設定
        p = self.palette()
        p.setColor(self.backgroundRole(), Qt.GlobalColor.transparent)#white)
        self.setPalette(p)
    def setDetailedText(self, string, font_name="Monospace", style_hint=QFont.StyleHint.Courier):
        super().setDetailedText(string)
        if font_name is None:
            return
        for child in self.children():
            # find QTextEdit object of detaile text
            if isinstance(child, QWidget):
                for grand_child in child.children():
                    if isinstance(grand_child, QTextEdit):
                        font = QFont(font_name)
                        font.setStyleHint(style_hint)
                        font.setBold(False)
                        grand_child.setFont(font)

def no_opened_files():
    return WarningPopup(message="There are no opened file.")

def no_target_added():
    return WarningPopup(message="There are no added target.")

def overwrite_warning():
    return WarningPopup(message="The following file(s) will be overwritten.\nDo you want to continue?", p_type="Bool")

class ProgressBar(QWidget):
    finished = pyqtSignal()
    def __init__(self, N_max=None, message="Processing"):
        super().__init__()
        self.pbar = QProgressBar()
        self.pbar.setValue(0)
        # 値
        self.N_done = 0
        self.N_max = N_max
        self.message = message
        threadCount = QThreadPool.globalInstance().maxThreadCount()
        # widgets
        self.description = QLabel()
        self.set_description()
        self.thread_pool_label = QLabel((f"Maximum number of threads: {threadCount}"))
        # レイアウト
        self.resize(300, 100)
        self.setLayout(QVBoxLayout())
        self.layout().addWidget(self.description)
        self.layout().addWidget(self.pbar)
        self.layout().addWidget(self.thread_pool_label)
        # フラッグ
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            # Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
    def set_description(self):
        text = f"{self.message}... {self.N_done} / {self.N_max} finished"
        self.description.setText(text)
    def add(self, v=1):
        self.N_done += v
        self.pbar.setValue(int(self.N_done / self.N_max * 100))
        self.set_description()
        if self.N_done == self.N_max:
            self.description.setText("finishing...")
            self.finished.emit()
            self.close()
            return

class ExportSettings(QMessageBox):
    def __init__(self, dir_path):
        super().__init__()
        self.ignore_event = False
        # checkboxes
        self.ckbx_chromatogram = QCheckBox("Chromatogram")
        self.ckbx_spectrum = QCheckBox("Spectrum")
        self.ckbx_ordered_dict = OrderedDict()
        self.ckbx_ordered_dict["RT m/z labels"] = [QCheckBox(), QCheckBox()]
        self.ckbx_ordered_dict["plus-minus style"] = [QCheckBox(), QCheckBox()]
        self.ckbx_ordered_dict["RT m/z regions"] = [QCheckBox(), QCheckBox()]
        # buttons
        self.btn_browse = QPushButton("Browse")
        p = self.btn_browse.sizePolicy()
        p.setHorizontalStretch(0)
        self.btn_browse.setSizePolicy(p)
        # dir_path
        self.dir_path_label = mw.RichLabel(str(dir_path))
        p = self.dir_path_label.sizePolicy()
        p.setHorizontalStretch(1)
        self.dir_path_label.setSizePolicy(p)
        # custom layout
        self.layout1 = QGridLayout()
        self.layout1.addWidget(self.ckbx_chromatogram, 0, 1)
        self.layout1.addWidget(self.ckbx_spectrum, 0, 2)
        for i, (k, v) in enumerate(self.ckbx_ordered_dict.items()):
            label = QLabel(k)
            self.layout1.addWidget(label, i+1, 0)
            self.layout1.addWidget(v[0], i+1, 1, alignment=Qt.AlignmentFlag.AlignCenter)
            self.layout1.addWidget(v[1], i+1, 2, alignment=Qt.AlignmentFlag.AlignCenter)
            # イベントコネクト
            v[0].stateChanged.connect(self.ckbx_in_grid_changed_c)
            v[1].stateChanged.connect(self.ckbx_in_grid_changed_s)
            if k == "plus-minus style":
                v[0].hide()
                v[1].hide()
                label.hide()
        layout2 = QHBoxLayout()
        layout2.setContentsMargins(0,0,0,0)
        layout2.addWidget(self.btn_browse, stretch=0)
        layout2.addWidget(self.dir_path_label)
        layout3 = QVBoxLayout()
        layout3.addLayout(self.layout1)
        layout3.addLayout(layout2)
        self.layout().addLayout(layout3, 1, 1)
        # QMessageBox default
        self.setText("Image Export Settings")
        self.setStandardButtons(QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Save)
        self.setDefaultButton(QMessageBox.StandardButton.Save)
        # イベントコネクト
        self.btn_browse.clicked.connect(self.btn_browse_clicked)
        self.ckbx_chromatogram.stateChanged.connect(self.ckbx_chromatogram_changed)
        self.ckbx_spectrum.stateChanged.connect(self.ckbx_spectrum_changed)
        self.ckbx_ordered_dict["RT m/z labels"][0].stateChanged.connect(self.ckbx_RT_labels_changed)
        self.ckbx_ordered_dict["RT m/z labels"][1].stateChanged.connect(self.ckbx_mz_labels_changed)
        # set default state
        self.ckbx_chromatogram.setChecked(True)
        self.ckbx_spectrum.setChecked(True)
    def include_mz_RT_labels(self):
        return list(map(lambda x: x.isChecked(), self.ckbx_ordered_dict["RT m/z labels"]))
    def plus_minus_style(self):
        return list(map(lambda x: x.isChecked(), self.ckbx_ordered_dict["plus-minus style"]))
    def include_mz_RT_regions(self):
        return list(map(lambda x: x.isChecked(), self.ckbx_ordered_dict["RT m/z regions"]))
    def btn_browse_clicked(self, ev):
        dir_path = self.dir_path_label.text()
        dir_path, dir_type = QFileDialog.getSaveFileName(self, 'Enter folder name', dir_path, filter="folder (*)")
        if dir_path == "":
            return
        else:
            self.dir_path_label.setText(dir_path)
    def event_process_deco(func):
        def wrapper(self, *keys, **kwargs):
            if self.ignore_event:
                return
            self.ignore_event = True
            res = func(self, *keys, **kwargs)
            self.ignore_event = False
            return res
        return wrapper
    @event_process_deco
    def ckbx_chromatogram_changed(self, state):
        if state == 0:
            state = Qt.CheckState.Unchecked
        elif state == 2:
            state = Qt.CheckState.Checked
        else:
            raise Exception(state)
        self.ckbx_chromatogram.setTristate(False)
        for r in range(1, self.layout1.rowCount()):
            ckbx = self.layout1.itemAtPosition(r, 1).widget()
            ckbx.setCheckState(state)
            if not ckbx.isEnabled():
                ckbx.setEnabled(True)
    @event_process_deco
    def ckbx_spectrum_changed(self, state):
        if state == 0:
            state = Qt.CheckState.Unchecked
        elif state == 2:
            state = Qt.CheckState.Checked
        else:
            raise Exception(state)
        self.ckbx_spectrum.setTristate(False)
        for r in range(1, self.layout1.rowCount()):
            ckbx = self.layout1.itemAtPosition(r, 2).widget()
            ckbx.setCheckState(state)
            if not ckbx.isEnabled():
                ckbx.setEnabled(True)
    @event_process_deco
    def ckbx_in_grid_changed_c(self, state):
        checkstate_list = []
        for r in range(1, self.layout1.rowCount()):
            ckbx = self.layout1.itemAtPosition(r, 1).widget()
            if not ckbx.isEnabled():
                continue
            checkstate_list.append(ckbx.checkState())
        if checkstate_list[1:] == checkstate_list[:-1]:
            self.ckbx_chromatogram.setCheckState(checkstate_list[0])
            self.ckbx_chromatogram.setTristate(False)
        else:
            self.ckbx_chromatogram.setCheckState(Qt.CheckState.PartiallyChecked)
    @event_process_deco
    def ckbx_in_grid_changed_s(self, state):
        checkstate_list = []
        for r in range(1, self.layout1.rowCount()):
            ckbx = self.layout1.itemAtPosition(r, 2).widget()
            if not ckbx.isEnabled():
                continue
            checkstate_list.append(ckbx.checkState())
        if checkstate_list[1:] == checkstate_list[:-1]:
            self.ckbx_spectrum.setCheckState(checkstate_list[0])
            self.ckbx_spectrum.setTristate(False)
        else:
            self.ckbx_spectrum.setCheckState(Qt.CheckState.PartiallyChecked)
    @event_process_deco
    def ckbx_RT_labels_changed(self, state):
        self.ckbx_ordered_dict["plus-minus style"][0].setEnabled(state == 2)
    @event_process_deco
    def ckbx_mz_labels_changed(self, state):
        self.ckbx_ordered_dict["plus-minus style"][1].setEnabled(state == 2)

class ViewRangeSettings(QWidget):
    view_range_changed_c_x = pyqtSignal(float, float)
    view_range_changed_s_x = pyqtSignal(float, float)
    view_range_changed_c_y = pyqtSignal(float, float)
    view_range_changed_s_y = pyqtSignal(float, float)
    contrast_changed_i = pyqtSignal(float, float)
    def __init__(self, *keys, **kwargs):
        image_on = kwargs.get("image_on", False)
        super().__init__()
        self.ignore_event = False
        self.setWindowTitle("View Range Settings")
        # x spinboxes
        self.x_btm_c = nb.RTSpinBox()
        self.x_top_c = nb.RTSpinBox()
        self.x_btm_s = nb.MzSpinBox()
        self.x_top_s = nb.MzSpinBox()
        # y spinboxes
        self.y_btm_c = mw.ExpoDoubleSpinBox()
        self.y_top_c = mw.ExpoDoubleSpinBox()
        self.y_btm_s = mw.ExpoDoubleSpinBox()
        self.y_top_s = mw.ExpoDoubleSpinBox()
        # contrast related
        self.gradient = mpw.MyGradientWidget()
        self.gradient_top = mw.ExpoDoubleSpinBox()
        self.gradient_btm = mw.ExpoDoubleSpinBox()
        self.gradient_graph = mpw.MyGradientGraph()
        # ボタン
        self.btn_close = QPushButton("Close")
        self.btn_close.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.btn_close.setAutoDefault(True)
        # レイアウト
        gridlayout = QGridLayout()
        gridlayout.addWidget(mw.RichLabel("Chromoatograms", font_type="boldfont"), 0, 0, 1, -1)
        gridlayout.addWidget(QLabel("x"), 1, 0)
        gridlayout.addWidget(self.x_btm_c, 1, 1)
        gridlayout.addWidget(self.x_top_c, 1, 2)
        gridlayout.addWidget(QLabel("y"), 2, 0)
        gridlayout.addWidget(self.y_btm_c, 2, 1)
        gridlayout.addWidget(self.y_top_c, 2, 2)
        gridlayout.addWidget(mw.RichLabel("\nSpectra", font_type="boldfont"), 3, 0, 1, -1)
        gridlayout.addWidget(QLabel("x"), 4, 0)
        gridlayout.addWidget(self.x_btm_s, 4, 1)
        gridlayout.addWidget(self.x_top_s, 4, 2)
        gridlayout.addWidget(QLabel("y"), 5, 0)
        gridlayout.addWidget(self.y_btm_s, 5, 1)
        gridlayout.addWidget(self.y_top_s, 5, 2)
        image_layout = QGridLayout()
        image_layout.addWidget(mw.RichLabel("\nm/z-RT Images", font_type="boldfont"), 0, 0, 1, -1)
        image_layout.addWidget(QLabel("contrast type"), 1, 0)
        image_layout.addWidget(self.gradient, 2, 0, 1, -1)
        image_layout.addWidget(QLabel("min"), 3, 0, 1, 1)
        image_layout.addWidget(self.gradient_btm, 3, 1, 1, 1)
        image_layout.addWidget(QLabel("\t"), 3, 2, 1, 1)
        image_layout.addWidget(QLabel("max"), 3, 3, 1, 1)
        image_layout.addWidget(self.gradient_top, 3, 4, 1, 1)
        image_layout.addWidget(self.gradient_graph, 4, 0, 1, -1)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_close)
        self.setLayout(QVBoxLayout())
        self.layout().addLayout(gridlayout)
        if image_on:
            self.layout().addLayout(image_layout)
        self.layout().addStretch(1)
        self.layout().addLayout(btn_layout)
        # イベントコネクト
        self.x_btm_c.valueChanged.connect(lambda v: self.view_range_changed_c_x.emit(v, self.x_top_c.value()))
        self.x_top_c.valueChanged.connect(lambda v: self.view_range_changed_c_x.emit(self.x_btm_c.value(), v))
        self.x_btm_s.valueChanged.connect(lambda v: self.view_range_changed_s_x.emit(v, self.x_top_s.value()))
        self.x_top_s.valueChanged.connect(lambda v: self.view_range_changed_s_x.emit(self.x_btm_s.value(), v))
        self.y_btm_c.valueChanged.connect(lambda v: self.view_range_changed_c_y.emit(v, self.y_top_c.value()))
        self.y_top_c.valueChanged.connect(lambda v: self.view_range_changed_c_y.emit(self.y_btm_c.value(), v))
        self.y_btm_s.valueChanged.connect(lambda v: self.view_range_changed_s_y.emit(v, self.y_top_s.value()))
        self.y_top_s.valueChanged.connect(lambda v: self.view_range_changed_s_y.emit(self.y_btm_s.value(), v))
        self.gradient_btm.valueChanged.connect(self.gradient_value_changed_from_spingox)
        self.gradient_top.valueChanged.connect(self.gradient_value_changed_from_spingox)
        self.gradient_graph.sig_region_changed.connect(self.gradient_value_changed_from_graph)
        self.gradient_graph.sig_region_change_finished.connect(self.gradient_value_change_finished_from_graph)
        self.btn_close.clicked.connect(self.close)
        # フラッグ
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.CustomizeWindowHint |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.WindowCloseButtonHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.enable_input(False)
        size_hint = self.sizeHint()
        size_hint.setWidth(0)
        size_hint.setHeight(0)
        self.resize(size_hint)
    # methods related to complicated events
    def event_process_deco(func):
        def wrapper(self, *keys, **kwargs):
            if self.ignore_event:
                return
            self.ignore_event = True
            res = func(self, *keys, **kwargs)
            self.ignore_event = False
            return res
        return wrapper
    def enable_input(self, enable):
        # x spinboxes
        self.x_btm_c.setEnabled(enable)
        self.x_top_c.setEnabled(enable)
        self.x_btm_s.setEnabled(enable)
        self.x_top_s.setEnabled(enable)
        # y spinboxes
        self.y_btm_c.setEnabled(enable)
        self.y_top_c.setEnabled(enable)
        self.y_btm_s.setEnabled(enable)
        self.y_top_s.setEnabled(enable)
        # mz_RT images
        self.gradient_btm.setEnabled(enable)
        self.gradient_top.setEnabled(enable)
        self.gradient_graph.setEnabled(enable)
    def enable_y_c(self, enable):
        self.y_btm_c.setEnabled(enable)
        self.y_top_c.setEnabled(enable)
    def enable_y_s(self, enable):
        self.y_btm_s.setEnabled(enable)
        self.y_top_s.setEnabled(enable)
    def set_values_s_x(self, x_view_range_s):
        self.x_btm_s.setValue(x_view_range_s[0])
        self.x_top_s.setValue(x_view_range_s[1])
    def set_values_s_y(self, y_view_range_s):
        self.y_btm_s.setValue(y_view_range_s[0])
        self.y_top_s.setValue(y_view_range_s[1])
    def set_values_c_x(self, x_view_range_c):
        self.x_btm_c.setValue(x_view_range_c[0])
        self.x_top_c.setValue(x_view_range_c[1])
    def set_values_c_y(self, y_view_range_c):
        self.y_btm_c.setValue(y_view_range_c[0])
        self.y_top_c.setValue(y_view_range_c[1])
    @event_process_deco
    def set_values_contrast(self, contrast):
        self.gradient_btm.setValue(contrast[0])
        self.gradient_top.setValue(contrast[1])
        self.gradient_graph.setValue(contrast)
        self.gradient_graph.adjust_view_range()
    @event_process_deco
    def gradient_value_changed_from_spingox(self, *keys, **kwargs):
        gradient_btm = self.gradient_btm.value()
        gradient_top = self.gradient_top.value()
        self.gradient_graph.setValue((gradient_btm, gradient_top))
        self.contrast_changed_i.emit(gradient_btm, gradient_top)
        self.gradient_graph.adjust_view_range()
    @event_process_deco
    def gradient_value_changed_from_graph(self, gradient_btm, gradient_top):
        self.gradient_btm.setValue(gradient_btm)
        self.gradient_top.setValue(gradient_top)
    @event_process_deco
    def gradient_value_change_finished_from_graph(self, gradient_btm, gradient_top):
        self.gradient_btm.setValue(gradient_btm)
        self.gradient_top.setValue(gradient_top)
        self.contrast_changed_i.emit(gradient_btm, gradient_top)
    def closeEvent(self, ev):
        ev.ignore()
        self.hide()
        return
        # return super().closeEvent(ev)
