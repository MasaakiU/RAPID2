# -*- coding: utf-8 -*-

import numpy as np
from PyQt6.QtWidgets import (
    QTableView, 
    QStyledItemDelegate, 
    QHeaderView, 
    QLineEdit, 
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QGridLayout, 
    QLabel, 
    QStyle, 
)
from PyQt6.QtCore import (
    Qt, 
    QAbstractTableModel, 
    QEvent, 
    QModelIndex, 
    pyqtSignal, 
)
from PyQt6.QtGui import (
    QPalette, 
    QColor, 
    QFocusEvent, 
    QMouseEvent, 
)
from ..widgets import navigation_bar as nb
from ..process import atomic_ratio as ar

class AbstractWidgetInsideCompoundCell(QWidget):
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.installEventFilter(self)
    def compound_cell(self):
        return self.parent().parent()
    def eventFilter(self, object, event) -> bool:
        if isinstance(event, QFocusEvent):
            self.compound_cell().set_selection(event)
        elif isinstance(event, QMouseEvent) and isinstance(self, BtnTIC):
            if event.type() == 2:   # pressed
                focus_event = QFocusEvent(QEvent.Type.FocusIn, Qt.FocusReason.MouseFocusReason)
                self.compound_cell().set_selection(focus_event)
        return super().eventFilter(object, event)
class RTSpinBox(nb.RTSpinBox, AbstractWidgetInsideCompoundCell):
    pass
class RTRangeBox(nb.RTRangeBox, AbstractWidgetInsideCompoundCell):
    pass
class MzSpinBox(nb.MzSpinBox, AbstractWidgetInsideCompoundCell):
    pass
class MzRangeBox(nb.MzRangeBox, AbstractWidgetInsideCompoundCell):
    pass
class CompoundName(QLineEdit, AbstractWidgetInsideCompoundCell):
    pass
class Formula(QLineEdit, AbstractWidgetInsideCompoundCell):
    enter_pressed = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.setPlaceholderText("Formula")
        self.setToolTip("test")
    def keyPressEvent(self, key_event):
        if (key_event.key() == 16777220):# and (key_event.modifiers() == Qt.KeyboardModifier.ControlModifier):
            self.enter_pressed.emit()
        return super().keyPressEvent(key_event)

class M_over_Z(QLabel, AbstractWidgetInsideCompoundCell):
    decimal = 5
    def __init__(self, *keys, **kwargs):
        super().__init__(*keys, **kwargs)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
    def setText_by_formula(self, formula):
        m = ar.e.calc_exact_mass(formula=formula)
        z = ar.e.calc_charge(formula=formula)
        if z == 0:
            z = 1
        self.setText(str(np.round(abs(m/z), self.decimal)))
class BtnTIC(nb.BtnTIC, AbstractWidgetInsideCompoundCell):
    pass

