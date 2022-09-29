# -*- coding: utf-8 -*-

from PyQt6.QtCore import (
    pyqtSignal, 
)
from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QHBoxLayout, 
    QWidget, 
    QCheckBox, 
    QPushButton, 
)

import pyqtgraph as pg
import numpy as np
from . import my_plot_widget as mpw

class OpenedFilesCheckbox(QWidget):
    btn_ok_clicked = pyqtSignal(list)
    btn_cancel_clicked = pyqtSignal()
    def __init__(self, rpd_list) -> None:
        super().__init__()
        # buttons
        self.btn_ok = QPushButton("Ok")
        self.btn_ok.setDefault(True)
        self.btn_cancel = QPushButton("Cancel")
        # layout
        self.ckbx_layout = QVBoxLayout()        
        for rpd in rpd_list:
            file_path_ckbx = QCheckBox(str(rpd.file_path))
            file_path_ckbx.setChecked(True)
            file_path_ckbx.rpd = rpd
            self.ckbx_layout.addWidget(file_path_ckbx)
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        self.setLayout(QVBoxLayout())
        self.layout().addLayout(self.ckbx_layout)
        self.layout().addLayout(btn_layout)
        # connect event
        self.btn_ok.clicked.connect(lambda x: self.btn_ok_clicked.emit(self.get_file_path_list_with_check()))
        self.btn_cancel.clicked.connect(lambda x: self.btn_cancel_clicked.emit())
        # focus
        self.btn_ok.setFocus()
    def get_ckbx_list(self):
        return [self.ckbx_layout.itemAt(i).widget() for i in range(self.ckbx_layout.count())]
    def get_file_path_list_with_check(self):
        return [file_path_checkbox.rpd for file_path_checkbox in self.get_ckbx_list() if file_path_checkbox.isChecked()]

class MzRTImage2D(QWidget):
    def __init__(self, window_title=""):
        super().__init__()
        self.setWindowTitle(window_title)
        self.image_widget = mpw.MyImageWidget()
        # layout
        self.setLayout(QHBoxLayout())
        self.layout().addWidget(self.image_widget)
        self.layout().addWidget(self.image_widget.histogram0)
    def set_image(self, img, x_range, y_range):
        self.image_widget.set_image(img)
        self.image_widget.set_range_of_image(x_range, y_range)



