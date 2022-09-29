# -*- coding: utf-8 -*-
from curses import window
import numpy as np
from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QScrollArea, 
    QLabel, 
)
from PyQt6.QtCore import (
    pyqtSignal, 
)
from . import data_window as dw
from . import popups

class DataArea(QScrollArea):
    data_min_w = 350
    info_w = 150
    data_info_h = 200
    min_h = 550
    margin = 1
    def __init__(self, *args, **kwargs):
        self.image_on = kwargs.get("image_on", False)
        if self.image_on:
            width_factor = 3
        else:
            width_factor = 2
        self.min_w = self.data_min_w * width_factor + self.info_w
        super().__init__()
        # main widgets
        self.chromatogram_layout = ChromatogramLayout(data_area=self)
        self.spectrum_layout = SpectrumLayout(data_area=self)
        self.mz_RT_image_layout = MzRTImageLayout(data_area=self)
        self.info_layout = InfoLayout(data_area=self)
        self.setMinimumSize(self.min_w, self.min_h + self.margin * 2)
        # scroll
        scroll_widget = QWidget()
        scroll_widget.setLayout(QHBoxLayout())
        scroll_widget.layout().setContentsMargins(0,0,0,0)
        scroll_widget.layout().setSpacing(0)
        scroll_widget.layout().addLayout(self.chromatogram_layout)
        scroll_widget.layout().addLayout(self.spectrum_layout)
        if self.image_on:
            scroll_widget.layout().addLayout(self.mz_RT_image_layout)
        scroll_widget.layout().addLayout(self.info_layout)
        self.setWidgetResizable(True)
        self.setWidget(scroll_widget)
        self.horizontalScrollBar().setEnabled(False)
    def add_row(self, N_data=1):
        for i in range(N_data):
            self.chromatogram_layout.add_window()
            self.spectrum_layout.add_window()
            self.mz_RT_image_layout.add_window()
            self.info_layout.add_window()
    def set_spectrum_window_type(self, spectrum_type, index):
        self.spectrum_layout.window_at(index).set_window_type(spectrum_type)
    # get info
    def get_view_range_s(self, ref_index):
        return self.spectrum_layout.window_at(ref_index).viewRange()
    def get_view_range_c(self, ref_index):
        return self.chromatogram_layout.window_at(ref_index).viewRange()
    def get_image_contrast_all(self):
        inten_min = np.inf
        inten_max = 0
        for mz_RT_image_window in self.mz_RT_image_layout:
            min, max = mz_RT_image_window.get_intensity_min_max()
            if min < inten_min:
                inten_min = min
            if max > inten_max:
                inten_max = max
        return inten_min, inten_max
    # updators for data
    def update_chromatograms(self, chromatograms):
        for i, chromatogram in enumerate(chromatograms):
            self.chromatogram_layout.update_chromatogram_at(i, chromatogram)
    def update_spectra(self, spectra):
        for i, spectrum in enumerate(spectra):
            self.spectrum_layout.update_spectrum_at(i, spectrum)
    def update_info_all(self, info_all):
        for i, info in enumerate(info_all):
            self.info_layout.update_info_at(i, info)
    def update_chromatogram(self, chromatogram, index):
        self.chromatogram_layout.window_at(index).update_chromatogram(chromatogram)
    def update_spectrum(self, spectrum, index):
        self.spectrum_layout.window_at(index).update_spectrum(spectrum)
    def update_mz_RT_image(self, rpd, index):
        if self.image_on:
            self.mz_RT_image_layout.window_at(index).update_mz_RT_image(rpd)
        else:
            self.mz_RT_image_layout.window_at(index).update_mz_RT_image_pseudo(rpd)
    def update_info(self, info, index):
        self.info_layout.window_at(index).update_info(info)
    # updators for regions
    def update_mz_regions(self, mz_btm, mz_top):
        for spectrum_window in self.spectrum_layout:
            spectrum_window.update_mz_region(mz_btm, mz_top)
    def update_RT_regions(self, RT_btm, RT_top):
        for chromatogram_window in self.chromatogram_layout:
            chromatogram_window.update_RT_region(RT_btm, RT_top)
    def set_mz_regions_visible(self, visible):
        for spectrum_window in self.spectrum_layout:
            spectrum_window.set_mz_region_visible(visible)
    def set_mz_region_visible(self, visible, index):
        self.spectrum_window.window_at(index).set_mz_region_visible(visible)
    def update_mz_region(self, mz_btm, mz_top, index):
        self.spectrum_layout.window_at(index).update_mz_region(mz_btm, mz_top)
    def update_RT_region(self, RT_btm, RT_top, index):
        self.chromatogram_layout.window_at(index).update_RT_region(RT_btm, RT_top)
    def set_mz_region_visible(self, visible, index):
        self.spectrum_layout.window_at(index).set_mz_region_visible(visible)
    # view range from buttons
    def set_view_range_s_y_link(self, ref_index):
        x_view_range, y_view_range = self.spectrum_layout.window_at(ref_index).viewRange()
        target_index_list = list(range(len(self.spectrum_layout)))
        target_index_list.remove(ref_index)
        for target_index in target_index_list:
            self.spectrum_layout.window_at(target_index).setYRange(*y_view_range, padding=0)
        return y_view_range
    def set_view_range_c_y_link(self, ref_index):
        x_view_range, y_view_range = self.chromatogram_layout.window_at(ref_index).viewRange()
        target_index_list = list(range(len(self.chromatogram_layout)))
        target_index_list.remove(ref_index)
        for target_index in target_index_list:
            self.chromatogram_layout.window_at(target_index).setYRange(*y_view_range, padding=0)
        return y_view_range
    def set_view_range_s_y_auto(self, ref_index):
        for spectrum_window in self.spectrum_layout:
            spectrum_window.setMyYRange_within_x_view_range()
    def set_view_range_c_y_auto(self, ref_index):
        for chromatogram_window in self.chromatogram_layout:
            chromatogram_window.setMyYRange_within_x_view_range()
    def set_view_range_s_y_link_auto(self):
        # get
        x_view_range, y_view_range = self.spectrum_layout.window_at(0).viewRange()
        y_min = np.nan
        y_max = np.nan
        for spectrum_window in self.spectrum_layout:
            y_min_tmp, y_max_tmp = spectrum_window.get_displayed_y_bounds_plot0(*x_view_range)
            if y_min_tmp is None:   # 表示すべきものがない場合
                continue
            if not (y_min <= y_min_tmp):
                y_min = y_min_tmp
            if not (y_max_tmp <= y_max):
                y_max = y_max_tmp
        if not np.isnan(y_min):   # 表示すべきものがある場合
            # set
            for spectrum_window in self.spectrum_layout:
                spectrum_window.setMyYRange(y_min, y_max)
        return spectrum_window.viewRange_y()
    def set_view_range_c_y_link_auto(self):
        # get
        x_view_range, y_view_range = self.chromatogram_layout.window_at(0).viewRange()
        y_min = np.nan
        y_max = np.nan
        for chromatogram_window in self.chromatogram_layout:
            y_min_tmp, y_max_tmp = chromatogram_window.get_displayed_y_bounds_plot0(*x_view_range)
            if y_min_tmp is None:   # 表示すべきものがない場合
                continue
            if not (y_min <= y_min_tmp):
                y_min = y_min_tmp
            if not (y_max_tmp <= y_max):
                y_max = y_max_tmp
        if not np.isnan(y_min):   # 表示すべきものがある場合
            # set
            for chromatogram_window in self.chromatogram_layout:
                chromatogram_window.setMyYRange(y_min, y_max)
        return chromatogram_window.viewRange_y()
    def set_image_contrast_auto(self):
        inten_min, inten_max = self.get_image_contrast_all()
        self.set_image_contrast(inten_min, inten_max)
        return inten_min, inten_max
    def reset_X_range_s(self):
        # get
        x_min = np.nan
        x_max = np.nan
        for spectrum_window in self.spectrum_layout:
            x_min_tmp, x_max_tmp = spectrum_window.get_x_bounds_plot0()
            if x_min_tmp is None:   # 表示すべきものがない場合
                continue
            if not (x_min <= x_min_tmp):
                x_min = x_min_tmp
            if not (x_max_tmp <= x_max):
                x_max = x_max_tmp
        if np.isnan(x_min):   # 表示すべきものがない場合
            return
        # set
        for spectrum_window, mz_RT_image_window in zip(self.spectrum_layout, self.mz_RT_image_layout):
            spectrum_window.setXRange(x_min, x_max, padding=0)
            mz_RT_image_window.setYRange(x_min, x_max, padding=0)
        return x_min, x_max
    def reset_X_range_c(self):
        # get
        x_min = np.nan
        x_max = np.nan
        for chromatogram_window in self.chromatogram_layout:
            x_min_tmp, x_max_tmp = chromatogram_window.get_x_bounds_plot0()
            if x_min_tmp is None:   # 表示すべきものがない場合
                continue
            if not (x_min <= x_min_tmp):
                x_min = x_min_tmp
            if not (x_max_tmp <= x_max):
                x_max = x_max_tmp
        if np.isnan(x_min):   # 表示すべきものがない場合
            return
        # set
        for chromatogram_window, mz_RT_image_window in zip(self.chromatogram_layout, self.mz_RT_image_layout):
            chromatogram_window.setXRange(x_min, x_max, padding=0)
            mz_RT_image_window.setXRange(x_min, x_max, padding=0)
        return x_min, x_max
    def set_view_range_s_x(self, x_min, x_max):
        for spectrum_window in self.spectrum_layout:
            spectrum_window.setXRange(x_min, x_max, padding=0)
    def set_view_range_c_x(self, x_min, x_max):
        for chromatogram_window in self.chromatogram_layout:
            chromatogram_window.setXRange(x_min, x_max, padding=0)
    def set_view_range_s_y(self, y_min, y_max):
        for spectrum_window in self.spectrum_layout:
            spectrum_window.setYRange(y_min, y_max, padding=0)
    def set_view_range_c_y(self, y_min, y_max):
        for chromatogram_window in self.chromatogram_layout:
            chromatogram_window.setYRange(y_min, y_max, padding=0)
    def set_view_range_i_mz(self, mz_min, mz_max):
        for mz_RT_image_window in self.mz_RT_image_layout:
            mz_RT_image_window.setYRange(mz_min, mz_max, padding=0)
    def set_view_range_i_RT(self, RT_min, RT_max):
        for mz_RT_image_window in self.mz_RT_image_layout:
            mz_RT_image_window.setXRange(RT_min, RT_max, padding=0)
    def set_image_contrast(self, inten_min, inten_max):
        for mz_RT_image_window in self.mz_RT_image_layout:
            mz_RT_image_window.set_contrast(inten_min, inten_max)
    # autorange (mainly when files are opened)
    def autorange_s_all(self):
        # get
        x_min = np.nan
        x_max = np.nan
        y_min = np.nan
        y_max = np.nan
        for spectrum_window in self.spectrum_layout:
            x_min_tmp, x_max_tmp = spectrum_window.get_x_bounds_plot0()
            y_min_tmp, y_max_tmp = spectrum_window.get_y_bounds_plot0()
            if not (x_min <= x_min_tmp):
                x_min = x_min_tmp
            if not (x_max_tmp <= x_max):
                x_max = x_max_tmp
            if not (y_min <= y_min_tmp):
                y_min = y_min_tmp
            if not (y_max_tmp <= y_max):
                y_max = y_max_tmp
        # set
        for spectrum_window in self.spectrum_layout:
            spectrum_window.setMyRange(x_min, x_max, y_min, y_max)
        return (x_min, x_max), spectrum_window.viewRange_y()
    def autorange_c_all(self):
        # get
        x_min = np.nan
        x_max = np.nan
        y_min = np.nan
        y_max = np.nan
        for chromatogram_window in self.chromatogram_layout:
            x_min_tmp, x_max_tmp = chromatogram_window.get_x_bounds_plot0()
            y_min_tmp, y_max_tmp = chromatogram_window.get_y_bounds_plot0()
            if not (x_min <= x_min_tmp):
                x_min = x_min_tmp
            if not (x_max_tmp <= x_max):
                x_max = x_max_tmp
            if not (y_min <= y_min_tmp):
                y_min = y_min_tmp
            if not (y_max_tmp <= y_max):
                y_max = y_max_tmp
        # set
        for chromatogram_window in self.chromatogram_layout:
            chromatogram_window.setMyRange(x_min, x_max, y_min, y_max)
        return (x_min, x_max), chromatogram_window.viewRange_y()
    def set_view_range_s_x_all(self, ref_index):
        x_view_range, y_view_range = self.spectrum_layout.window_at(ref_index).viewRange()
        target_index_list = list(range(len(self.spectrum_layout)))
        target_index_list.remove(ref_index)
        for target_index in target_index_list:
            self.spectrum_layout.window_at(target_index).setXRange(*x_view_range, padding=0)
        return x_view_range
    def set_view_range_c_x_all(self, ref_index):
        x_view_range, y_view_range = self.chromatogram_layout.window_at(ref_index).viewRange()
        target_index_list = list(range(len(self.chromatogram_layout)))
        target_index_list.remove(ref_index)
        for target_index in target_index_list:
            self.chromatogram_layout.window_at(target_index).setXRange(*x_view_range, padding=0)
        return x_view_range