class CompoundCell(QWidget):
    m_over_z_width = 75
    def __init__(self, parent, index):
        super().__init__(parent)
        self.unique_data_id = None
        self.RT_box = RTSpinBox()
        self.RT_range_box = RTRangeBox()
        self.mz_box = MzSpinBox()
        self.mz_range_box = MzRangeBox()
        self.compound_name = CompoundName()
        self.formula = Formula()
        self.m_over_z = M_over_Z("0")
        self.m_over_z.setFixedWidth(self.m_over_z_width)
        self.btn_TIC = BtnTIC()
        # layout1
        top_layout = QGridLayout()
        top_layout.setContentsMargins(0,0,0,0)
        top_layout.addWidget(self.compound_name, 0, 0, 1, 2)
        top_layout.addWidget(self.btn_TIC, 0, 2, 1, 1)
        top_layout.addWidget(self.formula, 1, 0, 1, 1)
        top_layout.addWidget(self.m_over_z, 1, 1, 1, 2)
        inner_layout = QGridLayout()
        inner_layout.setContentsMargins(2,2,2,2)
        inner_layout.setSpacing(0)
        inner_layout.addLayout(top_layout, 0, 0, 1, -1)
        inner_layout.addWidget(QLabel("RT:"), 1, 0)
        inner_layout.addWidget(self.RT_box, 1, 1)
        inner_layout.addWidget(QLabel("±"), 1, 2)
        inner_layout.addWidget(self.RT_range_box, 1, 3)
        inner_layout.addWidget(QLabel("mz:"), 2, 0)
        inner_layout.addWidget(self.mz_box, 2, 1)
        inner_layout.addWidget(QLabel("±"), 2, 2)
        inner_layout.addWidget(self.mz_range_box, 2, 3)
        # layout2
        self.inner_widget = QWidget()
        self.inner_widget.setLayout(inner_layout)
        self.inner_widget.setAutoFillBackground(True)
        # whole layout
        self.setLayout(QVBoxLayout())
        self.layout().setContentsMargins(2,2,2,2)
        self.layout().addWidget(self.inner_widget)
        # イベントコネクト
        self.pass_signal_to_presenter = True
        self.compound_name.textChanged.connect(self.compound_name_changed)
        self.formula.textChanged.connect(self.formula_changed)
        self.formula.enter_pressed.connect(self.formula_enter_pressed)
        self.btn_TIC.clicked.connect(self.btn_TIC_clicked)
        self.RT_box.valueChanged.connect(self.RT_changed)
        self.RT_range_box.valueChanged.connect(self.RT_range_changed)
        self.mz_box.valueChanged.connect(self.mz_changed)
        self.mz_range_box.valueChanged.connect(self.mz_range_changed)
    def table_view(self):
        return self.parent().parent()
    def model(self):
        return self.table_view().model
    def index(self):
        for row, item in enumerate(self.model().items):
            if item["unique_data_id"] == self.unique_data_id:
                return self.model().index(row, 0)
        else:
            raise Exception("Critical Error!")
    def init_editor_widgets(self, data):
        self.unique_data_id = data["unique_data_id"]
        self.RT_box.setValue(data["RT"])
        self.RT_range_box.setValue(data["RT_range"])
        self.mz_box.setValue(data["mz"])
        self.mz_range_box.setValue(data["mz_range"])
        self.compound_name.setText(data["compound_name"])
        self.formula.setText(data["formula"])
        self.set_TIC(data["is_TIC"])
    def set_TIC(self, enable):
        self.btn_TIC.setChecked(enable)
        self.enable_mz_related_box(not enable)
    def enable_mz_related_box(self, enable):
        self.mz_box.setEnabled(enable)
        self.mz_range_box.setEnabled(enable)
    def paint(self, painter, option, index):
        p = self.inner_widget.palette()
        if QStyle.StateFlag.State_Selected in option.state: # (QStyle.StateFlag.State_Active in option.state)
            p.setColor(self.inner_widget.backgroundRole(), QColor("#99ccff"))
        else:
            p.setColor(self.inner_widget.backgroundRole(), Qt.GlobalColor.transparent)#.white)#
        self.inner_widget.setPalette(p)
    def set_selection(self, event):
        if isinstance(event, QFocusEvent):
            my_table_view = self.table_view()
            if event.type() == 8:   # focus in
                my_table_view.selectRow(self.index().row())
            elif event.type() == 9:   # focus out
                pass
                # my_table_view.clearSelection()
            else:
                raise Exception(f"unknown event type: {event.type()}")
    # user actions to change data in the widgets
    def compound_name_changed(self, compound_name):
        self.model().items.update(self.index().row(), compound_name=compound_name)
    def formula_changed(self, formula):
        self.model().items.update(self.index().row(), formula=formula)
        self.m_over_z.setText_by_formula(formula)
    def formula_enter_pressed(self):
        m_over_z = float(self.m_over_z.text())
        self.btn_TIC.setChecked(False)
        # edit data
        self.pass_signal_to_presenter = False
        self.btn_TIC_clicked(status=False)
        self.mz_box.setValue(m_over_z)
        self.pass_signal_to_presenter = True
        self.target_data_changed({"formula":[m_over_z, self.mz_range_box.value()]})
    def btn_TIC_clicked(self, status):
        self.enable_mz_related_box(not status)
        self.model().items.update(self.index().row(), is_TIC=status)
        self.target_data_changed({"TIC":status})
    def RT_changed(self, RT):
        self.model().items.update(self.index().row(), RT=RT)
        self.target_data_changed({"RT_related":[RT, self.RT_range_box.value()]})
    def RT_range_changed(self, RT_range):
        self.model().items.update(self.index().row(), RT_range=RT_range)
        self.target_data_changed({"RT_related":[self.RT_box.value(), RT_range]})
    def mz_changed(self, mz):
        self.model().items.update(self.index().row(), mz=mz)
        self.target_data_changed({"mz_related":[mz, self.mz_range_box.value()]})
    def mz_range_changed(self, mz_range):
        self.model().items.update(self.index().row(), mz_range=mz_range)
        self.target_data_changed({"mz_related":[self.mz_box.value(), mz_range]})
    def target_data_changed(self, dict):
        if self.pass_signal_to_presenter:
            self.table_view().target_data_changed.emit(dict)

class MyDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return CompoundCell(parent, index)
    def setEditorData(self, editor, index):
        row = index.row()
        # column = index.column()
        data = index.model().items[row]
        if not isinstance(editor, CompoundCell):
            raise Exception("error!")
        # display data
        index.model().items.ignore_update = True
        editor.init_editor_widgets(data)
        index.model().items.ignore_update = False
    def paint(self, painter, option, index):
        # back
        option.palette.setColor(QPalette.ColorRole.Highlight, QColor("#99ccff"))
        super().paint(painter, option, index)
        # front (compound_cell)
        compound_cell = index.model().parent().indexWidget(index)
        compound_cell.paint(painter, option, index)

class MyTableView(QTableView):
    v_header_width = 30
    target_data_changed = pyqtSignal(dict)
    def __init__(self, width, parent=None):
        super().__init__(parent)        
        # model & delegate
        self.model = MyTableModel(parent=self)
        self.delegate = MyDelegate()
        self.setItemDelegateForColumn(0, self.delegate)
        self.setModel(self.model)
        # スタイル
        h_header = self.horizontalHeader()
        h_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(0, width - self.v_header_width - 2)
        h_header.hide()
        v_header = self.verticalHeader()
        v_header.setFixedWidth(self.v_header_width)
        # モード
        self.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        # イベントコネクト
        v_header.sectionPressed.connect(self.v_header_clicked)
        self.selection_changed = False
    def add_row(self, **item_kwargs):
        # add
        self.model.add_data(item_kwargs)
        # show compound_cell
        row_idx = self.model.rowCount() - 1
        index = self.model.index(row_idx, 0)
        self.openPersistentEditor(index)
        # adjust v_header
        self.verticalHeader().setSectionResizeMode(row_idx, QHeaderView.ResizeMode.ResizeToContents)
    def del_row(self, row):
        self.model.removeRows(row=row, count=1)
    def mousePressEvent(self, event):
        model_index = self.indexAt(event.pos())
        selected = self.selectionModel().isSelected(model_index)
        super().mousePressEvent(event)
        if selected:
            self.clearSelection()
    def mouseReleaseEvent(self, event):
        self.selection_changed = False  # reset
        return super().mouseReleaseEvent(event)
    def keyReleaseEvent(self, event):
        self.selection_changed = False  # reset
        return super().keyReleaseEvent(event)
    def keyPressEvent(self, event):
        # ignore every input except for up and down
        if event.key() in (16777235, 16777237):   # up or down
            return super().keyPressEvent(event)
        else:
            return
    def selectionChanged(self, *args):
        self.selection_changed = True
        super().selectionChanged(*args)
    def v_header_clicked(self, row):
        # model_index = self.model.index(row, 0)
        if not self.selection_changed:
            self.clearSelection()
        self.selection_changed = False  # reset

class MyTableModel(QAbstractTableModel):
    default_compound_name_prefix = "compound"
    def __init__(self, parent=None, items=[]):
        super().__init__(parent=parent)
        self.unique_data_id = 0
        self.items = Items(items)
    def add_data(self, item_kwargs):
        data_item = DataItem(item_kwargs)
        data_item.setdefault("compound_name", self.get_new_compound_name())
        data_item.setdefault("formula", "")
        data_item["unique_data_id"] = self.unique_data_id
        self.unique_data_id += 1
        self.items.append(data_item)
        self.layoutChanged.emit()
    def edit_data(self, row, item_kwargs):
        self.items.update(row, **item_kwargs)
        self.dataChanged.emit(self.index(row, 0), self.index(row, 0))
    def removeRows(self, row, count, parent=QModelIndex()):
        self.beginRemoveRows(parent, row, row + count - 1)
        del self.items[row:row + count]
        self.endRemoveRows()
        return True
    def get_new_compound_name(self):
        i = 1
        while not self.is_compound_name_unique(f"{self.default_compound_name_prefix} {i}"):
            i += 1
        return f"{self.default_compound_name_prefix} {i}"
    def is_compound_name_unique(self, compound_name):
        for item in self.items:
            if item["compound_name"] == compound_name:
                return False
        else:
            return True
    def data(self, index, role):
        if not index.isValid(): return
        if role == Qt.ItemDataRole.DisplayRole or role == Qt.ItemDataRole.EditRole:
            return self.items[index.row()]
    def rowCount(self, index=None):
        return len(self.items)
    def columnCount(self, index=None):
        return 1
    def flags(self, index):
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable

class Items(list):
    ignore_update = False
    def update(self, row, **kwargs):
        if not self.ignore_update:
            self[row].update(**kwargs)
class DataItem(dict):
    def __getattr__(self, k):
        return self[k]
    def copy(self):
        return DataItem(**self)


