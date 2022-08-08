# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
from pathlib import Path
from PyQt6.QtCore import (
    Qt, 
)
from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QHBoxLayout, 
    QGridLayout, 
    QLabel, 
    QLineEdit, 
    QWidget, 
    QCheckBox, 
    QPushButton, 
    QFileDialog, 
    QDoubleSpinBox, 
    QSizePolicy, 
)
from PyQt6.QtGui import (
    QFont, 
)
import pyqtgraph as pg

from .. import general_functions as gf
from ..process import atomic_ratio as ar
from . import data_window as dw
from . import navigation_bar as nb
from . import data_area as da
from . import my_widgets as mw

class ResultsLabel(mw.MyLabel):
    index_w = 3
    mass_number_w = 5
    composition_w = 13
    atomic_mass_w = 15
    padding = ' '
    def __init__(self, text=None, font_type=None):
        super().__init__(text, font_type)
        self.setMinimumWidth(300)
    def update_text(self):
        text = (
            f"{'':{self.padding}<{self.index_w}}"
            f"{'ms#':{self.padding}<{self.mass_number_w}}"
            f"{'composition':{self.padding}<{self.composition_w}}"
            f"{'atomic mass':{self.padding}<{self.atomic_mass_w}}\n"
        )
        for i, (relative_atomic_mass, isotopic_composition, mass_number) in enumerate(zip(
            self.parent().relative_atomic_mass_list, self.parent().isotopic_composition_list, self.parent().mass_number_list)):
            text += (
                f"{i+1:{self.padding}<{self.index_w}}"
                f"{mass_number:{self.padding}<{self.mass_number_w}}"
                f"{isotopic_composition:11.10f}  "   #:{self.padding}<{self.composition_w}
                f"{relative_atomic_mass:14.10f}\n"  #:{self.padding}<{self.atomic_mass_w}
            )
        self.setText(text)
    def export_csv(self, save_path_csv):
        df = pd.DataFrame()
        df["mass #"] = self.parent().mass_number_list
        df["composition"] = self.parent().isotopic_composition_list
        df["mass"] = self.parent().relative_atomic_mass_list
        df.to_csv(save_path_csv, sep="\t")

