# -*- coding: utf-8 -*-

from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QDoubleSpinBox, 
    QScrollArea, 
    QLabel, 
)
import pyqtgraph as pg

def main_c_pen():   # chromatogram
    return pg.mkPen("#1f77b4")
def main_s_pen():   # spectrum
    return pg.mkPen("#000000")
def main_r_pen():   # region_item
    return pg.mkPen("#FF000032", width=2)
def main_r_brush(): # region_item
    return pg.mkBrush("#FF000032")
def red_pen():
    return pg.mkPen("#FF0000")


# def target_r_pen(): # region_item
#     return pg.mkPen("#ff000032", width=2)
# def target_r_brush():
#     return pg.mkBrush("#ff000032")
mz_text_color = "#6464ff"
