# -*- coding: utf-8 -*-

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
    QItemSelection, 
)

from ..widgets import my_table_widgets as mtw
from ..widgets import my_widgets as mw
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
    def del_selected_compound(self):
        indices = self.compound_table.selectionModel().selectedRows()
        for index in sorted(indices):
            self.compound_table.del_row(index.row())
        return max(map(lambda index: index.row(), indices))
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
    def get_data_items_by_formula(self):
        return [item for item in self.compound_table.model.items if item["formula"] != ""]
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
        # add targets
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
    def update_info_of_selected_target(self, **item_kwargs):
        selected_rows = self.compound_table.selectionModel().selectedRows()
        if len(selected_rows) == 0:
            return
        elif len(selected_rows) != 1:
            raise Exception(f"Multple selection is not allowed!")
        self.compound_table.model.edit_data(selected_rows[0].row(), item_kwargs)
    def __getattr__(self, k):
        return getattr(self.compound_table, k)



