from PyQt5 import QtWidgets, QtCore, QtGui


# 与 paradefine_newui.ui 中详细定义表保持一致（表头走 QSS，不走 CustomHeaderView 旧自绘）
PARAM_DETAIL_TABLE_QSS = """
QTableWidget {
    background-color: #ffffff;
    alternate-background-color: #f7f9fc;
    border: 1px solid #CCCCCC;
    gridline-color: #CCCCCC;
    color: #1f1f1f;
    selection-background-color: #d9e6f7;
    selection-color: #1f1f1f;
}
QHeaderView::section {
    background-color: #f3f5f8;
    color: #1f1f1f;
    border: 1px solid #CCCCCC;
    padding: 4px 6px;
    font-weight: 600;
}
"""

# 界面显示用表头（库字段仍为「参数单位」）
PARAM_DETAIL_HEADERS = ["参数名称", "参数值", "单位"]
PARAM_DETAIL_DATA_KEYS = ["参数名称", "参数值", "参数单位"]
PARAM_DETAIL_UNIT_COLUMN_WIDTH = 56
# 参数值列初始宽度下限；实际还会按视口宽度按比例再分配
PARAM_DETAIL_VALUE_COLUMN_WIDTH = 240
# 剩余宽度中参数值约占比例（名称列仍略宽）
PARAM_DETAIL_VALUE_WIDTH_RATIO = 0.42
# 名称/值过长时最多折成几行（只拉高该行）
PARAM_DETAIL_NAME_MAX_LINES = 2
_PARAM_DETAIL_HEADER_TO_DATA_KEY = {
    "参数名称": "参数名称",
    "参数值": "参数值",
    "参数数值": "参数值",
    "单位": "参数单位",
    "参数单位": "参数单位",
}


def param_detail_data_key(header_or_key):
    """把界面表头映射回库字段名。"""
    key = str(header_or_key or "").strip()
    return _PARAM_DETAIL_HEADER_TO_DATA_KEY.get(key, key)


def get_param_detail_value(row_data, header_or_key):
    """按界面表头或库字段名取值；兼容「参数值/参数数值」。"""
    if not isinstance(row_data, dict):
        return ""
    key = param_detail_data_key(header_or_key)
    val = row_data.get(key, "")
    if (val is None or str(val).strip() == "") and key == "参数值":
        val = row_data.get("参数数值", "")
    if (val is None or str(val).strip() == "") and key == "参数单位":
        val = row_data.get("单位", "")
    return "" if val is None else str(val)


def param_name_text_alignment():
    """参数名称列：内容左对齐、垂直居中；表头仍由 header.setDefaultAlignment(Center) 居中。"""
    return QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter


def apply_param_detail_headers(table):
    """设置详细定义三列表头：参数名称 / 参数值 / 单位。"""
    if table is None:
        return table
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(list(PARAM_DETAIL_HEADERS))
    return table


def _param_detail_value_column_width(table, unit_width, value_width):
    """按视口剩余宽度给参数值列一个更稳的初始宽度。"""
    try:
        viewport_w = int(table.viewport().width() or table.width() or 0)
    except Exception:
        viewport_w = 0
    if viewport_w <= 0:
        return int(value_width)
    remain = max(viewport_w - int(unit_width) - 8, 120)
    ratio_w = int(remain * PARAM_DETAIL_VALUE_WIDTH_RATIO)
    return max(int(value_width), ratio_w, 200)


def apply_param_detail_column_widths(
    table,
    *,
    unit_width=PARAM_DETAIL_UNIT_COLUMN_WIDTH,
    value_width=PARAM_DETAIL_VALUE_COLUMN_WIDTH,
):
    """
    详细定义列宽：
    - 单位：Fixed，收窄
    - 参数值：Interactive，按比例加宽（避免长参数值被挡）
    - 参数名称：Stretch，吃掉剩余宽度
    """
    if table is None:
        return table
    header = table.horizontalHeader()
    col_count = table.columnCount()
    if col_count <= 0:
        return table
    if col_count >= 3:
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Interactive)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Fixed)
        table.setColumnWidth(1, _param_detail_value_column_width(table, unit_width, value_width))
        table.setColumnWidth(2, int(unit_width))
        try:
            table.setTextElideMode(QtCore.Qt.ElideNone)
        except Exception:
            pass
        for i in range(3, col_count):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)
    else:
        for i in range(col_count):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)
    install_param_detail_name_wrap(table)
    return table


