# -*- coding: utf-8 -*-

import numpy as np
import pandas as pd
import copy
from ..widgets import popups
from PyQt6.QtCore import (
    QCoreApplication, 
)

class Model():
    def __init__(self, main_window, fast_display):
        self.main_window = main_window
        # the following lists must be synchronyzed
        self.data_hash_list = []
        self.rpd_list = []
        self.fast_display = fast_display
    def database(self):
        return self.main_window.database
    # you can specify what kind of data you want by *key, **kwargs in the future.
    def set_rpd_data_from_database(self, index=None):
        if index is None:
            self.data_hash_list, self.rpd_list = self.database().get_all_rpd_data()
        else:
            data_hash, rpd = self.database().get_rpd_data(index)
            self.data_hash_list.append(data_hash)
            self.rpd_list.append(rpd)
        return len(self.data_hash_list)
    def extract_chromatograms(self, mz_btm, mz_top):
        self.pbar = popups.ProgressBar(N_max=len(self.rpd_list), message="Extracting Chromatograms")
        self.pbar.show()
        chromatograms = []
        for rpd in self.rpd_list:
            if self.fast_display:
                chromatograms.append(rpd.extract_chromatogram_fast(mz_btm, mz_top))
            else:
                chromatograms.append(rpd.extract_chromatogram(mz_btm, mz_top))
            self.pbar.add()
            QCoreApplication.processEvents()
        return chromatograms
    def extract_chromatogram(self, mz_btm, mz_top, index):
        if self.fast_display:
            return self.rpd_list[index].extract_chromatogram_fast(mz_btm, mz_top)
        else:
            return self.rpd_list[index].extract_chromatogram(mz_btm, mz_top)
    def extract_spectra(self, RT_btm, RT_top):
        self.pbar = popups.ProgressBar(N_max=len(self.rpd_list), message="Extracting Spectra")
        self.pbar.show()
        spectra = []
        for rpd in self.rpd_list:
            if self.fast_display:
                spectra.append(rpd.extract_spectrum_fast(RT_btm, RT_top))
            else:
                spectra.append(rpd.extract_spectrum(RT_btm, RT_top))
            self.pbar.add()
            QCoreApplication.processEvents()
        return spectra
    def extract_spectrum(self, RT_btm, RT_top, index):
        if self.fast_display:
            return self.rpd_list[index].extract_spectrum_fast(RT_btm, RT_top)
        else:
            return self.rpd_list[index].extract_spectrum(RT_btm, RT_top)
    def extract_info_all(self):
        return [rpd.extract_info() for rpd in self.rpd_list]
    def extract_info(self, index):
        return self.rpd_list[index].extract_info()
    def export_auc_data(self, data_items):
        auc_data_list = []
        for data_item in data_items:
            print(data_item.compound_name)
            # view_range_s_x
            # view_range_c_x
            RT_btm = data_item.RT - data_item.RT_range
            RT_top = data_item.RT + data_item.RT_range
            if data_item.is_TIC:
                mz_btm = 0
                mz_top = np.inf
            else:
                mz_btm = data_item.mz - data_item.mz_range
                mz_top = data_item.mz + data_item.mz_range
            # calc values
            for rpd in self.rpd_list:
                r = rpd.calc_chromatogram_auc(
                    mz_btm, 
                    mz_top, 
                    RT_btm, 
                    RT_top, 
                    return_BG_subtraction=True, 
                    return_height=True, 
                    return_baseline_height=True, 
                    return_real_RT_range=True
                )
                if r is not None:
                    auc, auc_BG, height, baseline_height, (real_RT_btm, real_RT_top) = r
                else:
                    auc, auc_BG, height, baseline_height, (real_RT_btm, real_RT_top) = np.nan, np.nan, np.nan, np.nan, (np.nan, np.nan)
                new_data_item = data_item.copy()
                new_data_item["file_path"] = rpd.file_path
                new_data_item["file_name"] = rpd.file_path.name
                new_data_item["data_hash"] = rpd.data_hash.decode('ascii')
                new_data_item["scan_settings"] = rpd.extract_info().get_scan_settings_text(full=False)
                new_data_item["mz_btm"] = mz_btm
                new_data_item["mz_top"] = mz_top
                new_data_item["RT_btm"] = RT_btm
                new_data_item["RT_top"] = RT_top
                new_data_item["area"] = auc
                new_data_item["area (baseline adjusted)"] = auc_BG
                new_data_item["height"] = height
                new_data_item["baseline_height"] = baseline_height
                new_data_item["RT_btm (value used for calculation)"] = real_RT_btm
                new_data_item["RT_top (value used for calculation)"] = real_RT_top
                if new_data_item.is_TIC:
                    new_data_item["mz"] = "None"
                    new_data_item["mz_range"] = "None"
                # append
                auc_data_list.append(new_data_item)
        df = pd.DataFrame.from_records(auc_data_list)
        column_order = [
            'compound_name', 
            "formula", 
            'file_path', 
            'file_name', 
            "data_hash", 
            'scan_settings', 
            'is_TIC', 
            'mz', 
            'mz_range', 
            'RT', 
            'RT_range', 
            'mz_btm', 
            'mz_top', 
            'RT_btm', 
            'RT_top', 
            "RT_btm (value used for calculation)", 
            "RT_top (value used for calculation)", 
            'view_range_s_x',
            'view_range_c_x', 
            'area', 
            'area (baseline adjusted)', 
            "height", 
            "baseline_height", 
        ]
        return df.reindex(columns=column_order).rename(columns={
            'mz':'m/z', 
            'mz_range':'m/z_range', 
            'mz_btm':'m/z_btm', 
            'mz_top':'m/z_top'
        })
    # deisotoping
    def set_deisotoping(self, deisotoping):
        for rpd in self.rpd_list:
            rpd.set_deisotoping(deisotoping)