class MyLayout(QVBoxLayout):
    window_clicked = pyqtSignal(float, float, object)  # x_value, y_value, window
    range_change_finished = pyqtSignal(float, float, object)  # x_min, x_min, window
    range_changed = pyqtSignal(float, float, object)
    view_range_changed = pyqtSignal(object)
    def __init__(self, data_area, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setContentsMargins(0,0,0,0)
        self.setSpacing(0)
        self.addStretch(1)
        self.data_area = data_area
    # allow both positive and negative index
    def negative_index(self, index):
        if index < 0:
            index = self.count() + index - 1    # because the last item is "stretch".
        return index
    def window_at(self, index): # allow negative indexing
        index = self.negative_index(index)
        return self.itemAt(index).widget()
    def get_window_index(self, window):
        for i, w in enumerate(self):
            if w == window:
                return i
        else:
            return -1
    def __iter__(self):
        self._i = 0
        self._max = self.count() - 2    # because the last item is "stretch".
        return self
    def __next__(self):
        if self._i > self._max: raise StopIteration
        self._i += 1
        return self.itemAt(self._i - 1).widget()
    def __len__(self):
        return self.count() - 1 # because the last item is "stretch".

class ChromatogramLayout(MyLayout):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
    def add_window(self):
        chromatogram_window = dw.ChromatogramWindow()
        chromatogram_window.setFixedHeight(self.data_area.data_info_h)
        self.insertWidget(self.count() - 1, chromatogram_window)
        # event connect
        chromatogram_window.view_box_clicked.connect(
            lambda x_value, y_value: self.window_clicked.emit(x_value, y_value, chromatogram_window))
        chromatogram_window.region0.sigRegionChangeFinished.connect(
            lambda RT_range: self.range_change_finished.emit(*RT_range.getRegion(), chromatogram_window))
        chromatogram_window.region0.sigRegionChanged.connect(
            lambda RT_range: self.range_changed.emit(*RT_range.getRegion(), chromatogram_window))
        chromatogram_window.sigRangeChanged.connect(
            lambda chromatogram_window: self.view_range_changed.emit(chromatogram_window))
    def update_chromatogram_at(self, i, chromatogram):
        self.itemAt(i).widget().update_chromatogram(chromatogram)

class SpectrumLayout(MyLayout):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
    def add_window(self):
        spectrum_window = dw.SpectrumWindow()
        spectrum_window.setFixedHeight(self.data_area.data_info_h)
        self.insertWidget(self.count() - 1, spectrum_window)
        # event connect
        spectrum_window.view_box_clicked.connect(
            lambda x_value, y_value: self.window_clicked.emit(x_value, y_value, spectrum_window))
        spectrum_window.region0.sigRegionChangeFinished.connect(
            lambda mz_range: self.range_change_finished.emit(*mz_range.getRegion(), spectrum_window))
        spectrum_window.region0.sigRegionChanged.connect(
            lambda mz_range: self.range_changed.emit(*mz_range.getRegion(), spectrum_window))
        spectrum_window.sigRangeChanged.connect(
            lambda spectrum_window: self.view_range_changed.emit(spectrum_window))
    def update_spectrum_at(self, i, spectrum):
        self.itemAt(i).widget().update_spectrum(spectrum)

class MzRTImageLayout(MyLayout):
    def __init__(self, data_area, *keys, **kwargs):
        super().__init__(data_area, *keys, **kwargs)
    def add_window(self):
        mz_RT_image_window = dw.MzRTImageWindow()
        mz_RT_image_window.setFixedHeight(self.data_area.data_info_h)
        self.insertWidget(self.count() - 1, mz_RT_image_window)
        # event connect
        mz_RT_image_window.view_box_clicked.connect(
            lambda x_value, y_value: self.window_clicked.emit(x_value, y_value, mz_RT_image_window))
        mz_RT_image_window.sigRangeChanged.connect(
            lambda mz_RT_image_window: self.view_range_changed.emit(mz_RT_image_window))

class InfoLayout(MyLayout):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
    def add_window(self):
        info_window = dw.InfoWindow()
        info_window.setFixedWidth(self.data_area.info_w)
        info_window.setFixedHeight(self.data_area.data_info_h)
        info_window.setStyleSheet("QWidget{background: #FFFFFF}")
        self.insertWidget(self.count() - 1, info_window)
    def update_info_at(self, i, info):
        self.itemAt(i).widget().update_info(info)










