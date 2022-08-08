# -*- coding: utf-8 -*-

from sqlite3 import connect
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QScrollArea, 
    QLabel, 
)
import pyqtgraph as pg
from . import my_plot_widget as mpw
from . import my_widgets as mw
from ..config import style

class SpectrumWindow(mpw.MyPlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.spectrum_type = None
        # items
        self.plot0.setPen(style.main_s_pen())
        self.plot1.setPen(style.red_pen())
    def update_spectrum(self, spectrum):
        if self.spectrum_type == "continuous":
            self.plot0.setData(*spectrum[0])
            self.plot1.setData(*spectrum[1])
        elif self.spectrum_type == "discrete":
            # process discrete data
            mz_list, inten_list = spectrum
            mz_list = np.hstack((mz_list[:, np.newaxis], mz_list[:, np.newaxis])).flatten()
            inten_list = np.hstack((np.zeros((len(inten_list), 1), dtype=float), inten_list[:, np.newaxis])).flatten()
            connection = np.ones_like(mz_list, dtype=int)
            connection[1::2] = 0
            # set data
            self.plot0.setData(x=mz_list, y=inten_list, connect=connection)
        else:
            raise Exception(f"unknown spectrum type\n{self.spectrum_type}")
    def update_mz_region(self, mz_btm, mz_top):
        self.region0.setRegion((mz_btm, mz_top))
    # methods that have no correspondence to ChromatogramLayout
    def set_window_type(self, spectrum_type):   # centroid or profile
        self.spectrum_type = spectrum_type
    def set_mz_region_visible(self, visible):
        self.region0.setVisible(visible)

class ChromatogramWindow(mpw.MyPlotWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # items
        self.plot0.setPen(style.main_c_pen())
        self.plot1.setPen(style.red_pen())
    def update_chromatogram(self, chromatogram):
        self.plot0.setData(*chromatogram[0])
        self.plot1.setData(*chromatogram[1])
    def update_RT_region(self, RT_btm, RT_top):
        self.region0.setRegion((RT_btm, RT_top))

class InfoWindow(mw.PaintableQWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.info = None
        self.scan_settings_label = mw.MyLabel(font_type="monospace")
        self.file_name_label = mw.MyLabel(font_type="monospace")
        # layout
        self.setLayout(QVBoxLayout())
        self.layout().setSpacing(3)
        self.layout().addWidget(self.scan_settings_label)
        self.layout().addWidget(self.file_name_label)
        self.layout().addStretch(1)
    def update_info(self, info):
        self.info = info
        self.scan_settings_label.setText(self.info.get_scan_settings_text(full=False))
        self.file_name_label.setText(self.info.file_path.name)













