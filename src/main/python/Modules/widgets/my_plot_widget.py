# -*- coding: utf-8 -*-

import fractions
import numpy as np
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import (
    QWidget, 
    QHBoxLayout, 
)

from PyQt6.QtCore import (
    Qt, 
    pyqtSignal, 
    QRectF, 
)
from PyQt6.QtGui import (
    QLinearGradient, 
    QColor, 
    QBrush, 
)
from . import my_widgets as mw
from PyQt6.QtWidgets import QSizePolicy
import pyqtgraph as pg
from pyqtgraph import Point
from pyqtgraph import functions as fn
from pyqtgraph.exporters import SVGExporter
from pyqtgraph.graphicsItems import GradientEditorItem

from pyqtgraph.Qt import QtGui
import numpy as np
from pyqtgraph.Point import Point
from pyqtgraph import debug as debug

from ..config import style

def make_label_html(text="", size=2):
    return f"<font size='{size}' color='#808080'>{text}</font>"

class MyPlotDataItem(pg.PlotDataItem):
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
    # you have to add "paint" function to avoid error when exporting SVG image by SVGExporter.
    def paint(self, *args, **kargs):
        pass

class MyViewBox(pg.ViewBox):
    view_box_clicked = pyqtSignal(float, float)
    def __init__(self, parent=None, border=None, lockAspect=False, enableMouse=True, invertY=False, enableMenu=True, name=None, invertX=False, defaultPadding=0.02):
        super().__init__(parent, border, lockAspect, enableMouse, invertY, enableMenu, name, invertX, defaultPadding)
    def isInViewRange(self, x_value, y_value):
        (min_x, max_x), (min_y, max_y) = self.viewRange()
        if (min_x < x_value < max_x) and (min_y < y_value < max_y):
            return True
        else:
            return False
    def mouseClickEvent(self, ev):
        # If ev.accept() is called, ev will not be passed to the parent plotItem.
        if ev.button() == Qt.MouseButton.LeftButton:
            ev.accept()
            # シグナル発火
            xy_position = self.mapSceneToView(ev.scenePos())
            x_value = xy_position.x()
            y_value = xy_position.y()
            # 表示範囲内のみアクセプト
            if self.isInViewRange(x_value, y_value):
                self.view_box_clicked.emit(x_value, y_value)
        elif ev.button() == Qt.RightButton and self.menuEnabled():
            ev.accept()
            self.raiseContextMenu(ev)

class MyPlotItem(pg.PlotItem):
    padding_x = 0.1
    padding_y = 0.1
    def __init__(self, parent=None, name=None, labels=None, title=None, viewBox=None, axisItems=None, enableMenu=True, **kargs):
        super().__init__(parent, name, labels, title, viewBox, axisItems, enableMenu, **kargs)
        # ignore autoBtn forever
        self.autoBtn.hide()
    # ignore autoBtn forever
    def updateButtons(self):
        pass    # ignore
    def calc_my_y_range(self, y_min, y_max):
        padding_y = (y_max - y_min) * self.padding_y
        y_btm = min(0, y_min - padding_y)
        y_top = y_max + y_min - y_btm
        return y_btm, y_top
    def setMyRange(self, x_min, x_max, y_min, y_max):
        y_btm, y_top = self.calc_my_y_range(y_min, y_max)
        self.setRange(xRange=(x_min, x_max), yRange=(y_btm, y_top), padding=0)
    def setMyYRange(self, y_min, y_max):
        y_btm, y_top = self.calc_my_y_range(y_min, y_max)
        self.setYRange(y_btm, y_top, padding=0)
    def setMyXRange(self, x_min, x_max):
        x_range = x_max - x_min
        x_min, x_max = x_min - x_range * self.padding_x, x_max + x_range * self.padding_x
        super().setXRange(x_min, x_max, padding=0)
        return x_min, x_max
    def setXRange(self, x_min, x_max, padding):
        super().setXRange(x_min, x_max, padding=padding)
    def setYRange(self, y_min, y_max, padding):
        super().setYRange(y_min, y_max, padding=padding)
    def viewRange_x(self):
        return self.viewRange()[0]
    def viewRange_y(self):
        return self.viewRange()[1]

