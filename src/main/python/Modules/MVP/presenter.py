# -*- coding: utf-8 -*-

from curses import window
import pandas as pd
import shutil
import numpy as np
from pathlib import Path
from functools import partial
from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
    QFileDialog, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout,  
    QSizePolicy, 
    QMenuBar, 
)
from PyQt6.QtCore import (
    Qt, 
    QObject, 
    QThread, 
    QThreadPool, 
    QCoreApplication, 
)

from .. import general_functions as gf
from ..widgets import popups
from ..widgets import mz_RT_image2d as mri
from ..widgets import data_window as dw
from ..process import convert_open as co
from ..process import deisotoping as diso

class Presenter():
    def __init__(self, main_window):
        self.main_window = main_window
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(max(QThreadPool().maxThreadCount() * 2 // 3, 1))
        # イベントコネクト
        self.ignore_event = False
        self.ignore_target_update = False
        self.data_area().chromatogram_layout.window_clicked.connect(self.c_window_clicked)
        self.data_area().chromatogram_layout.range_change_finished.connect(self.RT_range_chanage_finished)
        self.data_area().chromatogram_layout.range_changed.connect(self.RT_range_chanaged)
        self.data_area().chromatogram_layout.view_range_changed.connect(self.c_view_range_chanaged)
        self.data_area().spectrum_layout.window_clicked.connect(self.s_window_clicked)
        self.data_area().spectrum_layout.range_change_finished.connect(self.mz_range_chanage_finished)
        self.data_area().spectrum_layout.range_changed.connect(self.mz_range_chanaged)
        self.data_area().spectrum_layout.view_range_changed.connect(self.s_view_range_chanaged)
        self.data_area().mz_RT_image_layout.view_range_changed.connect(self.i_view_range_changed)
        self.navigation_bar().mz_related_box_changed.connect(self.mz_related_box_changed)
        self.navigation_bar().RT_related_box_changed.connect(self.RT_related_box_changed)
        self.navigation_bar().btn_status_changed_s.connect(self.btn_status_changed_s)
        self.navigation_bar().btn_status_changed_c.connect(self.btn_status_changed_c)
        self.navigation_bar().btn_status_changed_i.connect(self.btn_status_changed_i)
        self.view_range_settings().view_range_changed_s_x.connect(lambda x_min, x_max: self.set_x_view_range_from_settings_s(x_min, x_max))
        self.view_range_settings().view_range_changed_c_x.connect(lambda x_min, x_max: self.set_x_view_range_from_settings_c(x_min, x_max))
        self.view_range_settings().view_range_changed_s_y.connect(lambda y_min, y_max: self.set_y_view_range_from_settings_s(y_min, y_max))
        self.view_range_settings().view_range_changed_c_y.connect(lambda y_min, y_max: self.set_y_view_range_from_settings_c(y_min, y_max))
        self.view_range_settings().contrast_changed_i.connect(lambda contrast_min, contrast_max: self.set_contrast_range_from_settings_i(contrast_min, contrast_max))
        self.compound_navigator().add_compound_clicked.connect(self.add_compound_clicked)
        self.compound_navigator().del_compound_clicked.connect(self.del_compound_clicked)
        self.compound_widget().new_compound_selected.connect(self.new_compound_selected)
        self.compound_widget().compound_deselected.connect(self.compound_deselected)
        self.compound_widget().target_data_changed.connect(self.target_data_changed)
    # quick access
    def database(self):
        return self.main_window.database
    def model(self):
        return self.main_window.model
    def central_widget(self):
        return self.main_window.central_widget
    def navigation_bar(self):
        return self.central_widget().navigation_bar
    def data_area(self):
        return self.central_widget().data_area
    def view_range_settings(self):
        return self.central_widget().view_range_settings
    def compound_navigator(self):
        return self.central_widget().compound_navigator
    def compound_widget(self):
        return self.central_widget().compound_widget
    # methods free from complicated events
    def convert_files_clicked(self):
        file_path_list, file_type = QFileDialog.getOpenFileNames(self.central_widget(), 'Select mzdata file', str(gf.settings.last_opened_dir), filter="xml files (*.xml)")
        if not len(file_path_list):
            return
        # file name check
        overlaped_rpd_path = []
        for file_path in file_path_list:
            rpd_path = co.get_rpd_path(Path(file_path), return_rpd=False)
            if rpd_path.exists():
                overlaped_rpd_path.append(str(rpd_path))
        if len(overlaped_rpd_path) != 0:
            wp = popups.overwrite_warning()
            wp.setInformativeText("\n\n".join(overlaped_rpd_path))
            done = wp.exec()
            if done == 65536:   # no
                return
            elif done == 16384:   # yes
                pass
            else:
                raise Exception(f"unknown answer: {done}")
        # convert loop
        self.pbar = popups.ProgressBar(N_max=len(file_path_list), message="Converting Files")
        self.pbar.show()
        for file_path in file_path_list:
            gf.settings.set_val_and_save("last_opened_dir", Path(file_path).parent)
            worker = co.Worker(co.convert_file, Path(file_path))
            worker.signals.finished.connect(lambda:self.pbar.add())
            self.thread_pool.start(worker)
    def export_targets_clicked(self):
        if self.compound_widget().model.rowCount() == 0:
            wp = popups.no_target_added()
            wp.exec()
            return
        # 保存パス
        save_path = gf.new_dir_path_wo_overlap(gf.settings.last_opened_dir / (gf.settings.last_opened_dir.name))
        save_path, dir_type = QFileDialog.getSaveFileName(self.main_window, 'Enter file name', str(save_path), filter="csv file (*.csv)")
        if save_path == "":
            return
        # target information
        data_items = self.compound_widget().get_data_items()
        target_df = self.model().export_auc_data(data_items)
        target_df.to_csv(save_path, sep="\t")
    def export_images_clicked(self):
        if self.database().N_data() == 0:
            wp = popups.no_opened_files()
            wp.exec()
            return
        # ポップアップ
        dir_path = gf.new_dir_path_wo_overlap(gf.settings.last_opened_dir / (gf.settings.last_opened_dir.name + "_svg"))
        export_settings = popups.ExportSettings(dir_path)
        done = export_settings.exec()
        if done == 4194304: # cancel
            return
        elif done == 2048:  # save
            dir_path = Path(export_settings.dir_path_label.text())
            include_mz_RT_labels = export_settings.include_mz_RT_labels()
            include_mz_RT_regions = export_settings.include_mz_RT_regions()
            plus_minus_style = export_settings.plus_minus_style()
        else:
            raise Exception(f"Returned value {done} is not acceptable.")
        # Pathlib cannot remove directry with some files inside
        if dir_path.exists():
            shutil.rmtree(dir_path)
        dir_path.mkdir()
        # save svg
        self.central_widget().export_svg(dir_path, include_mz_RT_labels, include_mz_RT_regions, plus_minus_style)
    def generate_mz_RT_Image2D(self):
        self.ofc = mri.OpenedFilesCheckbox(self.model().rpd_list)
        self.ofc.show()
        self.ofc.btn_ok_clicked.connect(self.show_mz_RT_image2d)
        self.ofc.btn_cancel_clicked.connect(self.close_mz_RT_image2d)
    def show_mz_RT_image2d(self, rpd_list):
        mz_view_x_range, mz_view_y_range = self.data_area().get_view_range_s(ref_index=0)
        RT_view_x_range, RT_view_y_range  = self.data_area().get_view_range_c(ref_index=0)

        self.mz_RT_images2d = {}
        for rpd in rpd_list:
            img = rpd.extract_mz_RT_2d_image(mz_view_x_range, RT_view_x_range)  # shape = (len(RT), len(mz))
            img = np.rot90(img, 1)

        # for rpd in range(1):
        #     img = np.random.randn(200, 300)

            mri_window = mri.MzRTImage2D(window_title="TEST")#rpd.file_path.stem)
            mri_window.set_image(img, x_range=RT_view_x_range, y_range=mz_view_x_range)
            self.mz_RT_images2d[rpd] = mri_window
            self.mz_RT_images2d[rpd].show()
    def close_mz_RT_image2d(self):
        self.ofc.close()
        if not hasattr(self, "mz_RT_images2d"):
            return
        for rpd, mz_RT_image2d in self.mz_RT_images2d.items():
            mz_RT_image2d.close()
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
    def target_update_process_deco(func):
        def wrapper(self, *keys, **kwargs):
            if self.ignore_target_update:
                return
            self.ignore_target_update = True
            res = func(self, *keys, **kwargs)
            self.ignore_target_update = False
            return res
        return wrapper
    # from commands (e.g. file open menu)
    def open_files_clicked(self, file_path_list=None):
        if file_path_list is None:
            file_path_list, file_type = QFileDialog.getOpenFileNames(self.central_widget(), 'Select spctrum file', str(gf.settings.last_opened_dir), filter="text files (*.rpd;)")  # *.mzdata.xml
        if not len(file_path_list):
            return
        # prepare everything
        self.warning_messages = []
        worker_results_processor = co.WorkerResultsProcessor()
        self.pbar = popups.ProgressBar(N_max=len(file_path_list), message="Opening Files")
        self.pbar.finished.connect(partial(worker_results_processor.thread_pool_finished, self.welcome_new_rpd))
        self.pbar.finished.connect(self.show_warning_message_for_opening_file)
        self.pbar.show()
        # open loop
        for i, file_path in enumerate(file_path_list):
            gf.settings.set_val_and_save("last_opened_dir", Path(file_path).parent)
            worker = co.Worker(co.open_file, Path(file_path))
            worker.signals.result.connect(partial(worker_results_processor.append_worker_produced_results, i)) # return: rpd, message
            worker.signals.finished.connect(self.pbar.add)
            self.thread_pool.start(worker)
    def show_warning_message_for_opening_file(self):
        if len(self.warning_messages) > 0:
            wp = popups.WarningPopup("Warnings when opening files!")
            wp.setInformativeText("\n\n".join(self.warning_messages))
            wp.exec()
    @event_process_deco
    def welcome_new_rpd(self, rpd, message):
        if message is not None:
            self.warning_messages.append(message)
        if rpd is None:
            return
        self.database().add_rpd(rpd)
        self.model().set_rpd_data_from_database(-1) # set last added
        # add data based on the information on the navigation_bar
        self.data_area().add_row()
        # extract data (if mz_top is np.inf, TIC will be extracted)
        mz_btm, mz_top = self.navigation_bar().get_mz_top_bottom()
        RT_btm, RT_top = self.navigation_bar().get_RT_top_bottom()
        if self.navigation_bar().is_TIC():    # TIC
            chromatogram = self.model().extract_chromatogram(0, np.inf, index=-1)
            self.data_area().set_mz_region_visible(False, index=-1)
        else:
            chromatogram = self.model().extract_chromatogram(mz_btm, mz_top, index=-1)
        spectrum = self.model().extract_spectrum(RT_btm, RT_top, index=-1)
        info = self.model().extract_info(index=-1)
        # send it to view
        self.data_area().set_spectrum_window_type(info.spectrum_type, index=-1)
        self.data_area().update_chromatogram(chromatogram, index=-1)
        self.data_area().update_spectrum(spectrum, index=-1)
        self.data_area().update_mz_RT_image(rpd, index=-1)
        self.data_area().update_info(info, index=-1)
        # region items on the graphs
        self.data_area().update_RT_region(RT_btm, RT_top, index=-1)
        self.data_area().update_mz_region(mz_btm, mz_top, index=-1)
        # set view range based on the button state of the navigation bar
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        if not self.navigation_bar().is_bar_enabled:    # no files were opened previously
            self.navigation_bar().set_bar_enable(True)
            self.autorange_all_xy_s()
            self.autorange_all_xy_c()
            # view_range_settings
            self.view_range_settings().enable_input(True)
            self.enable_view_range_settings_y_s(y_scale_status_s)
            self.enable_view_range_settings_y_c(y_scale_status_c)
        else:                                           # at least one file was opened previously
            # view x_range: topの view に合わせる
            self.set_view_range_s_x_all(ref_index=0)
            self.set_view_range_c_x_all(ref_index=0)
            # view y_range: spectrum
            self.set_view_range_s_y_by_y_scale_status(y_scale_status_s.replace("L0A0", "L0A1"), ref_index=0)
            self.set_view_range_c_y_by_y_scale_status(y_scale_status_c.replace("L0A0", "L0A1"), ref_index=0)
            # view_range_settings
            self.update_view_range_settings_s_y(y_scale_status_s)
            self.update_view_range_settings_c_y(y_scale_status_c)
        self.update_view_range_settings_contrast()
    def set_view_range_clicked(self):
        self.view_range_settings().show()
        # self.view_range_settings.raise_()
        self.view_range_settings().activateWindow()
    @event_process_deco
    def load_targets_clicked(self):
        # パス
        file_path = gf.new_dir_path_wo_overlap(gf.settings.last_opened_dir / (gf.settings.last_opened_dir.name))
        file_path, dir_type = QFileDialog.getOpenFileName(self.main_window, 'Select a file', str(file_path), filter="csv file (*.csv)")
        if file_path == "":
            return
        target_df = pd.read_csv(file_path, sep="\t", index_col=0, keep_default_na=False)
        self.compound_widget().load_targets(target_df)
    def execute_Deisotoping(self):
        data_items = self.compound_widget().get_data_items_by_formula()
        deisotoping = diso.Deisotoping(data_items)
        self.model().set_deisotoping(deisotoping)
    # from widgets inside window
    @event_process_deco
    def c_window_clicked(self, x_value, y_value, chromatogram_window):
        # update navigation bar
        self.navigation_bar().set_RT(RT=x_value, RT_range=None)
        # process RT data
        RT = x_value
        RT_range = self.navigation_bar().RT_range_box.value()
        RT_btm, RT_top = RT - RT_range, RT + RT_range
        # update data_area
        self.data_area().update_RT_regions(RT_btm, RT_top)
        spectra = self.model().extract_spectra(RT_btm, RT_top)
        self.data_area().update_spectra(spectra)
        # update y view range
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.set_view_range_s_y_by_y_scale_status(y_scale_status_s.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_s_y(y_scale_status_s)
        # compound_widget
        self.clear_target_selection()
    @event_process_deco
    def s_window_clicked(self, x_value, y_value, spectrum_window):
        if self.navigation_bar().is_TIC():
            self.navigation_bar().btn_TIC.setChecked(False)
            self.data_area().set_mz_regions_visible(True)
        # update navigation bar
        self.navigation_bar().set_mz(mz=x_value, mz_range=None)
        self.navigation_bar().enable_mz_related_box(True)
        # process mz_data
        mz = x_value
        mz_range = self.navigation_bar().mz_range_box.value()
        mz_btm, mz_top = mz - mz_range, mz + mz_range
        # update data_area
        self.data_area().update_mz_regions(mz_btm, mz_top)
        chromatograms = self.model().extract_chromatograms(mz_btm, mz_top)
        self.data_area().update_chromatograms(chromatograms)

        print(chromatograms)

        # update y view range
        self.ignore_event = False
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.set_view_range_c_y_by_y_scale_status(y_scale_status_c.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_c_y(y_scale_status_c)
        # compound_widget
        self.clear_target_selection()
    @event_process_deco
    def RT_range_chanage_finished(self, RT_btm, RT_top, chromatogram_window):
        # update navigation bar
        RT = (RT_btm + RT_top) / 2
        RT_range = (RT_top - RT_btm) / 2
        self.navigation_bar().set_RT(RT=RT, RT_range=RT_range)
        # update data_area
        spectra = self.model().extract_spectra(RT_btm, RT_top)
        self.data_area().update_spectra(spectra)
        # update regions
        self.data_area().update_RT_regions(RT_btm, RT_top)
        # change target settings
        self.compound_widget().update_info_of_selected_target(RT=RT, RT_range=RT_range)
        # update y view range
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.set_view_range_s_y_by_y_scale_status(y_scale_status_s.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_s_y(y_scale_status_s)
    @event_process_deco
    def mz_range_chanage_finished(self, mz_btm, mz_top, spectrum_window):
        # update navigation bar
        mz = (mz_btm + mz_top) / 2
        mz_range = (mz_top - mz_btm) / 2
        self.navigation_bar().set_mz(mz=mz, mz_range=mz_range)
        # update data_area
        chromatograms = self.model().extract_chromatograms(mz_btm, mz_top)
        self.data_area().update_chromatograms(chromatograms)
        # update regions
        self.data_area().update_mz_regions(mz_btm, mz_top)
        # change target settings
        self.compound_widget().update_info_of_selected_target(mz=mz, mz_range=mz_range)
        # update y view range
        self.ignore_event = False
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.set_view_range_c_y_by_y_scale_status(y_scale_status_c.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_c_y(y_scale_status_c)
    @event_process_deco
    def RT_range_chanaged(self, RT_btm, RT_top, chromatogram_window):
        # update navigation bar
        self.navigation_bar().set_RT(RT=(RT_btm + RT_top) / 2, RT_range=(RT_top - RT_btm) / 2)
        # update regions
        self.data_area().update_RT_regions(RT_btm, RT_top)
    @event_process_deco
    def mz_range_chanaged(self, mz_btm, mz_top, spectrum_window):
        # update navigation bar
        self.navigation_bar().set_mz(mz=(mz_btm + mz_top) / 2, mz_range=(mz_top - mz_btm) / 2)
        # update regions
        self.data_area().update_mz_regions(mz_btm, mz_top)
    @event_process_deco
    def c_view_range_chanaged(self, chromatogram_window):
        ref_index = self.data_area().chromatogram_layout.get_window_index(chromatogram_window)
        self.ignore_event = False
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.set_view_range_c_x_all(ref_index=ref_index)
        self.set_view_range_c_y_by_y_scale_status(y_scale_status_c, ref_index=ref_index)
        # view_range_settings
        self.update_view_range_settings_c_y(y_scale_status_c)
        self.update_view_range_settings_contrast()
    @event_process_deco
    def s_view_range_chanaged(self, spectrum_window):
        ref_index = self.data_area().spectrum_layout.get_window_index(spectrum_window)
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.set_view_range_s_x_all(ref_index=ref_index)
        self.set_view_range_s_y_by_y_scale_status(y_scale_status_s, ref_index=ref_index)
        # view_range_settings
        self.update_view_range_settings_s_y(y_scale_status_s)
        self.update_view_range_settings_contrast()
    @event_process_deco
    def i_view_range_changed(self, mz_RT_image_window: dw.MzRTImageWindow):
        view_range_c_x, view_range_s_x = mz_RT_image_window.viewRange()
        self.data_area().set_view_range_i_RT(*view_range_c_x)
        self.data_area().set_view_range_i_mz(*view_range_s_x)
        self.data_area().set_view_range_c_x(*view_range_c_x)
        self.data_area().set_view_range_s_x(*view_range_s_x)
        self.view_range_settings().set_values_c_x(view_range_c_x)
        self.view_range_settings().set_values_s_x(view_range_s_x)
        self.update_view_range_settings_contrast()
        self.ignore_event = False
        self.set_view_range_c_y_by_y_scale_status(y_scale_status=self.navigation_bar().get_y_scale_status_c(), ref_index=0)
        self.set_view_range_s_y_by_y_scale_status(y_scale_status=self.navigation_bar().get_y_scale_status_s(), ref_index=0)
    # from navigation bar
    @event_process_deco
    def RT_related_box_changed(self, RT, RT_range):
        RT_btm = RT - RT_range
        RT_top = RT + RT_range
        # update data_area
        self.data_area().update_RT_regions(RT_btm, RT_top)
        spectra = self.model().extract_spectra(RT_btm, RT_top)
        self.data_area().update_spectra(spectra)
        # update view
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.set_view_range_s_y_by_y_scale_status(y_scale_status_s.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_s_y(y_scale_status_s)
        # compound_widget
        self.clear_target_selection()
    @event_process_deco
    def mz_related_box_changed(self, mz, mz_range):
        mz_btm = mz - mz_range
        mz_top = mz + mz_range
        # update data_area
        self.data_area().update_mz_regions(mz_btm, mz_top)
        chromatograms = self.model().extract_chromatograms(mz_btm, mz_top)
        self.data_area().update_chromatograms(chromatograms)
        # update view
        self.ignore_event = False
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.set_view_range_c_y_by_y_scale_status(y_scale_status_c.replace("L1A0", "pass"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_c_y(y_scale_status_c)
        # compound_widget
        self.clear_target_selection()
    @event_process_deco
    def btn_status_changed_s(self, btn_type, is_checked):
        # view_range_settings
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.enable_view_range_settings_y_s(y_scale_status_s)
        # update data
        if btn_type == "autoY_s":
            if not is_checked:  # when autoY is clicked OFF
                return
        elif btn_type == "linkY_s":
            pass
        elif btn_type == "reset_X_range_s":
            view_range_s_x = self.data_area().reset_X_range_s()
            self.view_range_settings().set_values_s_x(view_range_s_x)
            if not self.navigation_bar().btn_autoY_s.isChecked():
                return
        else:
            raise Exception(f"unknown btn_type: {btn_type}")
        # update view range
        self.ignore_event = False
        y_scale_status_s = self.navigation_bar().get_y_scale_status_s()
        self.set_view_range_s_y_by_y_scale_status(y_scale_status_s.replace("L1A0", "L1A1"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_s_y(y_scale_status_s)
    @event_process_deco
    def btn_status_changed_c(self, btn_type, is_checked):
       # view_range_settings
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.enable_view_range_settings_y_c(y_scale_status_c)
        # update data
        if btn_type == "TIC":
            if is_checked:    # TIC
                chromatograms = self.model().extract_chromatograms(0, np.inf)
            else:
                mz_btm, mz_top = self.navigation_bar().get_mz_top_bottom()
                chromatograms = self.model().extract_chromatograms(mz_btm, mz_top)
            self.data_area().update_chromatograms(chromatograms)
            self.data_area().set_mz_regions_visible(not is_checked)
            self.navigation_bar().enable_mz_related_box(not is_checked)
            self.clear_target_selection()
        elif btn_type == "autoY_c":
            if not is_checked:  # when autoY is clicked OFF
                return
        elif btn_type == "linkY_c":
            pass
        elif btn_type == "reset_X_range_c":
            view_range_c_x = self.data_area().reset_X_range_c()
            self.view_range_settings().set_values_c_x(view_range_c_x)
            if not self.navigation_bar().btn_autoY_c.isChecked():
                return
        else:
            raise Exception(f"unknown btn_type: {btn_type}")
        # update view range
        self.ignore_event = False
        y_scale_status_c = self.navigation_bar().get_y_scale_status_c()
        self.set_view_range_c_y_by_y_scale_status(y_scale_status_c.replace("L1A0", "L1A1"), ref_index=None)
        # view_range_settings
        self.update_view_range_settings_c_y(y_scale_status_c)
    @event_process_deco
    def btn_status_changed_i(self, btn_type, is_checked):
        if btn_type == "contrast_i":
            pass
        elif btn_type == "reset_XY_range_i":
            pass
    # methods to set view range
    @event_process_deco
    def autorange_all_xy_c(self):
        view_range_c_x, view_range_c_y = self.data_area().autorange_c_all()
        self.data_area().set_view_range_i_RT(*view_range_c_x)
        self.ignore_event = False
        self.set_values_of_view_range_settings_c(view_range_c_x, view_range_c_y)
    @event_process_deco
    def autorange_all_xy_s(self):
        view_range_s_x, view_range_s_y = self.data_area().autorange_s_all()
        self.data_area().set_view_range_i_mz(*view_range_s_x)
        self.ignore_event = False
        self.set_values_of_view_range_settings_s(view_range_s_x, view_range_s_y)
    @event_process_deco
    def set_view_range_s_x_all(self, ref_index):
        view_range_s_x = self.data_area().set_view_range_s_x_all(ref_index=ref_index)
        self.data_area().set_view_range_i_mz(*view_range_s_x)
        self.view_range_settings().set_values_s_x(view_range_s_x)
    @event_process_deco
    def set_view_range_c_x_all(self, ref_index):
        view_range_c_x = self.data_area().set_view_range_c_x_all(ref_index=ref_index)
        self.data_area().set_view_range_i_RT(*view_range_c_x)
        self.view_range_settings().set_values_c_x(view_range_c_x)
    @event_process_deco
    def set_view_range_s_y_by_y_scale_status(self, y_scale_status, ref_index):
        if y_scale_status == "L1A1_s":      # Link, and Auto
            self.data_area().set_view_range_s_y_link_auto()
        elif y_scale_status == "L1A0_s":    # Link, but not Auto
            self.data_area().set_view_range_s_y_link(ref_index=ref_index)
        elif y_scale_status == "L0A1_s":    # not Link, but Auto
            self.data_area().set_view_range_s_y_auto(ref_index=ref_index)
        elif y_scale_status in ("L0A0_s", "pass_s"):    # not Link not Auto
            pass
        else:
            raise Exception(f"unknown status: {y_scale_status}")
    @event_process_deco
    def set_view_range_c_y_by_y_scale_status(self, y_scale_status, ref_index):
        if y_scale_status == "L1A1_c":      # Link and Auto
            self.data_area().set_view_range_c_y_link_auto()
        elif y_scale_status == "L1A0_c":    # Link but not Auto
            self.data_area().set_view_range_c_y_link(ref_index=ref_index)
        elif y_scale_status == "L0A1_c":    # not Link but Auto
            self.data_area().set_view_range_c_y_auto(ref_index=ref_index)
        elif y_scale_status in ("L0A0_c", "pass_c"):    # not Link not Auto
            pass
        else:
            raise Exception(f"unknown status: {y_scale_status}")
    # methods to set view_range_settings
    def enable_view_range_settings_y_s(self, y_scale_status_s):
        enable = y_scale_status_s == "L1A0_s"
        self.view_range_settings().enable_y_s(enable)
        if enable:
            self.ignore_event = False
            self.update_view_range_settings_s_y(y_scale_status_s)
    def enable_view_range_settings_y_c(self, y_scale_status_c):
        enable = y_scale_status_c == "L1A0_c"
        self.view_range_settings().enable_y_c(enable)
        if enable:
            self.ignore_event = False
            self.update_view_range_settings_c_y(y_scale_status_c)
    def update_view_range_settings_contrast(self):
        contrast_status_i = self.navigation_bar().get_contrast_status_i()
        if contrast_status_i == "auto":
            contrast = self.data_area().set_image_contrast_auto()
        elif contrast_status_i == "manual":
            pass
        else:
            raise Exception(f"unknown contrast_status_i {contrast_status_i}")
        self.view_range_settings().set_values_contrast(contrast)
    @event_process_deco
    def set_values_of_view_range_settings_s(self, view_range_s_x, view_range_s_y):
        self.view_range_settings().set_values_s_x(view_range_s_x)
        self.view_range_settings().set_values_s_y(view_range_s_y)
    @event_process_deco
    def set_values_of_view_range_settings_c(self, view_range_c_x, view_range_c_y):
        self.view_range_settings().set_values_c_x(view_range_c_x)
        self.view_range_settings().set_values_c_y(view_range_c_y)
    @event_process_deco
    def set_x_view_range_from_settings_s(self, x_min, x_max):
        self.data_area().set_view_range_s_x(x_min, x_max)
        self.data_area().set_view_range_i_mz(x_min, x_max)
        self.ignore_event = False
        self.set_view_range_s_y_by_y_scale_status(y_scale_status=self.navigation_bar().get_y_scale_status_s(), ref_index=0)
        # change target settings
        self.compound_widget().update_info_of_selected_target(view_range_s_x=[x_min, x_max])
    @event_process_deco
    def set_x_view_range_from_settings_c(self, x_min, x_max):
        self.data_area().set_view_range_c_x(x_min, x_max)
        self.data_area().set_view_range_i_RT(x_min, x_max)
        self.ignore_event = False
        self.set_view_range_c_y_by_y_scale_status(y_scale_status=self.navigation_bar().get_y_scale_status_c(), ref_index=0)
        # change target settings
        self.compound_widget().update_info_of_selected_target(view_range_c_x=[x_min, x_max])
    @event_process_deco
    def set_y_view_range_from_settings_s(self, y_min, y_max):
        self.data_area().set_view_range_s_y(y_min, y_max)
    @event_process_deco
    def set_y_view_range_from_settings_c(self, y_min, y_max):
        self.data_area().set_view_range_c_y(y_min, y_max)
    @event_process_deco
    def set_contrast_range_from_settings_i(self, contrast_min, contrast_max):
        self.data_area().set_image_contrast(contrast_min, contrast_max)
    @event_process_deco
    def update_view_range_settings_s_y(self, y_scale_status_s):
        if y_scale_status_s == "L1A0_s":
            view_range_s_x, view_range_s_y = self.data_area().get_view_range_s(ref_index=0)
            self.view_range_settings().set_values_s_y(view_range_s_y)
    @event_process_deco
    def update_view_range_settings_c_y(self, y_scale_status_c):
        if y_scale_status_c == "L1A0_c":
            view_range_c_x, view_range_c_y = self.data_area().get_view_range_c(ref_index=0)
            self.view_range_settings().set_values_c_y(view_range_c_y)
    # from compound_navigator
    @target_update_process_deco
    def clear_target_selection(self):
        self.compound_widget().clearSelection()
    @event_process_deco
    @target_update_process_deco
    def add_compound_clicked(self):
        mz, mz_range = self.navigation_bar().get_mz_info()
        RT, RT_range = self.navigation_bar().get_RT_info()
        is_TIC = self.navigation_bar().is_TIC()
        view_range_s_x, view_range_s_y = self.data_area().get_view_range_s(ref_index=0)
        view_range_c_x, view_range_c_y = self.data_area().get_view_range_c(ref_index=0)
        self.compound_widget().add_compound(
            mz=mz, 
            mz_range=mz_range, 
            RT=RT, 
            RT_range=RT_range, 
            is_TIC=is_TIC, 
            view_range_s_x=view_range_s_x, 
            view_range_c_x=view_range_c_x
        )
        # select
        index = self.compound_widget().select_row(row=-1)
        self.compound_navigator().enable_btn_del(enable=True)
    @event_process_deco
    @target_update_process_deco
    def new_compound_selected(self, data_item):
        # navigation bar
        self.navigation_bar().set_RT(RT=data_item.RT, RT_range=data_item.RT_range)
        self.navigation_bar().set_mz(mz=data_item.mz, mz_range=data_item.mz_range)
        self.navigation_bar().enable_mz_related_box(enable=not data_item.is_TIC)
        self.navigation_bar().btn_TIC.setChecked(data_item.is_TIC)
        self.compound_navigator().enable_btn_del(enable=True)
        # mz_regions
        mz_btm = data_item.mz - data_item.mz_range
        mz_top = data_item.mz + data_item.mz_range
        self.data_area().set_mz_regions_visible(not data_item.is_TIC)
        self.data_area().update_mz_regions(mz_btm, mz_top)
        # view_range_x
        self.view_range_settings().set_values_c_x(data_item.view_range_c_x)
        self.view_range_settings().set_values_s_x(data_item.view_range_s_x)
        self.data_area().set_view_range_c_x(*data_item.view_range_c_x)
        self.data_area().set_view_range_s_x(*data_item.view_range_s_x)
        self.data_area().set_view_range_i_RT(*data_item.view_range_c_x)
        self.data_area().set_view_range_i_mz(*data_item.view_range_s_x)
        # update data
        self.ignore_event = False
        self.RT_related_box_changed(RT=data_item.RT, RT_range=data_item.RT_range)
        self.btn_status_changed_c(btn_type="TIC", is_checked=data_item.is_TIC)        
        # self.mz_related_box_changed(mz=data_item.mz, mz_range=data_item.mz_range)
    @event_process_deco
    def compound_deselected(self):
        self.compound_navigator().enable_btn_del(enable=False)
    @event_process_deco
    def del_compound_clicked(self):
        deleted_row = self.compound_widget().del_selected_compound()
        if self.compound_widget().model.rowCount() > 0:
            index = self.compound_widget().select_row(row=deleted_row)
            data_item = self.compound_widget().get_data_item(index=index)
            self.ignore_event = False
            self.new_compound_selected(data_item)
        else:
            self.compound_navigator().enable_btn_del(enable=False)
    # from compound_widget
    @target_update_process_deco
    def target_data_changed(self, data_item):
        for k, v in data_item.items():
            if k == "TIC":
                self.navigation_bar().btn_TIC.setChecked(v)
                self.btn_status_changed_c(btn_type=k, is_checked=v)
            elif k == "RT_related":
                self.navigation_bar().set_RT(RT=v[0], RT_range=v[1])
            elif k == "mz_related":
                self.navigation_bar().set_mz(mz=v[0], mz_range=v[1])
            elif k == "formula":
                self.navigation_bar().btn_TIC.setChecked(False)
                self.navigation_bar().enable_mz_related_box(True)
                self.navigation_bar().set_mz(mz=v[0], mz_range=v[1])
                self.data_area().set_mz_regions_visible(True)
            else:
                raise Exception(f"unknown key: {k}")