def _cell_display_text(table, row, col):
    """读取单元格当前显示文本（优先 cellWidget，其次 item）。"""
    try:
        w = table.cellWidget(row, col)
    except Exception:
        w = None
    if w is not None:
        try:
            if hasattr(w, "currentText"):
                return str(w.currentText() or "")
            if hasattr(w, "text"):
                return str(w.text() or "")
        except Exception:
            pass
    item = table.item(row, col)
    return (item.text() if item is not None else "") or ""


def _text_needed_height(fm, text, width, single_h, max_h, align_flags):
    if not (text or "").strip():
        return single_h
    br = fm.boundingRect(
        QtCore.QRect(0, 0, max(int(width), 20), max_h * 4),
        align_flags,
        text,
    )
    needed = int(br.height() + 10)
    if needed <= single_h + 2:
        return single_h
    return min(max(needed, single_h), max_h)


def refresh_param_detail_row_heights(
    table,
    *,
    name_col=0,
    value_col=1,
    max_lines=PARAM_DETAIL_NAME_MAX_LINES,
):
    """
    按「参数名称 / 参数值」列内容自适应行高：
    - 两列都能单行显示全 → 保持默认行高
    - 任一列显示不全 → 折行，并只增高这一行（默认最多 2 行）
    """
    if table is None:
        return table
    try:
        table.setWordWrap(True)
        table.setTextElideMode(QtCore.Qt.ElideNone)
    except Exception:
        pass

    vh = table.verticalHeader()
    try:
        vh.setSectionResizeMode(QtWidgets.QHeaderView.Fixed)
    except Exception:
        pass

    fm = table.fontMetrics()
    single_h = max(int(fm.height() + 10), int(vh.defaultSectionSize() or 24), 24)
    line_gap = max(2, int(fm.leading()))
    max_h = single_h if max_lines <= 1 else (
        int(fm.height() * max_lines + line_gap * (max_lines - 1) + 10)
    )

    name_w = max(int(table.columnWidth(name_col)) - 12, 20)
    value_w = max(int(table.columnWidth(value_col)) - 12, 20)
    # 中文无空格，需 TextWrapAnywhere 才能按列宽折行
    name_flags = (
        QtCore.Qt.TextWrapAnywhere
        | QtCore.Qt.TextWordWrap
        | QtCore.Qt.AlignLeft
        | QtCore.Qt.AlignVCenter
    )
    value_flags = (
        QtCore.Qt.TextWrapAnywhere
        | QtCore.Qt.TextWordWrap
        | QtCore.Qt.AlignHCenter
        | QtCore.Qt.AlignVCenter
    )

    for r in range(table.rowCount()):
        if table.isRowHidden(r):
            continue
        name_h = _text_needed_height(
            fm, _cell_display_text(table, r, name_col), name_w, single_h, max_h, name_flags
        )
        value_h = _text_needed_height(
            fm, _cell_display_text(table, r, value_col), value_w, single_h, max_h, value_flags
        )
        table.setRowHeight(r, max(name_h, value_h, single_h))
    return table