class MyPlotWidgetBase(pg.PlotWidget):
    view_box_clicked = pyqtSignal(float, float)
    def __init__(self, plot_item):
        super().__init__(plotItem=plot_item)
        # 設定
        self.vb().setMouseMode(pg.ViewBox.RectMode)
        self.disableAutoRange(axis="xy")
        # イベントコネクト
        self.vb().view_box_clicked.connect(lambda x, y: self.view_box_clicked.emit(x, y))
    def vb(self):
        return self.plotItem.vb
    # disable wheel event (event will be passed to QScrollArea)
    def wheelEvent(self, ev, axis=None):
        self.parent().parent().parent().wheelEvent(ev)
    @staticmethod
    def get_local_minmax(x_list, y_list, min_x, max_x):
        if x_list is None:
            return None, None
        local_area = (min_x <= x_list) & (x_list <= max_x)
        local_y = y_list[local_area]
        if len(local_y) > 0:
            return local_y.min(), local_y.max()
        else:
            return None, None
    def export_svg(self, save_path):
        svg_data = SVGExporter(self.scene())
        svg_data.export(fileName=save_path)
        # データの背景を変更（なぜか黒になってしまっている）
        tree = ET.parse(save_path)
        svg = tree.getroot()
        toplevel_rect = svg.findall("{http://www.w3.org/2000/svg}rect")
        if len(toplevel_rect) == 1:
            toplevel_rect = toplevel_rect[0]
        else:
            raise Exception("more than 1 master rect")
        toplevel_rect.set("style", "fill:none")
        # 上書き保存
        tree = ET.ElementTree(element=svg)
        tree.write(save_path, encoding='utf-8', xml_declaration=True)

class MyImageWidget(MyPlotWidgetBase):
    left_axis_width = 50
    def __init__(self):
        exp_axisitem = pg.AxisItem(orientation='left', maxTickLength=5)
        exp_axisitem.setWidth(w=self.left_axis_width)
        RT_axisitem = pg.AxisItem(orientation='bottom', maxTickLength=5)
        plot_item = MyPlotItem(viewBox=MyViewBox(), axisItems={'left':exp_axisitem, 'bottom':RT_axisitem})
        super().__init__(plot_item)
        # items
        self.image0 = pg.ImageItem()
        self.histogram0 = MyHistogramLUTWidget(orientation="horizontal")
        # connect image and histogram
        self.histogram0.setImageItem(self.image0)
        # add item
        self.addItem(self.image0)
    def set_image(self, img):
        self.image0.setImage(np.rot90(img, -1))
    def set_range_of_image(self, x_range, y_range):
        N_x_pixel, N_y_pixel = self.image0.image.shape
        x_scale = (x_range[1] - x_range[0]) / N_x_pixel # scale=length_on_axis/pixel
        y_scale = (y_range[1] - y_range[0]) / N_y_pixel # scale=length_on_axis/pixel
        tr = QtGui.QTransform()  # prepare ImageItem transformation:
        tr.translate(x_range[0], y_range[0]) # move image
        tr.scale(x_scale, y_scale)       # (horizontal, vertical)
        self.image0.setTransform(tr) # assign transform
    def get_intensity_min_max(self):
        # shape
        x_view_range, y_view_range = self.vb().viewRange()
        # 平行移動、拡大移動の値
        x_translate = self.image0.transform().dx()
        y_translate = self.image0.transform().dy()
        x_scale = self.image0.transform().m11()
        y_scale = self.image0.transform().m22()
        # 画像のピクセル上での位置
        x_pixel_view_range = ((np.array(x_view_range) - x_translate) / x_scale).astype(int)
        y_pixel_view_range = ((np.array(y_view_range) - y_translate) / y_scale).astype(int)
        target_pixel = self.image0.image[max(x_pixel_view_range[0], 0):x_pixel_view_range[-1] + 1, max(y_pixel_view_range[0], 0):y_pixel_view_range[-1] + 1]
        # 最大値・最小値を返す
        return target_pixel.min(), target_pixel.max()
    def set_contrast(self, inten_min, inten_max):
        self.image0.setLevels((inten_min, inten_max))

