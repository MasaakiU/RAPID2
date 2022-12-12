# -*- coding: utf-8 -*-

import imp
from importlib.resources import path
# import resource
import sys, os
import textwrap
from pathlib import Path
import pickle

from PyQt6.QtGui import (
    QFont, 
    QFontDatabase, 
)
from PyQt6.QtWidgets import (
    QLabel, 
    QApplication
)

import pyqtgraph as pg

###########
# 文字処理 #
###########
def rm_indent(string):
    return textwrap.dedent(string).strip()

################
# VERSION INFO #
################
QApplication.setApplicationName('RAPID')
QApplication.setApplicationVersion('0.2.2')
update_history = {
    "0.2.0":"General framework was generated.", 
    "0.2.1":"Minor bugfixes, mz_RT_images was implemented, but is hidden from GUI.", 
    "0.2.2":rm_indent("""
        Support of charge number of ions
        - 1 (+, +2, +3, ..., -, -2, -3, ...).
        Bugfixes for deisotoping
        - bug fix for display original data. Previously, original data was displayed correctly only when mz, RT ranges are equal to one of the targets.
        """), 
}
name = QApplication.applicationName()
ver = QApplication.applicationVersion()
def app_version():
    return f"{name} ver.{ver}"
print(app_version())

############
# SETTINGS #
############
pg.setConfigOption('background', 'w')
pg.setConfigOption("foreground", "k")

# 設定フィアル処理
class Settings():
    def __init__(self):
        self.fixed_settings_dict = {}
        self.default_settings_dict = {}
    def __getattr__(self, k):
        v = self.fixed_settings_dict.get(k, None)
        if v is not None:
            return v
        v = self.default_settings_dict.get(k, None)
        if v is not None:
            return v
        raise Exception(f"undefined key: {k}")
    def keys(self):
        return list(self.fixed_settings_dict.keys()) + list(self.default_settings_dict.keys())
    def load_settings(self, base_path):
        self.initialize_settings(base_path)
        # 設定ファイルの読み込み
        with open(self.settings_path, mode='r') as f:
            new_default_settings_dict = {}
            for l in f.read().strip().split("\n"):
                k, v = l.split("\t")
                if v == "None":
                    v = None
                elif k.endswith("_dir"):
                    v = Path(v)
                new_default_settings_dict[k] = v
        self.update_default_settings(new_default_settings_dict)
        self.apply_styles()
    def initialize_settings(self, resource_path):
        # 保存されない、固定値（base_path のみに影響される）の設定値
        self.fixed_settings_dict.update(
            resource_path = resource_path, 
            btn_icon_path = resource_path / "icons", 
            settings_path = resource_path / "settings"
        )
        # 保存される、可変の設定値
        self.default_settings_dict.update(
                last_opened_dir = Path.home() / 'Desktop'
        )
    def update_default_settings(self, new_default_settings_dict):
        for k, v in new_default_settings_dict.items():
            if k in self.fixed_settings_dict.keys():
                raise Exception(f"Error!\n{new_default_settings_dict.keys()}\n{self.fixed_settings_dict.keys()}")
            if v is not None:
                self.default_settings_dict[k] = v
    def apply_styles(self):
        for k, v in self.default_settings_dict.items():
            # background, foreground 設定
            if k in ("background", "foreground"):
                pg.setConfigOption(k, v)
                # pg.setConfigOption("background", settings["bg_brush"])
                # pg.setConfigOption("foreground", settings["graph_line"])
    def set_val_and_save(self, k, v):
        if k not in self.keys():
            raise Exception(f"{k} is not defined")
        self.update_default_settings({k:v})
        self.save_settings_file()
    def reset_settings_and_save(self, resource_path=None):
        if resource_path is None:
            resource_path = self.resource_path
        self.initialize_settings(resource_path)
        self.save_settings_file()
    def save_settings_file(self):
        with open(self.settings_path, mode='w') as f:
            settings_data = "\n".join([f"{k}\t{v}"for k, v in self.default_settings_dict.items()])
            f.write(settings_data)

global settings
settings = Settings()

##########
# VALUES #
##########
default_mz_value = 150
default_mz_range = 0.4
default_RT_value = 1/6
default_RT_range = 1/6

###########
# ファイル #
###########
def new_dir_path_wo_overlap(dir_path_base, spacing="_"):
    dir_path_output = dir_path_base
    i = 0
    while dir_path_output.exists():
        i += 1
        dir_path_output = dir_path_base.parent / f"{dir_path_base.name}{spacing}{i}"
    return dir_path_output
def new_file_path_wo_overlap(file_path, spacing="_"):
    # 未検証！
    file_path_output = file_path
    i = 0
    while file_path_output.exists():
        i += 1
        file_path_output = (file_path.parent / f"{file_path.stem}{spacing}{i}").with_suffix(file_path.suffix)
    return file_path_output