class ParamDetailWrapDelegate(QtWidgets.QStyledItemDelegate):
    """详细定义文本列：按列宽折行绘制（中文无空格也能断行）。"""

    def __init__(self, parent=None, *, align=None):
        super().__init__(parent)
        self._align = align if align is not None else (
            QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
        )

    def paint(self, painter, option, index):
        self.initStyleOption(option, index)
        option.textElideMode = QtCore.Qt.ElideNone
        option.displayAlignment = self._align
        try:
            option.features |= QtWidgets.QStyleOptionViewItem.WrapText
        except Exception:
            pass

        text = index.data(QtCore.Qt.DisplayRole)
        if text is None:
            text = ""
        text = str(text)

        style = option.widget.style() if option.widget else QtWidgets.QApplication.style()
        style.drawPrimitive(
            QtWidgets.QStyle.PE_PanelItemViewItem, option, painter, option.widget
        )

        text_rect = style.subElementRect(
            QtWidgets.QStyle.SE_ItemViewItemText, option, option.widget
        )
        if not text_rect.isValid():
            text_rect = option.rect.adjusted(4, 2, -4, -2)
        else:
            text_rect = text_rect.adjusted(2, 1, -2, -1)

        if option.state & QtWidgets.QStyle.State_Selected:
            painter.setPen(option.palette.color(QtGui.QPalette.HighlightedText))
        else:
            painter.setPen(option.palette.color(QtGui.QPalette.Text))

        painter.drawText(
            text_rect,
            QtCore.Qt.TextWrapAnywhere | QtCore.Qt.TextWordWrap | int(self._align),
            text,
        )

    def sizeHint(self, option, index):
        hint = super().sizeHint(option, index)
        text = str(index.data(QtCore.Qt.DisplayRole) or "")
        if not text:
            return hint
        fm = option.fontMetrics
        width = option.rect.width() if option.rect.width() > 0 else hint.width()
        width = max(width - 8, 20)
        br = fm.boundingRect(
            QtCore.QRect(0, 0, width, 1000),
            QtCore.Qt.TextWrapAnywhere | QtCore.Qt.TextWordWrap,
            text,
        )
        max_h = int(fm.height() * PARAM_DETAIL_NAME_MAX_LINES + 10)
        hint.setHeight(min(max(br.height() + 8, hint.height()), max_h))
        return hint


# 兼容旧名称
ParamNameWrapDelegate = ParamDetailWrapDelegate


def install_param_detail_name_wrap(table, *, name_col=0, value_col=1, deferred=True):
    """
    启用参数名称/参数值折行，并在列宽变化时按行重算行高。
    数据填充完成后也应再调一次 refresh_param_detail_row_heights。

    注意：参数值列很多行会用 setItemDelegateForRow 装下拉框（行委托优先于列委托），
    因此值列折行主要靠 setWordWrap + 行高；名称列用列委托保证中文可断行。
    """
    if table is None:
        return table

    try:
        table.setWordWrap(True)
        table.setTextElideMode(QtCore.Qt.ElideNone)
    except Exception:
        pass

    def _do_refresh():
        refresh_param_detail_row_heights(table, name_col=name_col, value_col=value_col)

    table._refresh_param_detail_row_heights = _do_refresh

    if not getattr(table, "_param_detail_name_wrap_installed", False):
        try:
            table.setItemDelegateForColumn(
                name_col,
                ParamDetailWrapDelegate(
                    table, align=QtCore.Qt.AlignLeft | QtCore.Qt.AlignVCenter
                ),
            )
        except Exception:
            pass

        header = table.horizontalHeader()

        def _on_section_resized(logical_index, _old, _new):
            if logical_index in (name_col, value_col):
                QtCore.QTimer.singleShot(0, _do_refresh)

        try:
            header.sectionResized.connect(_on_section_resized)
        except Exception:
            pass

        # 表格整体尺寸变化时（Stretch 列宽会变）也重算
        class _ParamDetailResizeFilter(QtCore.QObject):
            def eventFilter(self, obj, event):
                if event.type() == QtCore.QEvent.Resize and obj is table:
                    QtCore.QTimer.singleShot(0, _do_refresh)
                return False

        try:
            filt = _ParamDetailResizeFilter(table)
            table.installEventFilter(filt)
            table._param_detail_resize_filter = filt
        except Exception:
            pass

        table._param_detail_name_wrap_installed = True

    if deferred:
        QtCore.QTimer.singleShot(0, _do_refresh)
        # 布局稳定后再算一次，避免首次 Stretch 宽度未定时算矮了
        QtCore.QTimer.singleShot(50, _do_refresh)
    else:
        _do_refresh()
    return table


