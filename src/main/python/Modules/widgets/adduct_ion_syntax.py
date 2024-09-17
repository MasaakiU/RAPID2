# -*- coding: utf-8 -*-

import textwrap
import re

from PyQt6.QtCore import (
    pyqtSignal, 
)
from PyQt6.QtWidgets import (
    QVBoxLayout, 
    QHBoxLayout, 
    QWidget, 
    QLabel, 
    QCheckBox, 
    QPushButton, 
    QTextEdit, 
    QScrollArea, 
)
from PyQt6.QtCore import (
    Qt, 
    pyqtSignal, 
    QSize, 
)

from ..widgets import popups
from ..process import atomic_ratio as ar

class AdductIonSyntax(QWidget):
    sig_apply_btn_clicked = pyqtSignal(list)
    sig_sync_RT_btn_clicked = pyqtSignal(list)
    def __init__(self, main_window=None, window_title="adduct ion syntax", initial_adduct_list=[]):
        self.main_window = main_window
        super().__init__()
        self.setWindowTitle(window_title)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.text_edit = QTextEdit()
        self.text_edit.setAcceptRichText(False)
        self.text_edit.setText("\n".join(initial_adduct_list))

        # ボタン
        self.help_btn = QPushButton("Show Help")
        self.help_btn.setFixedWidth(120)
        self.sync_RT_btn = QPushButton("sync RT")
        self.sync_RT_btn.setFixedWidth(60)
        self.close_btn = QPushButton("close")
        self.close_btn.setFixedWidth(60)
        self.apply_btn = QPushButton("apply")
        self.apply_btn.setFixedWidth(60)

        help_description = QLabel(textwrap.dedent("""
            Before you begin, description of adducts must be added at the end of the compound name of the targets in the format of "[M<'+' or '-'><adduct>]<charge>".
            Targets whoes compound names do not meet the syntax will be ignored.
            In addition, redundancy of targets with the same compound name will be removed.
            Examples: 
                compound name[M]+
                compound name[M+Cl]-
                compound name[M+NH4]+
                compound name[M+2H]2+
                compound name[M-2H+Na]-
            To add/remove targets with different adducts, fill in the field below with the adducts you want.
            Adducts not in the field are removed from the target, and newly added adducts in the field are added to the target.
            The RT of the adduct listed at the top of the field has priority and is reflected in the RTs of all adducts that share the compound name.
        """).strip())
        help_description.setWordWrap(True)
        # help_description.setMinimumWidth(100)
        self.help = QScrollArea()
        self.help.setWidget(help_description)
        self.help.setWidgetResizable(True)
        self.help.hide()

        # layout
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0,0,0,0)
        btn_layout.addWidget(self.help_btn)
        # btn_layout.addWidget(self.sync_RT_btn)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.close_btn)
        btn_layout.addWidget(self.apply_btn)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(5,5,5,5)
        self.layout().setSpacing(5)
        self.layout().addWidget(self.help)
        self.layout().addWidget(self.text_edit)
        self.layout().addLayout(btn_layout)

        # シグナルコネクト
        self.help_btn.clicked.connect(self.help_btn_clicked)
        self.sync_RT_btn.clicked.connect(self.sync_RT_btn_clicked)
        self.close_btn.clicked.connect(self.close_btn_clicked)
        self.apply_btn.clicked.connect(self.apply_btn_clicked)

    def close_btn_clicked(self):
        self.close()

    def help_btn_clicked(self):
        if self.help_btn.text() == "Show Help":
            self.help_btn.setText("Hide Help")
            self.help.show()
        elif self.help_btn.text() == "Hide Help":
            self.help_btn.setText("Show Help")
            self.help.hide()
        else:
            raise Exception("error")

    def validate_adduct_list(func):
        def wrapper(self, *keys, **kwargs):
            # execute validation
            connected_adduct_list = self.text_edit.toPlainText().split("\n")
            for connected_adduct in connected_adduct_list:
                try:
                    formula_to_add, formula_to_sub, formula_for_total_charge = self.adduct_to_formula(connected_adduct)
                except:
                    p = popups.WarningPopup(f"invalid syntax:\n{connected_adduct}")
                    p.exec()
                    return
            # execute func
            return func(self, connected_adduct_list, *keys, **kwargs)
        return wrapper
    @validate_adduct_list
    def apply_btn_clicked(self, connected_adduct_list, *keys, **kwargs):
        self.sig_apply_btn_clicked.emit(connected_adduct_list)
    @validate_adduct_list
    def sync_RT_btn_clicked(self, connected_adduct_list, *keys, **kwargs):
        self.sig_sync_RT_btn_clicked.emit(connected_adduct_list)
    adduct_syntax = re.compile(r"^\[M(.*)\]([0-9]*)([+-])$")
    adduct_syntax_core = re.compile(r"([+-])([0-9A-z]+)")
    chemical_syntax = re.compile(r"^([0-9]*)([0-9A-z]+?)$")
    @classmethod
    def adduct_to_formula(cls, connected_adduct):
        m1 = cls.adduct_syntax.match(connected_adduct)
        all_adduct = m1.group(1)
        # チャージ
        if m1.group(2) == "":
            number_of_charge = 1
        else:
            number_of_charge = int(m1.group(2))
        formula_for_total_charge = ar.Formula("")
        formula_for_total_charge.add_number(m1.group(3), number_of_charge)

        # アダクト
        formula_to_add = ar.Formula("")
        formula_to_sub = ar.Formula("")
        m2 = cls.adduct_syntax_core.findall(all_adduct)
        for plus_or_minus, adduct in m2:
            m3 = cls.chemical_syntax.match(adduct)
            if m3.group(1) == "":
                number_of_adduct = 1
            else:
                number_of_adduct = int(m3.group(1))
            formula = ar.Formula(m3.group(2)) * number_of_adduct
            if plus_or_minus == "+":
                formula_to_add += formula
            elif plus_or_minus == "-":
                formula_to_sub += formula
            else:
                raise Exception("error")
        return formula_to_add, formula_to_sub, formula_for_total_charge



