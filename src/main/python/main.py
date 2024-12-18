# -*- Coding: utf-8 -*-

import os, sys
import traceback
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, 
    QMainWindow, 
)

# my modules
from Modules import general_functions as gf
from Modules.MVP import model
from Modules.MVP import database as db
from Modules.MVP import presenter
from Modules.widgets import popups
from Modules.widgets import central_widget as cw
from Modules.widgets import atomic_ratio_window as arw
from Modules.process import atomic_ratio as ar
from Modules.process import convert_open as co

# SPECIAL FUNCTIONS
def get_resource_path():
    if getattr(sys, 'frozen', False):
        main_path = Path(sys.executable)
    elif __file__:
        main_path = Path(__file__).resolve()
    return main_path.parents[3] / "src" / "main" / "resources"

########
# MAIN #
########
class MainWindow(QMainWindow):
    # child_window_list_changed = pyqtSignal(QWidget)
    def __init__(self):
        ####################
        # general settings #
        ####################
        gf.settings.load_settings(get_resource_path())
        ar.load_elements(gf.settings.resource_path / "Atomic Weights and Isotopic Compositions 20220704.txt")
        # hidden settings
        image_on = False
        fast_display = False    #True

        super().__init__()
        self.setWindowTitle(gf.app_version())
        self.central_widget = cw.CentralWidget(main_window=self, image_on=image_on)
        self.setCentralWidget(self.central_widget)
        # error処理
        sys.excepthook = self.excepthook

        #######
        # MVP #
        #######
        """
        - database -> model <-> presenter <-> view/ctrl - user
        - MVP should be defied after the construction of central widget
        """
        self.database = db.DataBase(main_window=self)
        self.model = model.Model(main_window=self, fast_display=fast_display)
        self.presenter = presenter.Presenter(main_window=self)

        ############
        # MENU BAR #
        ############
        # File
        fileMenu = self.menuBar().addMenu('File')
        fileMenu.addAction('Open', self.presenter.open_files_clicked).setShortcut("Ctrl+O")
        fileMenu.addAction('Convert Files', self.presenter.convert_files_clicked).setShortcut("Ctrl+Shift+C")
        fileMenu.addAction('Export Targets', self.presenter.export_targets_clicked).setShortcut("Ctrl+E")
        fileMenu.addAction('Load Targets', self.presenter.load_targets_clicked).setShortcut("Ctrl+L")
        fileMenu.addAction('Export Images', self.presenter.export_images_clicked).setShortcut("Ctrl+Shift+E")
        # Edit
        editMenu = self.menuBar().addMenu('Edit')
        editMenu.addAction('Add Target', self.presenter.add_compound_clicked) #.setShortcut("Ctrl+A")
        editMenu.addAction('Remove All Targets', self.presenter.remove_all_targets_clicked)
        # View
        viewMenu = self.menuBar().addMenu('View')
        viewMenu.addAction('Set View Range', self.presenter.set_view_range_clicked).setShortcut("Ctrl+Meta+V")
        # Tools
        toolsMenu = self.menuBar().addMenu('Tools')
        toolsMenu.addAction("Atomic Ratio Calculator", self.show_atomic_ratio_window).setShortcut("Ctrl+T")
        toolsMenu.addAction("Execute Deisotoping", self.presenter.execute_Deisotoping).setShortcut("Ctrl+D")
        toolsMenu.addAction("Generate mz-RT Image2D", self.presenter.generate_mz_RT_Image2D).setShortcut("Ctrl+G")
        toolsMenu.addAction("Use adduct ion syntax", self.presenter.show_adduct_ion_syntax).setShortcut("Ctrl+H")
        # Helps
        helpMenu = self.menuBar().addMenu('Help')
        helpMenu.addAction('About', self.show_about)
        helpMenu.addAction('Settings', self.show_preferences)

        #########
        # STYLE #
        #########
        self.setStyleSheet("QMainWindow {background: #00FFFFFF}")

        ########
        # TEST #
        ########
        if not getattr(sys, 'frozen', False):
            demo_file_path = gf.settings.resource_path.parents[2] / "demo_data" / "20220523_1-v12-mix3_0.mzdata.xml"
            demo_file_path = gf.settings.resource_path.parents[2] / "demo_data" / "20240919_RPformate18MIN70B_neg-pos_PJL280_ER-mCh-iLID-LOVPLD_0_1_WITH-SEGMENT.mzdata.xml"
            demo_file_path_centroid = gf.settings.resource_path.parents[2] / "demo_data" / "20220523_1-v12-mix3_0_centroid.rpd"
            demo_file_path_centroid = gf.settings.resource_path.parents[2] / "demo_data" / "20241129_Cho-release_centroid_9_P2-8-15_spl1_p0_centroid.rpd"
            demo_file_path_rpd = gf.settings.resource_path.parents[2] / "demo_data" / "0_blank__p0_v23.rpd"
            demo_file_path_rpd = gf.settings.resource_path.parents[2] / "demo_data" / "8_HEK293T-d9Cho_B&D_p220.rpd"
            demo_file_path_csv = gf.settings.resource_path.parents[2] / "demo_data" / "PC_simplified_09092024.csv"
            demo_file_path_xml_centroid = gf.settings.resource_path.parents[2] / "demo_data" / "20241129_Cho-release_centroid_9_P2-8-15_spl1_p0_centroid.mzdata.xml"
            ### open mzdata file and view
            # self.presenter.convert_files_clicked(file_path_list=[demo_file_path])
            # self.presenter.convert_files_clicked(file_path_list=[demo_file_path_xml_centroid])
            # self.presenter.open_files_clicked([demo_file_path_rpd])
            # self.presenter.open_files_clicked([demo_file_path_centroid])
            # self.presenter.load_targets_clicked(demo_file_path_csv)

            ### convert mzdata file

    # その他
    def show_about(self):
        about_popup = popups.About()
        about_popup.exec()
    def show_preferences(self):
        preferencess_popup = popups.Preferences(cvParam_assertion=co.cvParam_assertion)
        preferencess_popup.exec()
        if preferencess_popup.pressed_button is None:
            return
        elif preferencess_popup.pressed_button == "ok":
            co.cvParam_assertion = preferencess_popup.cvParam_assertion.isChecked()
    def show_atomic_ratio_window(self):
        self.atomic_ratio_calculator = arw.AtomicRatioCalculator()
        self.atomic_ratio_calculator.show()
    def close_file_clicked(self):
        # 保存されていない場合
        is_modified = False
        done = 0    # no button
        if is_modified:
            warning_popup = popups.WarningPopup("Do you want to save the changes made to the file?\nYour changes will be lost if you don't save them!", p_type="Save")
            done = warning_popup.exec_()
            # discard:8388608, cancel: 4194304, Save: 2048
            if done == 2048:
                pass
                # self.save_file_clicked()
            elif done == 4194304:
                return done
            elif done == 8388608:
                pass
        # self.close_file()
        return done
    def closeEvent(self, event=None):
        # discard:8388608, cancel: 4194304, Save: 2048
        done = self.close_file_clicked()
        if done == 4194304:
            event.ignore()
            return
        print("closing...")
        sys.exit()
    def excepthook(self, exc_type, exc_value, exc_traceback):
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(tb)
        w = popups.WarningPopup(message="Unexpected error!", title="crash report", p_type="Normal")
        w.setInformativeText(f"Please send the detaileds below to the developer.\n{gf.app_version()} may not function correctly without restarting.")
        w.setDetailedText(tb)
        w.exec()
 

###########
###########
###########


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