def setup_param_detail_table(table, *, use_custom_header=False, stretch_columns=True, header_height=None):
    """
    给动态创建的详细定义表套上与普通元件一致的新 UI 样式。

    注意：普通元件 tableWidget_para 的表头实际由 Form QSS（#f3f5f8）绘制；
    若再装 CustomHeaderView，会走 paintSection 旧自绘色，表头就会仍像旧 UI。
    因此默认不装 CustomHeaderView，只套与 paradefine_newui.ui 一致的 QSS。
    """
    if table is None:
        return table

    if use_custom_header:
        try:
            table.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, table))
        except Exception:
            pass
    else:
        # 确保不是残留的 CustomHeaderView（否则仍会旧色自绘）
        header = table.horizontalHeader()
        if isinstance(header, CustomHeaderView):
            table.setHorizontalHeader(QtWidgets.QHeaderView(QtCore.Qt.Horizontal, table))

    table.setStyleSheet(PARAM_DETAIL_TABLE_QSS)
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setEditTriggers(QtWidgets.QAbstractItemView.SelectedClicked)
    table.verticalHeader().setVisible(False)

    header = table.horizontalHeader()
    header.setStyleSheet("")  # 避免旧的 header 局部 QSS 覆盖 Form 风格
    if stretch_columns:
        apply_param_detail_column_widths(table)
    else:
        install_param_detail_name_wrap(table)
    header.setDefaultAlignment(QtCore.Qt.AlignCenter)
    if header_height:
        header.setFixedHeight(header_height)
    else:
        # 取消此前固定 35 的旧高度，与普通元件表头高度一致
        try:
            header.setMinimumHeight(0)
            header.setMaximumHeight(16777215)
        except Exception:
            pass

    # Tab 仅落在可输入单元格（参数名称/单位/只读格自动跳过）
    try:
        from modules.cailiaodingyi.controllers.style import install_editable_only_tab
        install_editable_only_tab(table, mode="editable")
    except Exception:
        pass
    return table


def highlight_param_detail_selection(table):
    """
    选中行高亮：未选中单元格刷 #d0e7ff，与普通元件 on_param_table_selection_changed 一致。
    供动态详细定义表在 itemSelectionChanged 时调用。
    """
    if table is None:
        return
    selected_items = table.selectedItems()
    selected_cells = {(item.row(), item.column()) for item in selected_items}
    selected_rows = {row for row, _ in selected_cells}

    for r in range(table.rowCount()):
        for c in range(table.columnCount()):
            item = table.item(r, c)
            if not item:
                continue
            if (r, c) in selected_cells:
                continue
            item.setBackground(QtGui.QColor("#ffffff"))

    for row in selected_rows:
        for col in range(table.columnCount()):
            if (row, col) in selected_cells:
                continue
            item = table.item(row, col)
            if item:
                item.setBackground(QtGui.QColor("#d0e7ff"))


def install_param_detail_selection_highlight(table):
    """给动态详细定义表挂上选中高亮（避免重复连接）。"""
    if table is None:
        return
    if getattr(table, "_param_detail_sel_hl_installed", False):
        return

    def _on_sel_changed():
        highlight_param_detail_selection(table)

    try:
        table.itemSelectionChanged.connect(_on_sel_changed)
        table._param_detail_sel_hl_installed = True
    except Exception:
        pass


