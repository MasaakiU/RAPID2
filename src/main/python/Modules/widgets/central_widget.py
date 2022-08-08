# -*- coding: utf-8 -*-

import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QScrollArea, 
)

from . import navigation_bar as nb
from . import my_widgets as mw
from . import data_area as da
from . import compound_widget as cw
from . import popups
from .. import general_functions as gf

class CentralWidget(QWidget):
    navigator_height = 33
    def __init__(self, main_window, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.main_window = main_window
        ###########
        # WIDGETS #
        ###########
        self.navigation_bar = nb.NavigationBar()
        self.compound_navigator = cw.CompoundNavigator()
        self.compound_widget = cw.CompoundWidget()
        self.data_area = da.DataArea()
        self.view_range_settings = popups.ViewRangeSettings()
        #########
        # STYLE #
        #########
        self.navigation_bar.setFixedHeight(self.navigator_height)
        self.compound_navigator.setFixedHeight(self.navigator_height)
        ##########
        # LAYOUT #
        ##########
        compound_layout = QVBoxLayout()
        compound_layout.addWidget(self.compound_navigator)
        compound_layout.addWidget(self.compound_widget)
        data_layout = QVBoxLayout()
        data_layout.setContentsMargins(0,0,0,0)
        data_layout.setSpacing(0)
        data_layout.addWidget(self.navigation_bar)
        data_layout.addWidget(self.data_area)
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().setSpacing(0)
        self.layout().addLayout(compound_layout, stretch=0)
        self.layout().addLayout(data_layout, stretch=1)

    def export_svg(self, dir_path, include_mz_RT_labels, include_mz_RT_regions, plus_minus_style):
        save_path_base_list = []
        dict_records = []
        for chromatogram_window, spectrum_window, info_window in zip(self.data_area.chromatogram_layout, self.data_area.spectrum_layout, self.data_area.info_layout):
            save_path_base_pre = (dir_path / info_window.info.file_path.name).with_suffix("")
            if save_path_base_pre.suffix == ".mzdata":
                save_path_base_pre = save_path_base_pre.with_suffix("")
            # 重複チェック
            i = 0
            save_path_base = save_path_base_pre
            while save_path_base in save_path_base_list:
                i += 1
                save_path_base = f"{save_path_base_pre}_{i}"
            save_path_base_list.append(save_path_base)
            # ラベル情報
            if self.navigation_bar.is_TIC():
                mz_range = "TIC"
            else:
                if plus_minus_style[1]:
                    mz_range = "{0:.4f}±{1:.4f}".format(*self.navigation_bar.get_mz_info())
                else:
                    mz_range = "{0:.4f}-{1:.4f}".format(*self.navigation_bar.get_mz_top_bottom())
            if plus_minus_style[0]:
                RT_range = "{0:.4f}±{1:.4f}".format(*self.navigation_bar.get_RT_info())
            else:
                RT_range = "{0:.4f}-{1:.4f}".format(*self.navigation_bar.get_RT_top_bottom())
            dict_records.append({
                "file_path":info_window.info.file_path, 
                "data_hash":info_window.info.data_hash, 
                "scan_settings":info_window.info.scan_settings, 
                "svg_name":save_path_base, 
                "m/z":mz_range, 
                "RT[min]":RT_range
            })
            # 一時的に表示
            if include_mz_RT_labels[0] and include_mz_RT_regions[0]:
                chromatogram_window.set_top_right_label_html(f"mz={mz_range}, RT={RT_range}")
            elif include_mz_RT_labels[0]:
                chromatogram_window.set_top_right_label_html(f"mz={mz_range}")
            if not include_mz_RT_regions[0]:
                chromatogram_window.region0.setVisible(False)
            if include_mz_RT_labels[1] and include_mz_RT_regions[1]:
                spectrum_window.set_top_right_label_html(f"mz={mz_range}, RT={RT_range}")
            elif include_mz_RT_labels[1]:
                spectrum_window.set_top_right_label_html(f"RT={RT_range}")
            if not include_mz_RT_regions[1]:
                spectrum_window.region0.setVisible(False)
            # 保存
            save_path_c = save_path_base.parent / (save_path_base.name + "_c.svg")
            save_path_s = save_path_base.parent / (save_path_base.name + "_s.svg")
            chromatogram_window.export_svg(save_path_c)
            spectrum_window.export_svg(save_path_s)
            # もとに戻す
            if include_mz_RT_labels[0]:
                chromatogram_window.set_top_right_label_html("")
            if include_mz_RT_labels[1]:
                spectrum_window.set_top_right_label_html("")
            if not include_mz_RT_regions[0]:
                chromatogram_window.region0.setVisible(True)
            if not include_mz_RT_regions[1]:
                spectrum_window.region0.setVisible(True)
        # save picture info
        df_info = pd.DataFrame.from_records(dict_records)
        df_info.to_csv(dir_path / f"{dir_path.name}_info.csv", sep="\t")