class MyPlotWidget(MyPlotWidgetBase):
    left_axis_width = 40
    def __init__(self):
        exp_axisitem = ExpAxisItem(orientation='left', maxTickLength=5)
        exp_axisitem.setWidth(w=self.left_axis_width)
        RT_axisitem = pg.AxisItem(orientation='bottom', maxTickLength=5)
        plot_item = MyPlotItem(viewBox=MyViewBox(), axisItems={'left':exp_axisitem, 'bottom':RT_axisitem})
        super().__init__(plot_item=plot_item)
        # items
        self.plot0 = MyPlotDataItem()
        self.plot1 = MyPlotDataItem()
        self.region0 = pg.LinearRegionItem(pen=style.main_r_pen(), brush=style.main_r_brush())
        # add items
        self.addItem(self.plot0)
        self.addItem(self.plot1)
        self.addItem(self.region0)
        # order
        self.plot0.setZValue(2)

        # 情報表示用テキストボックス
        exp_axisitem.exp_item.setParentItem(self.vb())
        self.top_right_label = pg.TextItem(anchor=(1, 0), html=make_label_html())
        self.top_right_label.setParentItem(self.vb())
        # イベントコネクト
        self.vb().sigResized.connect(self.vb_resized)

    def get_x_bounds_plot0(self):
        return np.nanmin(self.plot0.xData), np.nanmax(self.plot0.xData)
    def get_y_bounds_plot0(self):
        return np.nanmin(self.plot0.yData), np.nanmax(self.plot0.yData)
    def get_displayed_y_bounds_plot0(self, x_min, x_max):
        return self.get_local_minmax(self.plot0.xData, self.plot0.yData, x_min, x_max)
    def setMyYRange_within_x_view_range(self):
        x_view_range, y_view_range = self.viewRange()
        y_min, y_max = self.get_displayed_y_bounds_plot0(*x_view_range)
        if y_min is None:
            return
        else:
            self.setMyYRange(y_min, y_max)
    # windowサイズ変更時、テキストボックスの位置を調整する
    def vb_resized(self, vb=None):
        self.top_right_label.setPos(vb.screenGeometry().width(), 0)
    def set_top_right_label_html(self, text):
        self.top_right_label.setHtml(text)

