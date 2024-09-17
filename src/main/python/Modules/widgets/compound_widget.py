# -*- coding: utf-8 -*-

import re
import copy
import numpy as np
import pandas as pd

from PyQt6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QTableWidgetItem, 
)
from PyQt6.QtGui import (
    QIcon, 
    QColor, 
)
from PyQt6.QtCore import (
    Qt, 
    pyqtSignal, 
    QCoreApplication, 

)
from ..widgets import my_table_widgets as mtw, popups
from ..widgets import my_widgets as mw
from ..widgets import adduct_ion_syntax as ais
from ..process import atomic_ratio as ar
from .. import general_functions as gf

class CompoundNavigator(QWidget):
    btn_width = 27
    margin = 5
    add_compound_clicked = pyqtSignal()
    del_compound_clicked = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        # widget
        self.btn_add_compound = mw.MyPushButton()
        self.btn_add_compound.setIcons(QIcon(str(gf.settings.btn_icon_path / "plus-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "plus-solid_white.svg")))
        self.btn_add_compound.setFixedWidth(self.btn_width)
        self.btn_del_compound = mw.MyPushButton()
        self.btn_del_compound.setIcons(QIcon(str(gf.settings.btn_icon_path / "minus-solid.svg")), QIcon(str(gf.settings.btn_icon_path / "minus-solid_white.svg")))
        self.btn_del_compound.setFixedWidth(self.btn_width)
        self.enable_btn_del(False)
        # layout
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(11,0,11,0)
        self.layout().setSpacing(self.margin)
        self.layout().addWidget(mw.RichLabel("Targets", font_type="boldfont"))
        self.layout().addStretch(1)
        self.layout().addWidget(self.btn_add_compound)
        self.layout().addWidget(self.btn_del_compound)
        # イベントコネクト
        self.btn_add_compound.clicked.connect(lambda x: self.add_compound_clicked.emit())
        self.btn_del_compound.clicked.connect(lambda x: self.del_compound_clicked.emit())
    def enable_btn_del(self, enable):
        self.btn_del_compound.setEnabled(enable)

class CompoundWidget(QWidget):
    width = 250
    new_compound_selected = pyqtSignal(dict)
    compound_deselected = pyqtSignal()
    target_data_changed = pyqtSignal(dict)
    compound_name_with_adduct_syntax = re.compile(r"^(.+)(\[M(?:[+-][0-9A-z]+)*\][0-9]*[+-])$")
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # widget
        self.compound_table = mtw.MyTableView(width=self.width)
        # layout
        self.setFixedWidth(self.width)
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(0,0,0,0)
        self.layout().addWidget(self.compound_table)
        # イベントコネクト
        self.compound_table.selectionModel().selectionChanged.connect(self.compound_selection_changed)
        self.compound_table.target_data_changed.connect(lambda data_item: self.target_data_changed.emit(data_item))
    def select_row(self, row):
        if row < 0:
            row = self.compound_table.model.rowCount() + row
        elif row >= self.compound_table.model.rowCount():
            row = self.compound_table.model.rowCount() - 1
        self.compound_table.selectRow(row)
        indices = self.compound_table.selectionModel().selectedRows()
        if len(indices) > 1:
            raise Exception("error!")
        return indices[0]
    def add_compound(self, **item_kwargs):   # mz, mz_range, RT, RT_range, is_TIC
        self.compound_table.add_row(**item_kwargs)
    def add_compound_by_data_items(self, data_items):
        self.pbar = popups.ProgressBar(N_max=len(data_items), message="Loading Targets")
        self.pbar.show()
        for data_item in data_items:
            self.add_compound(**data_item)
            self.pbar.add()
            QCoreApplication.processEvents()
    def del_selected_compound(self):
        indices = self.compound_table.selectionModel().selectedRows()
        for index in sorted(indices):
            self.compound_table.del_row(index.row())
        return max(map(lambda index: index.row(), indices))
    def del_all(self):
        for row in range(self.compound_table.model.rowCount())[::-1]:
            self.compound_table.del_row(row)
    def compound_selection_changed(self, item_selection):
        model_indexes = item_selection.indexes()
        if len(model_indexes) > 1:
            raise Exception("Multple selection is not allowed!")
        elif len(model_indexes) == 0:   # no selection
            self.compound_deselected.emit()
            return
        else:
            model_index = model_indexes[0]
        # model_index.row()
        data_item = self.compound_table.model.data(model_index, Qt.ItemDataRole.DisplayRole)
        self.new_compound_selected.emit(data_item)
    def get_data_item(self, row=None, index=None):
        if index is None:
            index = self.compound_table.model.index(row, 0)
        return self.compound_table.model.data(index, Qt.ItemDataRole.DisplayRole)
    def get_data_items(self):
        return self.compound_table.model.items
    def deepcopy_data_items(self):
        return copy.deepcopy(self.get_data_items())
    def get_data_items_with_formula(self):
        return [item for item in self.compound_table.model.items if item["formula"] != ""]
    def get_data_items_by_compound_name(self, compound_name):
        return [item for item in self.compound_table.model.items if item["compound_name"] == compound_name]
    def get_data_item_by_compound_name(self, compound_name):
        for item in self.compound_table.model.items:
            if item["compound_name"] == compound_name:
                return item
            else:
                None
    def load_targets(self, target_df):
        target_df = target_df.drop_duplicates(
            subset=[
                "compound_name", 
                "formula", 
                "is_TIC", 
                "m/z", 
                "m/z_range", 
                "RT", 
                "RT_range", 
                # "m/z_btm", 
                # "m/z_top", 
                # "RT_btm", 
                # "RT_top", 
            ]
        )
        # modify
        target_df = target_df.rename(columns={
            'm/z':'mz', 
            'm/z_range':'mz_range', 
            'm/z_btm':'mz_btm', 
            'm/z_top':'mz_top'
        })
        if "view_range_s_x" not in target_df.columns:
            target_df["view_range_s_x"] = list(map(lambda x: str(list(x)), zip(target_df["mz"] - 3, target_df["mz"] + 5)))
        if "view_range_c_x" not in target_df.columns:
            target_df["view_range_c_x"] = list(map(lambda x: str(list(x)), zip(target_df["RT"] - 2, target_df["RT"] + 2)))
        # add targets
        self.pbar = popups.ProgressBar(N_max=target_df.shape[0], message="Loading Targets")
        self.pbar.show()
        for i, s in target_df.iterrows():
            # modify
            s["view_range_s_x"] = eval(s["view_range_s_x"])
            s["view_range_c_x"] = eval(s["view_range_c_x"])
            if s["is_TIC"]:
                s["mz"] = gf.default_mz_value
                s["mz_range"] = gf.default_mz_range
            # set
            data_item = s[[
                "compound_name", 
                "formula", 
                "is_TIC", 
                "mz", 
                "mz_range", 
                "RT", 
                "RT_range", 
                "view_range_s_x", 
                "view_range_c_x"
            ]].to_dict()
            self.add_compound(**data_item)
            self.pbar.add()
            QCoreApplication.processEvents()
    def update_info_of_selected_target(self, **item_kwargs):
        selected_rows = self.compound_table.selectionModel().selectedRows()
        if len(selected_rows) == 0:
            return
        elif len(selected_rows) != 1:
            raise Exception(f"Multple selection is not allowed!")
        self.compound_table.model.edit_data(selected_rows[0].row(), item_kwargs)
    def get_compound_adduct_df(self) -> pd.DataFrame:
        compound_name_and_adduct_types = []
        for data_item in self.get_data_items():
            compound_name = data_item["compound_name"]
            m = self.compound_name_with_adduct_syntax.match(compound_name)
            if m is not None:
                compound_name_and_adduct_types.append((m.group(1), m.group(2)))
            else:
                compound_name_and_adduct_types.append((compound_name, "invalid_syntax"))
        # 集計
        df = pd.DataFrame(compound_name_and_adduct_types, columns=['compound_name', 'adduct_type'])
        result = pd.crosstab(df['compound_name'], df['adduct_type'])
        # assert df.isin([0, 1]).all().all()  # 重複がないことを確認 -> 確か、compound_name に重複を許してたはず（というか、チェックしてない？不確実情報）
        if "invalid_syntax" in result.columns:
            assert (result.query("invalid_syntax > 0").drop("invalid_syntax", axis=1) == 0).all().all()
        return result
    def get_all_adduct_types(self):
        adduct_types = list(self.get_compound_adduct_df().columns)
        if "invalid_syntax" in adduct_types:
            adduct_types.remove("invalid_syntax")
        return adduct_types
    def apply_adducts_to_all(self, adduct_list):
        adduct_types_df = self.get_compound_adduct_df()
        new_data_items = []
        invalid_formula_list = []
        for compound_name_without_adduct, s in adduct_types_df.iterrows():
            if ("invalid_syntax" in s.index) and (s["invalid_syntax"] > 0):
                detected_data_items = self.get_data_items_by_compound_name(compound_name_without_adduct)
                if len(detected_data_items) == 0:
                    raise Exception("error")
                new_data_items.extend(detected_data_items)
            else:
                # リスト中の最初のアダクト
                # adduct_ion_syntax 由来のリストにマッチするかを最優先に探す
                for base_adduct in adduct_list:
                    if base_adduct in s[s != 0].index:   # 絶対 data_item にあるはず
                        base_data_item = self.get_data_item_by_compound_name(f"{compound_name_without_adduct}{base_adduct}")
                        assert base_data_item is not None
                        break
                # adduct_ion_syntax 由来のリストにマッチするものがない場合、既存のものから探す
                else:
                    base_adduct = s[s != 0].index[0]
                    base_data_item = self.get_data_item_by_compound_name(f"{compound_name_without_adduct}{base_adduct}")
                    assert base_data_item is not None

                # 追加すべきアダクトを順次追加（adduct_ion_syntax 由来のリストの順番で追懐していく）
                for adduct in adduct_list:
                    formula_to_add_1, formula_to_sub_1, formula_for_total_charge_1 = ais.AdductIonSyntax.adduct_to_formula(base_adduct)
                    formula_to_add_2, formula_to_sub_2, formula_for_total_charge_2 = ais.AdductIonSyntax.adduct_to_formula(adduct)
                    formula_to_add_sum = ar.Formula.sum(formula_to_sub_1, formula_to_add_2)
                    formula_to_sub_sum = ar.Formula.sum(formula_to_add_1, formula_to_sub_2)
                    number_of_charge_1 = getattr(formula_for_total_charge_1, formula_for_total_charge_1.atomic_symbol_list[0])
                    number_of_charge_2 = getattr(formula_for_total_charge_2, formula_for_total_charge_2.atomic_symbol_list[0])
                    new_mz = (
                        base_data_item["mz"] * number_of_charge_1
                         + ar.e.calc_exact_mass(formula_to_add_sum)
                         - ar.e.calc_exact_mass(formula_to_sub_sum)
                    ) / number_of_charge_2
                    new_data_item = copy.deepcopy(base_data_item)
                    new_data_item["compound_name"] = f"{compound_name_without_adduct}{adduct}"
                    new_data_item["mz"] = new_mz
                    new_data_item["view_range_s_x"] = list(np.array(new_data_item["view_range_s_x"]) + new_mz - base_data_item["mz"])
                    if new_data_item["formula"] != "":
                        try:
                            skip_following_process = False
                            base_formula = ar.Formula(new_data_item["formula"])
                            # チャージの一致をチェック
                            if "+" in base_formula.atomic_symbol_list:
                                assert getattr(base_formula, "+") == getattr(formula_for_total_charge_1, "+")
                                base_formula.sub_number("+", getattr(base_formula, "+"))
                            elif "-" in base_formula.atomic_symbol_list:
                                assert getattr(base_formula, "-") == getattr(formula_for_total_charge_1, "-")
                                base_formula.sub_number("-", getattr(base_formula, "-"))
                            else:
                                skip_following_process = True
                            # アダクトを追加&除去
                            if not skip_following_process:
                                base_formula += formula_to_add_sum
                                base_formula -= formula_to_sub_sum
                                base_formula += formula_for_total_charge_2
                                new_data_item["formula"] = str(base_formula)
                            else:
                                invalid_formula_list.append(new_data_item["compound_name"])
                        except:
                            invalid_formula_list.append(new_data_item["compound_name"])
                    new_data_items.append(new_data_item)

        # アプデ
        self.del_all()
        self.add_compound_by_data_items(new_data_items)

        QCoreApplication.processEvents()
        #
        # redundant_target_list = []  # adduct_types_df で、値が2以上のもの
        # display: invalid_formula_list
        if len(invalid_formula_list) > 0:
            p = popups.WarningPopup(f"The formulas for the following compounds were not updated because the adducts could not be subtracted.")
            p.setDetailedText("\n".join(invalid_formula_list))
            p.exec()
    # def sync_RT_by_adduct(self, adduct_list):
    #     adduct_types_df = self.get_compound_adduct_df()
    #     data_items = self.get_data_items()
    #     for compound_name_without_adduct, s in adduct_types_df.iterrows():
    #         if ("invalid_syntax" in s.index) and (s["invalid_syntax"] > 0):
    #             continue
    #         else:
    #             # リスト中の最初のアダクト
    #             for data_item in data_items:
    #                 if data_item["compound_name"] == f"{compound_name_without_adduct}{adduct_list[0]}":
    #                     new_RT = data_item["RT"]
    #                     new_view_range_c_x = data_item["view_range_c_x"]
    #                     break
    #             else:
    #                 raise Exception("error")
    #             # RTを修正していく！
    #             for adduct, count in s.iteritems():
    #                 if count == 0:
    #                     continue
    #                 else:
    #                     number_of_modified_data_items = 0
    #                     for data_item in data_items:
    #                         if data_item["compound_name"] == f"{compound_name_without_adduct}{adduct}":
    #                             data_item["RT"] = new_RT
    #                             data_item["view_range_c_x"] = new_view_range_c_x
    #                             number_of_modified_data_items += 1
    #                     assert number_of_modified_data_items == count
    def __getattr__(self, k):
        return getattr(self.compound_table, k)