class SpectrumWindow(dw.SpectrumWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spectrum_type = "discrete"
        self.setYRange(0, 1.1, padding=0)
    def update_graph(self):
        self.update_spectrum([self.parent().relative_atomic_mass_list, self.parent().isotopic_composition_list])
    def auto_range(self):
        x_btm, x_top = self.get_x_bounds_plot0()
        return self.setMyXRange(x_btm, x_top)
    def line_width_changed(self, value):
        pen = pg.mkPen(width=value, color="#000000")
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        self.plot0.setPen(pen)

class LineWidthSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDecimals(1)
        self.setMaximum(100)
        self.setSingleStep(0.5)

class AtomicRatioCalculator(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Atomic Ratio Calculator")
        self.ignore_event = False
        # データ
        self.relative_atomic_mass_list = np.array([])
        self.isotopic_composition_list = np.array([])
        self.mass_number_list = np.array([])
        # ウィジェット
        self.results_label = ResultsLabel(font_type="monospace")
        self.spectrum_window = SpectrumWindow()
        self.spectrum_window.region0.setVisible(False)
        self.spectrum_window.setFixedHeight(da.DataArea.data_info_h)
        self.spectrum_window.setMinimumWidth(da.DataArea.data_min_w)
        self.formula = QLineEdit()
        self.formula.setPlaceholderText("Formula")
        self.view_rang_mz_btm = nb.MzSpinBox()
        self.view_rang_mz_top = nb.MzSpinBox()
        self.view_rang_mz_btm.setValue(0)
        self.view_rang_mz_top.setValue(1)
        self.auto_view_range = QCheckBox("Auto")
        self.set_auto_view_range(True)
        self.line_width = LineWidthSpinBox()
        self.ckbx_allow_deuterium = QCheckBox("Allow Deuterium Atoms")
        self.deuterium_purity = QDoubleSpinBox()
        self.deuterium_purity.setDecimals(4)
        self.deuterium_purity.setValue(1)
        self.deuterium_purity.setEnabled(False)
        self.btn_export = QPushButton("Export")
        self.btn_export.setDefault(True)
        # レイアウト
        view_range_layout = QHBoxLayout()
        view_range_layout.addWidget(QLabel("View Range"))
        view_range_layout.addWidget(self.view_rang_mz_btm)
        view_range_layout.addWidget(self.view_rang_mz_top)
        view_range_layout.addWidget(self.auto_view_range)
        view_range_layout.addStretch(1)
        view_style_layout = QHBoxLayout()
        view_style_layout.addWidget(QLabel("Line Width"))
        view_style_layout.addWidget(self.line_width)
        view_style_layout.addStretch(1)
        deuterium_layout = QHBoxLayout()
        deuterium_layout.addWidget(self.ckbx_allow_deuterium)
        deuterium_layout.addStretch(1)
        deuterium_purity_layout = QHBoxLayout()
        deuterium_purity_layout.addWidget(QLabel("\tDeuterium Purity"))
        deuterium_purity_layout.addWidget(self.deuterium_purity)
        deuterium_purity_layout.addStretch(1)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_export)
        control_panel = QVBoxLayout()
        control_panel.addWidget(self.formula)
        control_panel.addWidget(self.results_label)
        control_panel.addStretch(1)
        view_panel = QVBoxLayout()
        view_panel.addWidget(self.spectrum_window)
        view_panel.addLayout(view_range_layout)
        view_panel.addLayout(view_style_layout)
        view_panel.addLayout(deuterium_layout)
        view_panel.addLayout(deuterium_purity_layout)
        view_panel.addLayout(btn_layout)
        self.setLayout(QGridLayout())
        self.layout().addLayout(control_panel, 0, 0, 2, 1)
        self.layout().addLayout(view_panel, 0, 1, 1, 1)

        # 機能してない
        self.setSizePolicy(QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding)

        # イベントコネクト
        self.formula.textChanged.connect(self.formula_changed)
        self.auto_view_range.stateChanged.connect(lambda x: self.set_auto_view_range(x==2))
        self.line_width.valueChanged.connect(self.spectrum_window.line_width_changed)
        self.view_rang_mz_btm.valueChanged.connect(lambda mz_btm: self.mz_view_range_changed(mz_btm, self.view_rang_mz_top.value()))
        self.view_rang_mz_top.valueChanged.connect(lambda mz_top: self.mz_view_range_changed(self.view_rang_mz_btm.value(), mz_top))
        self.ckbx_allow_deuterium.stateChanged.connect(lambda x: self.allow_deuterium(x==2))
        self.btn_export.clicked.connect(self.export_svg)
        # 初期化
        self.results_label.update_text()
        self.spectrum_window.update_graph()
        self.line_width.setValue(10)
        self.resize(0, 0)

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
    def formula_changed(self, formula):
        self.relative_atomic_mass_list, self.isotopic_composition_list, self.mass_number_list = ar.e.mass_distribution(ar.Formula(formula), composition_threshold=10**(-9), group_by_mass_number=True)
        self.results_label.update_text()
        self.spectrum_window.update_graph()
        if self.auto_view_range.checkState() == Qt.CheckState.Checked:
            x_btm, x_top = self.spectrum_window.auto_range()
            self.view_rang_mz_btm.setValue(x_btm)
            self.view_rang_mz_top.setValue(x_top)
    @event_process_deco
    def set_auto_view_range(self, enable):
        self.auto_view_range.setChecked(enable)
        self.view_rang_mz_btm.setEnabled(not enable)
        self.view_rang_mz_top.setEnabled(not enable)
    @event_process_deco
    def mz_view_range_changed(self, mz_btm, mz_top):
        self.spectrum_window.setXRange(mz_btm, mz_top, padding=0)

    def allow_deuterium(self, allow):
        self.deuterium_purity.setEnabled(allow)
        if allow:
            ar.set_custom_deuterium_atoms(d_purity=self.deuterium_purity.value())

    def export_svg(self):
        # ポップアップ
        save_path = Path.home() / 'Desktop' / "atomic_ratio.svg"
        save_path_svg, dir_type = QFileDialog.getSaveFileName(self, 'Enter file name', str(save_path), filter="svg (*.svg)")
        if save_path_svg == "":
            return
        self.spectrum_window.export_svg(save_path_svg)
        self.results_label.export_csv(Path(save_path_svg).with_suffix(".csv"))