# tickStrings で i (tickLevel) を参照するためのベースクラス。
class ExpAxisItem(pg.AxisItem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exp = np.nan
        self.isTickDetermined = False
        self.enableAutoSIPrefix(False)
        # 指数表記用テキストボックス
        self.exp_item = pg.TextItem(anchor=(0, 0), html=make_label_html("e0"))
    def generateDrawSpecs(self, p):
        """
        Calls tickValues() and tickStrings() to determine where and how ticks should
        be drawn, then generates from this a set of drawing commands to be
        interpreted by drawPicture().
        """
        profiler = debug.Profiler()
        if self.style['tickFont'] is not None:
            p.setFont(self.style['tickFont'])
        bounds = self.mapRectFromParent(self.geometry())

        linkedView = self.linkedView()
        if linkedView is None or self.grid is False:
            tickBounds = bounds
        else:
            tickBounds = linkedView.mapRectToItem(self, linkedView.boundingRect())

        if self.orientation == 'left':
            span = (bounds.topRight(), bounds.bottomRight())
            tickStart = tickBounds.right()
            tickStop = bounds.right()
            tickDir = -1
            axis = 0
        elif self.orientation == 'right':
            span = (bounds.topLeft(), bounds.bottomLeft())
            tickStart = tickBounds.left()
            tickStop = bounds.left()
            tickDir = 1
            axis = 0
        elif self.orientation == 'top':
            span = (bounds.bottomLeft(), bounds.bottomRight())
            tickStart = tickBounds.bottom()
            tickStop = bounds.bottom()
            tickDir = -1
            axis = 1
        elif self.orientation == 'bottom':
            span = (bounds.topLeft(), bounds.topRight())
            tickStart = tickBounds.top()
            tickStop = bounds.top()
            tickDir = 1
            axis = 1
        else:
            raise ValueError("self.orientation must be in ('left', 'right', 'top', 'bottom')")
        #print tickStart, tickStop, span

        ## determine size of this item in pixels
        points = list(map(self.mapToDevice, span))
        if None in points:
            return
        lengthInPixels = Point(points[1] - points[0]).length()
        if lengthInPixels == 0:
            return

        # Determine major / minor / subminor axis ticks
        if self._tickLevels is None:
            tickLevels = self.tickValues(self.range[0], self.range[1], lengthInPixels)
            tickStrings = None
        else:
            ## parse self.tickLevels into the formats returned by tickLevels() and tickStrings()
            tickLevels = []
            tickStrings = []
            for level in self._tickLevels:
                values = []
                strings = []
                tickLevels.append((None, values))
                tickStrings.append(strings)
                for val, strn in level:
                    values.append(val)
                    strings.append(strn)

        ## determine mapping between tick values and local coordinates
        dif = self.range[1] - self.range[0]
        if dif == 0:
            xScale = 1
            offset = 0
        else:
            if axis == 0:
                xScale = -bounds.height() / dif
                offset = self.range[0] * xScale - bounds.height()
            else:
                xScale = bounds.width() / dif
                offset = self.range[0] * xScale

        xRange = [x * xScale - offset for x in self.range]
        xMin = min(xRange)
        xMax = max(xRange)

        profiler('init')

        tickPositions = [] # remembers positions of previously drawn ticks

        ## compute coordinates to draw ticks
        ## draw three different intervals, long ticks first
        tickSpecs = []
        for i in range(len(tickLevels)):
            tickPositions.append([])
            ticks = tickLevels[i][1]

            ## length of tick
            tickLength = self.style['tickLength'] / ((i*0.5)+1.0)
                
            lineAlpha = self.style["tickAlpha"]
            if lineAlpha is None:
                lineAlpha = 255 / (i+1)
                if self.grid is not False:
                    lineAlpha *= self.grid/255. * fn.clip_scalar((0.05  * lengthInPixels / (len(ticks)+1)), 0., 1.)
            elif isinstance(lineAlpha, float):
                lineAlpha *= 255
                lineAlpha = max(0, int(round(lineAlpha)))
                lineAlpha = min(255, int(round(lineAlpha)))
            elif isinstance(lineAlpha, int):
                if (lineAlpha > 255) or (lineAlpha < 0):
                    raise ValueError("lineAlpha should be [0..255]")
            else:
                raise TypeError("Line Alpha should be of type None, float or int")

            for v in ticks:
                ## determine actual position to draw this tick
                x = (v * xScale) - offset
                if x < xMin or x > xMax:  ## last check to make sure no out-of-bounds ticks are drawn
                    tickPositions[i].append(None)
                    continue
                tickPositions[i].append(x)

                p1 = [x, x]
                p2 = [x, x]
                p1[axis] = tickStart
                p2[axis] = tickStop
                if self.grid is False:
                    p2[axis] += tickLength*tickDir
                tickPen = self.pen()
                color = tickPen.color()
                color.setAlpha(int(lineAlpha))
                tickPen.setColor(color)
                tickSpecs.append((tickPen, Point(p1), Point(p2)))
        profiler('compute ticks')


        if self.style['stopAxisAtTick'][0] is True:
            minTickPosition = min(map(min, tickPositions))
            if axis == 0:
                stop = max(span[0].y(), minTickPosition)
                span[0].setY(stop)
            else:
                stop = max(span[0].x(), minTickPosition)
                span[0].setX(stop)
        if self.style['stopAxisAtTick'][1] is True:
            maxTickPosition = max(map(max, tickPositions))
            if axis == 0:
                stop = min(span[1].y(), maxTickPosition)
                span[1].setY(stop)
            else:
                stop = min(span[1].x(), maxTickPosition)
                span[1].setX(stop)
        axisSpec = (self.pen(), span[0], span[1])


        textOffset = self.style['tickTextOffset'][axis]  ## spacing between axis and text
        #if self.style['autoExpandTextSpace'] is True:
            #textWidth = self.textWidth
            #textHeight = self.textHeight
        #else:
            #textWidth = self.style['tickTextWidth'] ## space allocated for horizontal text
            #textHeight = self.style['tickTextHeight'] ## space allocated for horizontal text

        textSize2 = 0
        lastTextSize2 = 0
        textRects = []
        textSpecs = []  ## list of draw

        # If values are hidden, return early
        if not self.style['showValues']:
            return (axisSpec, tickSpecs, textSpecs)

        for i in range(min(len(tickLevels), self.style['maxTextLevel']+1)):
            ## Get the list of strings to display for this level
            if tickStrings is None:
                spacing, values = tickLevels[i]
                strings = self.tickStrings(values, self.autoSIPrefixScale * self.scale, spacing, i)
            else:
                strings = tickStrings[i]

            if len(strings) == 0:
                continue

            ## ignore strings belonging to ticks that were previously ignored
            for j in range(len(strings)):
                if tickPositions[i][j] is None:
                    strings[j] = None

            ## Measure density of text; decide whether to draw this level
            rects = []
            for s in strings:
                if s is None:
                    rects.append(None)
                else:
                    br = p.boundingRect(QRectF(0, 0, 100, 100), Qt.AlignmentFlag.AlignCenter, s)
                    ## boundingRect is usually just a bit too large
                    ## (but this probably depends on per-font metrics?)
                    br.setHeight(br.height() * 0.8)

                    rects.append(br)
                    textRects.append(rects[-1])

            if len(textRects) > 0:
                ## measure all text, make sure there's enough room
                if axis == 0:
                    textSize = np.sum([r.height() for r in textRects])
                    textSize2 = np.max([r.width() for r in textRects])
                else:
                    textSize = np.sum([r.width() for r in textRects])
                    textSize2 = np.max([r.height() for r in textRects])
            else:
                textSize = 0
                textSize2 = 0

            if i > 0:  ## always draw top level
                ## If the strings are too crowded, stop drawing text now.
                ## We use three different crowding limits based on the number
                ## of texts drawn so far.
                textFillRatio = float(textSize) / lengthInPixels
                finished = False
                for nTexts, limit in self.style['textFillLimits']:
                    if len(textSpecs) >= nTexts and textFillRatio >= limit:
                        finished = True
                        break
                if finished:
                    break
            
            lastTextSize2 = textSize2

            #spacing, values = tickLevels[best]
            #strings = self.tickStrings(values, self.scale, spacing)
            # Determine exactly where tick text should be drawn
            for j in range(len(strings)):
                vstr = strings[j]
                if vstr is None: ## this tick was ignored because it is out of bounds
                    continue
                x = tickPositions[i][j]
                #textRect = p.boundingRect(QRectF(0, 0, 100, 100), Qt.AlignmentFlag.AlignCenter, vstr)
                textRect = rects[j]
                height = textRect.height()
                width = textRect.width()
                #self.textHeight = height
                offset = max(0,self.style['tickLength']) + textOffset

                if self.orientation == 'left':
                    alignFlags = Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignVCenter
                    rect = QRectF(tickStop-offset-width, x-(height/2), width, height)
                elif self.orientation == 'right':
                    alignFlags = Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter
                    rect = QRectF(tickStop+offset, x-(height/2), width, height)
                elif self.orientation == 'top':
                    alignFlags = Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignBottom
                    rect = QRectF(x-width/2., tickStop-offset-height, width, height)
                elif self.orientation == 'bottom':
                    alignFlags = Qt.AlignmentFlag.AlignHCenter|Qt.AlignmentFlag.AlignTop
                    rect = QRectF(x-width/2., tickStop+offset, width, height)

                textFlags = alignFlags | Qt.TextFlag.TextDontClip    
                #p.setPen(self.pen())
                #p.drawText(rect, textFlags, vstr)
                textSpecs.append((rect, textFlags, vstr))
        profiler('compute text')

        ## update max text size if needed.
        self._updateMaxTextSize(lastTextSize2)

        return (axisSpec, tickSpecs, textSpecs)
    def tickStrings(self, values, scale, spacing, i):
        if self.logMode:
            return self.logTickStrings(values, scale, spacing)
        # i==0 の場合のみ処理
        if i == 0:
            self.isTickDetermined = False
            if max(map(abs, values)) == 0:
                return ["0.0"]
        # すべての場合で処理される可能性がある
        if len(values) == 0:
            return []
        if not self.isTickDetermined:
            exp = np.floor(np.log10(max(map(abs, values))))
            if exp != self.exp:
                self.exp_changed(exp)
                self.exp = exp
            self.isTickDetermined = True
        return list(map(lambda v: str(np.round(v / (10 ** self.exp), 1)), values))
    def exp_changed(self, exp):
        self.exp_item.setHtml(make_label_html(f"e{int(exp)}"))

class MyGradientWidget(mw.PaintableQWidget):
    gradient_bar_height = 15
    gradient_changed = pyqtSignal(object)
    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.setStyleSheet("MyGradientWidget{border-width:1px; border-style:solid; border-color:black; background-color:black}")
        # アイテム
        self.gradient_bar = QWidget()
        self.gradient_bar.setAutoFillBackground(True)
        # レイアウト
        self.setLayout(QHBoxLayout())
        self.layout().setContentsMargins(1,1,1,1)
        self.layout().addWidget(self.gradient_bar)
        # 初期化
        self.set_gradient(default_gradient_info)
    def set_gradient(self, gradient_info):
        # カラーモードなど
        if isinstance(gradient_info, str):
            gradient_info = GradientEditorItem.Gradients[gradient_info]
        color_mode = gradient_info["mode"]
        # パレット準備
        p = self.gradient_bar.palette()
        gradient = QLinearGradient(0, 0, 1, 0)# QPointF(0, 0), QPointF(20, 0))
        gradient.setCoordinateMode(gradient.CoordinateMode.ObjectMode)
        for tick, color_values in gradient_info["ticks"]:
            if color_mode == "rgb":
                gradient.setColorAt(tick, QColor(*color_values))
            else:
                raise Exception(f"unknown color_mode {color_mode}")
        p.setBrush(self.gradient_bar.backgroundRole(), QBrush(gradient))#QBrush(gradient))
        self.gradient_bar.setPalette(p)
        self.gradient_bar.setFixedHeight(self.gradient_bar_height)
        # event emit
        self.gradient_changed.emit(gradient_info)

default_gradient_info = "plasma" # "thermal" # "flame" # "yellowy" # "viridis" # "inferno" # "plasma" # "magma" # {'ticks': [(0.0, (0, 0, 3, 255)), (0.25, (80, 18, 123, 255)), (0.5, (182, 54, 121, 255)), (0.75, (251, 136, 97, 255)), (1.0, (251, 252, 191, 255))], 'mode': 'rgb'}

class MyGradientGraph(pg.PlotWidget):
    fixed_height = 50
    sig_region_changed = pyqtSignal(float, float)
    sig_region_change_finished = pyqtSignal(float, float)
    def __init__(self, parent=None, background='default', plotItem=None, **kargs):
        super().__init__(parent, background, plotItem, **kargs)
        self.plotItem.hideAxis('left')
        self.setFixedHeight(self.fixed_height)
        self.region0 = pg.LinearRegionItem(values=[0, 0], orientation="vertical")
        self.addItem(self.region0)
        # イベントコネクト
        self.region0.sigRegionChanged.connect(lambda x: self.sig_region_changed.emit(*self.region0.getRegion()))
        self.region0.sigRegionChangeFinished.connect(lambda x: self.sig_region_change_finished.emit(*self.region0.getRegion()))
    def setEnabled(self, enable):
        self.region0.setMovable(enable)
    def setValue(self, contrast):
        self.region0.setRegion(contrast)
    def adjust_view_range(self):
        btm, top = self.region0.getRegion()
        d = top - btm
        self.setXRange(btm - d / 2, top + d / 2, padding=0)

class MyHistogramLUTWidget(pg.HistogramLUTWidget):
    def __init__(self, parent=None, *args, **kargs):
        self.ignore_event = False
        super().__init__(parent, *args, **kargs)
        assert self.levelMode == "mono"
        self.init_ticks()
        # items
        self.min_level = pg.SpinBox()
        self.min_level.setOpts(finite=True)
        self.max_level = pg.SpinBox()
        self.max_level.setOpts(finite=True)


        # gradient = "grey"
        self.load_gradient(default_gradient_info)

        # イベントコネクト
        self.regions[0].sigRegionChanged.connect(self.histogram_level_changed)
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
    def init_ticks(self):
        for tick in self.gradient.ticks:
            tick.movable = False
            tick.pen = pg.mkPen({"color":"#000000"})
            tick.hoverPen = pg.mkPen({"color":"#000000"})
            tick.currentPen = pg.mkPen({"color":"#000000"})
            tick.update()
    def load_gradient(self, gradient):
        if isinstance(gradient, str):
            self.gradient.loadPreset(gradient)
        elif isinstance(gradient, dict):
            self.gradient.restoreState(gradient)
        self.init_ticks()

    @event_process_deco
    def histogram_level_changed(self, region_item):
        level = region_item.getRegion()
        print(level)