class CustomHeaderView(QtWidgets.QHeaderView):
    """表头：可选 Excel 式筛选箭头，仅点击箭头触发筛选。"""

    filterArrowClicked = QtCore.pyqtSignal(int)

    # 箭头可点区域宽度（像素）
    ARROW_HIT_WIDTH = 18

    def __init__(self, orientation, parent=None):
        super().__init__(orientation, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignCenter)
        self._show_filter_arrows = False
        self._hover_section = -1
        self.setMouseTracking(True)

    def setShowFilterArrows(self, enabled: bool):
        self._show_filter_arrows = bool(enabled)
        self.viewport().update()

    def showFilterArrows(self) -> bool:
        return self._show_filter_arrows

    def _arrow_rect(self, section_rect: QtCore.QRect) -> QtCore.QRect:
        w = self.ARROW_HIT_WIDTH
        return QtCore.QRect(
            section_rect.right() - w + 1,
            section_rect.top(),
            w,
            section_rect.height(),
        )

    def _section_at_pos(self, pos: QtCore.QPoint) -> int:
        return self.logicalIndexAt(pos)

    def _is_on_filter_arrow(self, pos: QtCore.QPoint) -> int:
        """若点击落在筛选箭头上，返回逻辑列号；否则返回 -1。"""
        if not self._show_filter_arrows:
            return -1
        logical = self._section_at_pos(pos)
        if logical < 0:
            return -1
        # 避开列宽拖拽热区
        if self.orientation() == QtCore.Qt.Horizontal:
            visual = self.visualIndex(logical)
            x = self.sectionViewportPosition(logical)
            section_w = self.sectionSize(logical)
            # 右侧约 3px 留给 resize handle
            if pos.x() >= x + section_w - 3:
                return -1
            section_rect = QtCore.QRect(x, 0, section_w, self.height())
        else:
            return -1
        if self._arrow_rect(section_rect).contains(pos):
            return logical
        return -1

    def paintSection(self, painter, rect, logicalIndex):
        painter.save()

        # 与 paradefine_newui.ui 表头色一致
        painter.fillRect(rect, QtGui.QColor("#f3f5f8"))

        # 绘制文字
        text = self.model().headerData(logicalIndex, self.orientation(), QtCore.Qt.DisplayRole)
        painter.setPen(QtGui.QPen(QtGui.QColor("#1f1f1f")))

        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        text_rect = QtCore.QRect(rect)
        if self._show_filter_arrows:
            # 给右侧箭头留空，避免汉字与箭头重叠
            text_rect.setRight(rect.right() - self.ARROW_HIT_WIDTH)

        painter.drawText(text_rect, QtCore.Qt.AlignCenter, str(text))

        # Excel 式下拉箭头
        if self._show_filter_arrows:
            arrow_area = self._arrow_rect(rect)
            cx = arrow_area.center().x()
            cy = arrow_area.center().y()
            # 悬停时箭头略深
            color = QtGui.QColor("#333333") if logicalIndex == self._hover_section else QtGui.QColor("#666666")
            painter.setPen(QtCore.Qt.NoPen)
            painter.setBrush(QtGui.QBrush(color))
            size = 4
            points = [
                QtCore.QPoint(cx - size, cy - size // 2),
                QtCore.QPoint(cx + size, cy - size // 2),
                QtCore.QPoint(cx, cy + size // 2 + 1),
            ]
            painter.drawPolygon(QtGui.QPolygon(points))

        # 底部分隔线
        pen = QtGui.QPen(QtGui.QColor("#CCCCCC"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 列之间竖线
        if self.model() and logicalIndex != self.model().columnCount() - 1:
            painter.drawLine(rect.topRight(), rect.bottomRight())

        painter.restore()

    def mouseMoveEvent(self, event):
        if self._show_filter_arrows:
            logical = self._is_on_filter_arrow(event.pos())
            prev = self._hover_section
            self._hover_section = logical
            if logical >= 0:
                self.viewport().setCursor(QtCore.Qt.PointingHandCursor)
            else:
                self.viewport().unsetCursor()
            if prev != self._hover_section:
                self.viewport().update()
        super().mouseMoveEvent(event)

    def leaveEvent(self, event):
        if self._hover_section >= 0:
            self._hover_section = -1
            self.viewport().unsetCursor()
            self.viewport().update()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if (
            self._show_filter_arrows
            and event.button() == QtCore.Qt.LeftButton
        ):
            logical = self._is_on_filter_arrow(event.pos())
            if logical >= 0:
                self.filterArrowClicked.emit(logical)
                event.accept()
                return
        super().mousePressEvent(event)
