# ==================== 下拉框委托模块 ====================
# 本模块实现了多种类型的表格单元格下拉编辑器（委托），用于在表格中提供下拉选择功能，
# 并支持联动、批量填充、动态选项等高级特性。
# ========================================================

from PyQt5 import QtCore, sip
from PyQt5.QtGui import QColor, QStandardItem
from PyQt5.QtWidgets import QTableWidgetItem, QComboBox, QStyledItemDelegate, QAbstractItemView
from PyQt5.QtCore import Qt, QObject, QTimer, QItemSelectionModel
from PyQt5.QtCore import QEvent

# 引入项目内部函数：根据筛选条件获取材料可选值（用于动态联动）
from modules.cailiaodingyi.funcs.funcs_pdf_change import get_filtered_material_options


# ==================== 基础下拉框委托类 ====================
class ComboDelegate(QStyledItemDelegate):
    """基础下拉框委托类，提供通用的下拉选择编辑器，并支持行高亮"""
    
    def __init__(self, options, table=None):
        """
        初始化下拉框委托
        
        参数:
            options: list[str] - 下拉选项列表
            table: QTableWidget - 表格对象（用于高亮行）
        """
        super().__init__(table)
        self.options = options or []   # 存储选项列表，若传入None则设为空列表
        self.table = table             # 保存表格引用，以便后续操作

    def createEditor(self, parent, option, index):
        """创建下拉框编辑器并配置自动弹出"""
        # 创建组合框控件，不可编辑（只能从下拉列表中选择）
        combo = QComboBox(parent)
        combo.setEditable(False)

        # 加载选项，确保首个为空项（便于用户清空选择）
        opts = self.options or []
        # 如果选项列表为空或第一个元素不是空字符串，则在开头插入一个空项
        if not opts or (opts and opts[0] != ""):
            opts = [""] + list(dict.fromkeys(opts))  # 去重后加空项
        combo.addItems(opts)
        
        # 行高亮：当进入编辑状态时，高亮当前行（浅蓝色背景）
        if self.table:
            self.highlight_row(index.row())

        # 对齐当前值：从表格模型中读取当前单元格的值，并在下拉框中选中对应的项
        cur = index.data() or ""
        i = combo.findText(cur)
        combo.setCurrentIndex(max(0, i))   # 若找不到则选中空项（索引0）

        # 自动弹出下拉框（使用单次定时器，确保编辑器完全创建后再弹出）
        QTimer.singleShot(0, combo.showPopup)

        # 当下拉框的选项被激活（选中）时，提交数据并关闭编辑器
        combo.activated.connect(lambda _: self._commit_and_close(combo))
        return combo

    def setEditorData(self, editor, index):
        """将单元格数据回写到编辑器（初始化编辑器显示内容）"""
        # 从模型中获取当前单元格的文本
        txt = index.model().data(index, Qt.EditRole) or ""
        # 在编辑器中查找该文本对应的索引
        i = editor.findText(txt)
        # 设置编辑器的当前选中项（若找不到则设为0，即空项）
        editor.setCurrentIndex(max(0, i))

    def setModelData(self, editor, model, index):
        """将编辑器数据保存到模型并居中显示"""
        r, c = index.row(), index.column()
        # 将编辑器的当前文本写入模型（Qt标准数据存储）
        model.setData(index, editor.currentText(), Qt.EditRole)

        # 获取表格中的单元格项，若不存在则创建一个新的
        it = self.table.item(r, c)
        if it is None:
            it = QTableWidgetItem()
            self.table.setItem(r, c, it)
        # 设置单元格文本并居中显示
        it.setText(editor.currentText() or "")
        it.setTextAlignment(Qt.AlignCenter)

        # 立即恢复当前单元格为活动状态，并重新高亮行
        self.table.setCurrentCell(r, c)
        if hasattr(self, "highlight_row"):
            self.highlight_row(r)

    def highlight_row(self, row):
        """高亮显示指定行（浅蓝色背景），其他行恢复白色"""
        # 先将所有单元格背景设为白色
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                item = self.table.item(r, c)
                if item:
                    item.setBackground(QColor("#ffffff"))
        # 再将当前行的所有列背景设为浅蓝色
        for c in range(self.table.columnCount()):
            item = self.table.item(row, c)
            if item:
                item.setBackground(QColor("#d0e7ff"))


# ==================== 辅助函数 ====================
def _row_value_cols(table, row, *, exclude_col=None):
    """返回该行可写入的列（列1/2/3且可编辑），用于批量填充时确定目标列"""
    cols = []
    for c in (1, 2, 3):
        if exclude_col is not None and c == exclude_col:
            continue   # 排除指定的列（通常为当前编辑的列本身）
        it = table.item(row, c)
        # 检查该单元格是否存在并且是可编辑的
        if it and (it.flags() & Qt.ItemIsEditable):
            cols.append(c)
    return cols

def _set_text_center(table, r, c, text):
    """在表格指定单元格设置居中文本（复用已有的item，若无则创建）"""
    it = table.item(r, c)
    if it is None:
        it = QTableWidgetItem()
        it.setTextAlignment(Qt.AlignCenter)
        table.setItem(r, c, it)
    it.setText(text or "")


# ==================== 行填充下拉委托 ====================
class RowFillComboDelegate(ComboDelegate):
    """
    行填充下拉委托
    
    选择一个下拉值后，把相同的值写入"本行其余可编辑的值列(1/2/3)"
    用于实现：同一行的多个列共享同一个值（例如管道规格统一填写）
    """
    def setModelData(self, editor, model, index):
        """保存当前格并同步到本行其他可编辑列"""
        # 先按父类的逻辑把当前格写回（包含居中设置）
        super().setModelData(editor, model, index)

        row, col = index.row(), index.column()
        new_text = editor.currentText()

        # 获取本行其他可编辑的值列（排除当前列）
        targets = _row_value_cols(self.table, row, exclude_col=col)
        if not targets:
            return   # 没有其他可编辑列，直接返回

        # 批量写入其他列，期间阻断表格信号以避免不必要的刷新
        self.table.blockSignals(True)
        try:
            for cc in targets:
                _set_text_center(self.table, row, cc, new_text)
        finally:
            self.table.blockSignals(False)
        # 恢复当前单元格为活动状态
        self.table.setCurrentCell(row, col)


# ==================== 成型工艺专用委托（按列动态选项） ====================
class ProcessPerColumnDelegate(QStyledItemDelegate):
    """
    成型工艺行专用代理
    
    根据"覆层材料类型"本列的取值决定下拉候选：
    - 如果类型属于板材类型集合，则提供板材选项列表
    - 如果属于焊接类型集合，则提供焊接选项列表
    - 否则提供两者并集
    """
    def __init__(self, table, type_row, plate_values, weld_values,
                 plate_options, weld_options):
        """
        初始化成型工艺代理
        
        参数:
            table: QTableWidget - 表格对象
            type_row: int - 类型行号（固定行，存储材料类型）
            plate_values: set - 板材类型值集合（例如 {"板材", "板"}）
            weld_values: set - 焊接类型值集合（例如 {"焊接", "焊"}）
            plate_options: list - 板材选项列表（例如 ["Q235B", "304"]）
            weld_options: list - 焊接选项列表（例如 ["焊条", "氩弧焊"]）
        """
        super().__init__(table)
        self.table = table
        self.type_row = type_row
        self.plate_values = set(plate_values)
        self.weld_values = set(weld_values)
        self.plate_options = list(plate_options)
        self.weld_options = list(weld_options)

    def _type_text(self, col):
        """获取指定列的类型文本（优先从组合框控件获取，否则从单元格文本获取）"""
        w = self.table.cellWidget(self.type_row, col)
        if isinstance(w, QComboBox):
            return w.currentText().strip()
        it = self.table.item(self.type_row, col)
        return it.text().strip() if it else ""

    def createEditor(self, parent, option, index):
        """根据类型创建对应的下拉编辑器"""
        cb = QComboBox(parent)
        t = self._type_text(index.column())  # 获取当前列对应的材料类型
        # 根据类型选择对应的选项列表
        if t in self.plate_values:
            opts = self.plate_options
        elif t in self.weld_values:
            opts = self.weld_options
        else:
            # 类型未知或为空时，提供板材和焊接选项的并集（去重）
            opts = list(dict.fromkeys(self.plate_options + self.weld_options))
        # 确保选项列表包含空项（便于清空）
        cb.addItems(opts if "" in opts else [""] + opts)
        return cb

    def setEditorData(self, editor, index):
        """将单元格数据回写到编辑器"""
        cur = index.data() or ""
        i = editor.findText(cur)
        editor.setCurrentIndex(0 if i < 0 else i)   # 找不到则选空项

    def setModelData(self, editor, model, index):
        """将编辑器数据保存到模型"""
        model.setData(index, editor.currentText())

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何位置"""
        editor.setGeometry(option.rect)


# ==================== 非负浮点数输入委托 ====================
class NonNegativeDoubleDelegate(QStyledItemDelegate):
    """
    非负浮点数输入委托
    
    用于某一行装上后：该行所有可编辑单元格都用带下限的QDoubleValidator，
    限制输入为非负数字，保留指定小数位数。
    """
    def __init__(self, bottom=0.0, decimals=6, parent=None):
        """
        初始化非负浮点数委托
        
        参数:
            bottom: float - 允许的最小值（默认0.0）
            decimals: int - 小数位数（默认6位）
            parent: QWidget - 父控件
        """
        super().__init__(parent)
        self.bottom = float(bottom)
        self.decimals = int(decimals)

    def createEditor(self, parent, option, index):
        """创建带验证器的输入框（QLineEdit）"""
        from PyQt5.QtWidgets import QLineEdit
        from PyQt5.QtGui import QDoubleValidator
        le = QLineEdit(parent)
        v = QDoubleValidator(self.bottom, 1e12, self.decicals if hasattr(self, "decicals") else self.decimals, le)
        v.setNotation(QDoubleValidator.StandardNotation)
        le.setValidator(v)
        le.setAlignment(Qt.AlignCenter)   # 文本居中
        return le

    def setEditorData(self, editor, index):
        """将单元格数据回写到编辑器"""
        editor.setText((index.data() or "").strip())

    def setModelData(self, editor, model, index):
        """将编辑器数据保存到模型"""
        model.setData(index, editor.text().strip())


# ==================== 材料字段即时提交委托 ====================
class MaterialInstantDelegate(ComboDelegate):
    """
    材料字段即时提交委托
    
    用于'材料类型/材料牌号/材料标准/供货状态'四字段：
    - 选项改变时，立即写回模型、关闭编辑器
    - 把"新值+行/列+字段名"回调给外部进行联动
    """
    def __init__(self, options, table=None, field_name=None, on_pick=None):
        """
        初始化材料字段委托
        
        参数:
            options: list[str] - 下拉选项列表
            table: QTableWidget - 表格对象
            field_name: str - 字段名称（例如"材料类型"）
            on_pick: callable - 回调函数，签名: on_pick(field_name, new_text, row, col)
        """
        super().__init__(options, table)
        self.field_name = field_name
        self.on_pick = on_pick

    def createEditor(self, parent, option, index):
        """创建下拉框并绑定自动提交事件"""
        ed = super().createEditor(parent, option, index)

        # 定义内部函数：提交并关闭编辑器，然后触发联动回调
        def _commit_and_close():
            # 1) 发射提交数据信号（会调用 setModelData）
            self.commitData.emit(ed)
            # 2) 关闭编辑器
            self.closeEditor.emit(ed, QStyledItemDelegate.NoHint)
            # 3) 下一事件循环中回调联动函数（确保数据已写入模型）
            if self.on_pick:
                r, c = index.row(), index.column()
                new_text = ed.currentText()
                QtCore.QTimer.singleShot(0, lambda: self.on_pick(self.field_name, new_text, r, c))

        # 绑定多种信号：activated（用户选中某项）、currentIndexChanged、currentTextChanged
        # 只要值发生变化就立即提交
        ed.activated.connect(lambda _=None: _commit_and_close())
        ed.currentIndexChanged.connect(lambda _=None: _commit_and_close())
        ed.currentTextChanged.connect(lambda _=None: _commit_and_close())
        return ed

    def setModelData(self, editor, model, index):
        """维持原ComboDelegate的写回逻辑（居中显示等）"""
        super().setModelData(editor, model, index)


# ==================== 下拉框弹出事件过滤器 ====================
class ComboPopupEventFilter(QObject):
    """下拉框弹出事件过滤器，处理多选情况（当同一行有多列被选中时，阻止Qt默认选区处理，强制编辑当前格）"""
    
    def __init__(self, table):
        """
        初始化事件过滤器
        
        参数:
            table: QTableWidget - 表格对象
        """
        super().__init__(table)
        self.table = table

    def eventFilter(self, obj, event):
        """过滤鼠标点击事件，处理同一行多列选中情况"""
        # 检查表格对象是否仍然有效（避免在析构后访问）
        if not hasattr(self, "table") or self.table is None:
            return False
        if sip.isdeleted(self.table):
            return False
        
        # 只拦截表格视口（viewport）上的鼠标点击事件
        if obj is self.table.viewport() and event.type() in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick):
            idx = self.table.indexAt(event.pos())   # 获取鼠标位置对应的模型索引
            if idx.isValid():
                sm = self.table.selectionModel()
                sel = sm.selectedIndexes() if sm else []
                # 判断：同一行是否有多列被选中（且这些列都是可编辑的）
                same_row_cols = sorted({
                    i.column() for i in sel
                    if i.row() == idx.row()
                    and self.table.item(i.row(), i.column())
                    and (self.table.item(i.row(), i.column()).flags() & Qt.ItemIsEditable)
                })
                if len(same_row_cols) >= 2:
                    # 阻止Qt自己的选区处理（避免多个单元格同时进入编辑状态）
                    event.accept()
                    # 延迟一下启动编辑，确保事件处理完成
                    QTimer.singleShot(0, lambda: self.table.edit(idx))
                    return True
        return False   # 其他情况交给默认处理


# ==================== 材料字段变化联动处理函数（列模式） ====================
def _read_col_values(table, col: int, rows_map: dict):
    """读取指定列多个行的值，返回字段名到值的映射"""
    vals = {}
    for f, r in rows_map.items():
        it = table.item(r, col)
        vals[f] = (it.text().strip() if it else "")
    return vals

def _write_cell(table, row: int, col: int, text: str):
    """写入单元格文本（复用已有item，若无则创建并居中）"""
    it = table.item(row, col)
    if it is None:
        it = QTableWidgetItem()
        it.setTextAlignment(Qt.AlignCenter)
        table.setItem(row, col, it)   # 仅在确实没有时创建
    else:
        # 复用已有 item，避免频繁 setItem 导致 currentIndex 丢失
        pass
    it.setText(text or "")


def on_material_field_changed_col(table, col: int, rows_map: dict, sender_field: str, prev_value: str = None):
    """
    材料字段变化时的联动处理（基于列索引的版本）
    
    当某一列的材料字段（材料类型/牌号/标准/状态）发生变化时，
    根据依赖关系自动清空后续字段，并重新计算可选值。
    
    参数:
        table: QTableWidget - 表格对象
        col: int - 列号
        rows_map: dict - 字段名到行号的映射（例如 {'材料类型': 0, '材料牌号': 1, ...}）
        sender_field: str - 触发变化的字段名
        prev_value: str - 变化前的值（用于判断是否真正改变）
    """
    # 添加防重复执行标志，避免递归调用（因为修改单元格内容会再次触发信号）
    if not hasattr(table, '_material_changing'):
        table._material_changing = False

    if table._material_changing:
        return   # 正在处理中，直接返回

    table._material_changing = True

    try:
        # 定义内部辅助函数：读取指定行当前列的文本
        def _get(r):
            it = table.item(r, col)
            return (it.text().strip() if it else "")

        # 定义内部辅助函数：设置指定行当前列的文本
        def _set(r, val):
            it = table.item(r, col)
            if it is None:
                it = QTableWidgetItem()
                it.setTextAlignment(Qt.AlignCenter)
                table.setItem(r, col, it)
            it.setText(val or "")

        # 获取各字段对应的行号
        r_type = rows_map.get('材料类型')
        r_brand = rows_map.get('材料牌号')
        r_std = rows_map.get('材料标准')
        r_status = rows_map.get('供货状态')

        # 读取当前各字段的值
        cur_type = _get(r_type)
        cur_brand = _get(r_brand)
        cur_std = _get(r_std)
        cur_status = _get(r_status)

        # 引入外部联动函数
        from modules.cailiaodingyi.funcs.funcs_pdf_change import get_filtered_material_options

        # ===== 根据触发字段执行不同联动逻辑 =====
        if sender_field == '材料类型':
            # 材料类型变化：清空后续字段（牌号、标准、状态），并重新安装委托
            new_val = cur_type
            # 如果值没有实际变化，则不做处理（防止空触发）
            if prev_value is not None and (new_val or "") == (prev_value or ""):
                return

            # 清空后续字段（阻断信号避免递归）
            table.blockSignals(True)
            try:
                for rr in (r_brand, r_std, r_status):
                    if rr is not None:
                        _set(rr, "")
            finally:
                table.blockSignals(False)

            # 重新安装委托（刷新下拉选项）
            _reinstall_material_delegates(table, col, rows_map, cur_type, cur_brand, cur_std)

        elif sender_field == '材料牌号':
            # 材料牌号变化：清空材料标准和供货状态
            table.blockSignals(True)
            try:
                if r_std is not None:
                    _set(r_std, "")
                if r_status is not None:
                    _set(r_status, "")
            finally:
                table.blockSignals(False)

            # 重新获取选项（基于材料类型和牌号）
            f = get_filtered_material_options({"材料类型": cur_type, "材料牌号": cur_brand}) or {}
            std_opts = f.get("材料标准", []) or []
            stat_opts = f.get("供货状态", []) or []

            # 如果只有唯一选项，则自动填入（提升用户体验）
            table.blockSignals(True)
            try:
                if len(std_opts) == 1:
                    _set(r_std, std_opts[0])
                if len(stat_opts) == 1:
                    _set(r_status, stat_opts[0])
            finally:
                table.blockSignals(False)

            # 重新安装委托
            _reinstall_material_delegates(table, col, rows_map, cur_type, cur_brand, cur_std)

        elif sender_field == '材料标准':
            # 材料标准变化：更新供货状态选项
            f = get_filtered_material_options({"材料类型": cur_type, "材料牌号": cur_brand, "材料标准": cur_std}) or {}
            stat_opts = f.get("供货状态", []) or []

            # 如果当前供货状态为空且只有唯一选项，自动填入
            if (not cur_status) and len(stat_opts) == 1:
                table.blockSignals(True)
                try:
                    _set(r_status, stat_opts[0])
                finally:
                    table.blockSignals(False)

            # 重新安装委托
            _reinstall_material_delegates(table, col, rows_map, cur_type, cur_brand, cur_std)

        # 供货状态变化：无需额外联动（最后一个字段）

    finally:
        table._material_changing = False


def _reinstall_material_delegates(table, col: int, rows_map: dict, cur_type: str, cur_brand: str, cur_std: str):
    """重新安装材料字段的delegate（刷新视图，让用户看到最新的选项）"""
    # 简单触发视图更新，让用户知道数据已变化（实际委托更新由外部调用方负责）
    table.viewport().update()


# ==================== 动态选项下拉委托 ====================
class DynamicOptionsDelegate(ComboDelegate):
    """
    动态选项下拉委托
    
    根据当前行的其他字段值动态计算下拉选项（基于数据库中的材料约束关系）
    """
    def __init__(self, table, groups, row2field, row2group):
        """
        初始化动态选项委托
        
        参数:
            table: QTableWidget - 表格对象
            groups: list[dict] - 字段组列表，每个元素是一个字典 {字段名: 行号}
            row2field: dict - 行号到字段名的映射
            row2group: dict - 行号到组索引的映射
        """
        super().__init__(options=[], table=table)
        self.groups = groups          # 存储所有组的行号映射
        self.row2field = row2field    # 行号 -> 字段名（例如 0 -> "材料类型"）
        self.row2group = row2group    # 行号 -> 组索引（例如 0 -> 0 表示第0组）

    def _field_of_row(self, row: int):
        """获取行对应的字段名"""
        return self.row2field.get(row, "")

    def _group_map_of_row(self, row: int):
        """获取行对应的组映射（该组内所有字段的行号）"""
        gi = self.row2group.get(row, None)
        # 如果组索引有效，则返回对应的组字典；否则返回空字典
        return (self.groups[gi] if gi is not None and 0 <= gi < len(self.groups) else {})

    def _all_material_types(self):
        """获取所有材料类型（来自数据库，去重）"""
        all_map = get_filtered_material_options({}) or {}
        return list(dict.fromkeys(all_map.get('材料类型', [])))

    def createEditor(self, parent, option, index):
        """根据当前选择动态创建下拉选项"""
        row, col = index.row(), index.column()
        field = self._field_of_row(row)
        # 只处理材料相关的四个字段，其他字段不处理
        if field not in ('材料类型', '材料牌号', '材料标准', '供货状态'):
            return None

        group_map = self._group_map_of_row(row)
        # 收集组内当前各字段的值（同列下）
        selected = {}
        for k in ('材料类型', '材料牌号', '材料标准', '供货状态'):
            rr = group_map.get(k)
            it = self.table.item(rr, col) if rr is not None else None
            selected[k] = (it.text().strip() if it else "")

        # 根据当前字段的不同，计算可选项
        if field == '材料类型':
            opts = self._all_material_types()   # 材料类型显示全部选项
        else:
            # 其他字段：基于已选的其他字段（排除自身）进行过滤
            basis = {k: v for k, v in selected.items() if k != field and v}
            all_options = get_filtered_material_options(basis) or {}
            opts = all_options.get(field, [])

        # 确保选项列表包含空项（便于清空）
        if not opts or opts[0] != "":
            opts = [""] + list(dict.fromkeys(opts))
        self.options = opts

        # 调用父类创建编辑器
        ed = super().createEditor(parent, option, index)

        # 对齐当前值（从模型读取）
        cur = index.data() or ""
        i = ed.findText(cur)
        ed.setCurrentIndex(max(0, i))
        return ed

    def setModelData(self, editor, model, index):
        """保存数据并触发联动"""
        old_val = index.data() or ""   # 保存变化前的值

        # 正常写回（调用父类方法，会写入模型和表格）
        super().setModelData(editor, model, index)

        # 联动处理：如果修改的是材料相关字段，调用联动函数
        row, col = index.row(), index.column()
        sender_field = self._field_of_row(row)
        if sender_field in ('材料类型', '材料牌号', '材料标准', '供货状态'):
            group_map = self._group_map_of_row(row)
            on_material_field_changed_col(self.table, col, group_map, sender_field, prev_value=old_val)

        self.table.setCurrentCell(row, col)   # 恢复当前单元格焦点


# ==================== 批量填充动态选项委托 ====================
class BulkFillDynamicOptionsDelegate(DynamicOptionsDelegate):
    """
    批量填充动态选项委托
    
    支持"多选列->一次选择->批量写入"的材料四字段下拉代理。
    当用户在同一行中选中了多个列，然后通过其中一个列的下拉框选择值时，
    会尝试将相同的值同时写入其他被选中的列（前提是候选列表中包含该值）。
    """
    def _editable(self, r, c):
        """判断单元格是否可编辑（检查其flags）"""
        it = self.table.item(r, c)
        return bool(it and (it.flags() & Qt.ItemIsEditable))

    def _selected_editable_cols_same_row(self, row, anchor_col):
        """获取同一行中被多选的可编辑列（至少包含 anchor_col）"""
        cols = set()
        sm = self.table.selectionModel()
        if sm:
            # 遍历所有选中的索引，收集同一行且可编辑的列号
            for idx in sm.selectedIndexes():
                if idx.row() == row and self._editable(row, idx.column()):
                    cols.add(idx.column())
        # 如果没有多选（即只选中了一列），则将该行所有可编辑列都作为目标（批量填充整行）
        if not cols:
            for c in range(self.table.columnCount()):
                if self._editable(row, c):
                    cols.add(c)
        # 确保当前列在集合中
        cols.add(anchor_col)
        return sorted(cols)

    def _current_group_values_at_col(self, group_map, col):
        """获取指定列的当前组值（各字段的文本）"""
        cur = {}
        for k in ('材料类型','材料牌号','材料标准','供货状态'):
            rr = group_map.get(k)
            it = self.table.item(rr, col) if rr is not None else None
            cur[k] = (it.text().strip() if it else "")
        return cur

    def setModelData(self, editor, model, index):
        """批量写入并联动"""
        old_val = index.data() or ""   # 变化前的值
        # 先调用父类保存当前单元格（会写入当前列）
        super().setModelData(editor, model, index)

        row, col = index.row(), index.column()
        sender_field = self._field_of_row(row)
        # 只处理材料字段
        if sender_field not in ('材料类型', '材料牌号', '材料标准', '供货状态'):
            self.table.setCurrentCell(row, col)
            return

        new_val = editor.currentText()           # 新值
        group_map = self._group_map_of_row(row)  # 当前行的组映射

        # 计算同一行被多选的其它列（包含当前列）
        target_cols = self._selected_editable_cols_same_row(row, col)

        from modules.cailiaodingyi.funcs.funcs_pdf_change import get_filtered_material_options

        # 辅助函数：设置单元格文本（居中）
        def _set_cell_text(r, c, txt):
            it = self.table.item(r, c)
            if it is None:
                it = QTableWidgetItem()
                it.setTextAlignment(Qt.AlignCenter)
                self.table.setItem(r, c, it)
            it.setText(txt or "")

        # 逐列校验候选并写入
        self.table.blockSignals(True)
        try:
            for cc in target_cols:
                if not self._editable(row, cc):
                    continue   # 不可编辑的列跳过

                # 基于该列当前选择组合拿候选选项
                cur_vals = self._current_group_values_at_col(group_map, cc)

                # 根据字段类型获取该列当前的候选列表
                if sender_field == '材料类型':
                    all_map = get_filtered_material_options({}) or {}
                    opts = list(dict.fromkeys(all_map.get('材料类型', [])))
                else:
                    basis = {k: v for k, v in cur_vals.items() if k != sender_field and v}
                    filtered = get_filtered_material_options(basis) or {}
                    opts = filtered.get(sender_field, []) or []

                # 确保包含空项
                if not opts or opts[0] != "":
                    opts = [""] + list(dict.fromkeys(opts))

                # 如果新值在当前列的候选列表中，则写入该列对应的字段行
                if new_val in opts:
                    rr = group_map.get(sender_field)
                    if rr is not None:
                        cur_txt = (self.table.item(rr, cc).text().strip()
                                   if self.table.item(rr, cc) else "")
                        if cur_txt != new_val:
                            _set_cell_text(rr, cc, new_val)
        finally:
            self.table.blockSignals(False)

        # 批量联动：对写入过的每个列各触发一次联动处理（清空依赖字段等）
        for cc in target_cols:
            if cc == col:
                continue   # 当前列已在父类中触发过联动，跳过避免重复
            # 获取该列在变化前的值（用于联动判断）
            prev_cc = self._current_group_values_at_col(group_map, cc).get(sender_field, "")
            if prev_cc == new_val:
                continue   # 值未变，无需联动
            on_material_field_changed_col(self.table, cc, group_map, sender_field, prev_value=prev_cc)

        self.table.setCurrentCell(row, col)   # 恢复焦点


# ==================== 多选行下拉委托 ====================
class MultiSelectRowComboDelegate(ComboDelegate):
    """
    多选行下拉委托
    
    普通下拉：同一行横向多选(>=2)才批量写入；否则只改当前格。
    用于非材料的普通下拉字段，批量将选中的值写入同一行的其他选中列。
    """

    def __init__(self, options, table=None):
        """初始化多选行委托"""
        super().__init__(options, table)
        self._targets_cache = []   # 缓存进入编辑时被选中的列号列表

    def _snapshot_targets(self, row: int):
        """快照当前行被选中的可编辑列（在进入编辑前调用）"""
        cols = []
        sm = self.table.selectionModel() if self.table else None
        if sm:
            for i in sm.selectedIndexes():
                if i.row() == row:
                    it = self.table.item(row, i.column())
                    if it and (it.flags() & Qt.ItemIsEditable):
                        cols.append(i.column())
        cols = sorted(set(cols))
        return cols

    def createEditor(self, parent, option, index):
        """进入编辑前先把"多选列"快照下来"""
        self._targets_cache = self._snapshot_targets(index.row())
        return super().createEditor(parent, option, index)

    def _selected_cols_same_row(self, row):
        """获取同一行中被多选的列（至少2列）"""
        sm = self.table.selectionModel()
        if not sm: 
            return []
        cols = sorted({i.column()
                       for i in sm.selectedIndexes()
                       if i.row() == row and self.table.item(row, i.column())
                       and (self.table.item(row, i.column()).flags() & Qt.ItemIsEditable)})
        return cols if len(cols) >= 2 else []

    def setModelData(self, editor, model, index):
        """批量写入多选列"""
        # 先正常写回当前格
        super().setModelData(editor, model, index)

        row, col = index.row(), index.column()
        new_text = editor.currentText()

        # 使用快照中的目标列（进入编辑时选中的列），如果没有则重新获取
        targets = list(self._targets_cache) if self._targets_cache else self._snapshot_targets(row)
        self._targets_cache = []   # 清空缓存

        if not targets:
            return   # 没有需要批量写入的列

        # 批量写入其他选中列（排除当前列）
        self.table.blockSignals(True)
        try:
            for cc in targets:
                if cc == col:
                    continue
                it = self.table.item(row, cc) or QTableWidgetItem()
                it.setTextAlignment(Qt.AlignCenter)
                it.setText(new_text or "")
                self.table.setItem(row, cc, it)
        finally:
            self.table.blockSignals(False)
        self.table.setCurrentCell(row, col)   # 恢复当前单元格


# ==================== 多选动态选项委托 ====================
class MultiSelectDynamicOptionsDelegate(DynamicOptionsDelegate):
    """
    多选动态选项委托
    
    材料四字段专用：只有多选时才批量；逐列校验候选并逐列联动。
    同时针对"材料牌号"字段做了特殊优化：仅根据材料类型过滤牌号选项。
    """

    def __init__(self, table, groups, row2field, row2group):
        """初始化多选动态选项委托"""
        super().__init__(table, groups, row2field, row2group)
        self._targets_cache = []   # 缓存选中的列号

    def _snapshot_targets(self, row: int):
        """快照同一行已选中的可编辑列（至少2列）"""
        sm = self.table.selectionModel() if self.table else None
        if not sm:
            return []
        cols = sorted({
            i.column() for i in sm.selectedIndexes()
            if i.row() == row
               and self.table.item(row, i.column())
               and (self.table.item(row, i.column()).flags() & Qt.ItemIsEditable)
        })
        return cols if len(cols) >= 2 else []

    def createEditor(self, parent, option, index):
        """创建编辑器，材料牌号特殊处理（仅依赖材料类型）"""
        from PyQt5.QtWidgets import QComboBox
        from modules.cailiaodingyi.funcs.funcs_pdf_change import get_filtered_material_options

        # 进入编辑前先快照多选列
        self._targets_cache = self._snapshot_targets(index.row())

        field = self._field_of_row(index.row())
        # 针对材料牌号字段做特殊优化：只根据材料类型过滤，避免依赖其他字段导致选项过多或过少
        if field == '材料牌号':
            grp = self._group_map_of_row(index.row()) or {}
            type_row = grp.get('材料类型')
            # 同列下，读取"材料类型"的当前值
            cur_type = ""
            if type_row is not None:
                it = self.table.item(type_row, index.column())
                cur_type = (it.text().strip() if it else "")

            # 仅按类型过滤，拿到"该类型下的所有牌号"
            brand_opts = []
            if cur_type:
                m = get_filtered_material_options({'材料类型': cur_type}) or {}
                brand_opts = list(dict.fromkeys(m.get('材料牌号', []) or []))

            # 构造一个简单的单选下拉框（不可编辑）
            cb = QComboBox(parent)
            cb.setEditable(False)
            cb.addItems(brand_opts)   # 注意：没有添加空项，因为牌号通常不应为空

            # 添加自动提交机制（选中即提交并关闭）
            def _commit_and_close():
                self.commitData.emit(cb)
                self.closeEditor.emit(cb, QStyledItemDelegate.NoHint)

            cb.activated.connect(lambda _=None: _commit_and_close())
            cb.currentIndexChanged.connect(lambda _=None: _commit_and_close())

            # 进入即弹出下拉框
            QTimer.singleShot(0, cb.showPopup)
            return cb

        # 其他字段仍用父类默认编辑器（动态选项）
        return super().createEditor(parent, option, index)

    def _cur_vals(self, grp, col):
        """获取指定列的当前四个字段的值"""
        d = {}
        for k in ('材料类型','材料牌号','材料标准','供货状态'):
            rr = grp.get(k)
            it = self.table.item(rr, col) if rr is not None else None
            d[k] = (it.text().strip() if it else "")
        return d

    def setEditorData(self, editor, index):
        """设置编辑器数据，材料牌号特殊处理"""
        from PyQt5.QtWidgets import QComboBox
        field = self._field_of_row(index.row())
        # 对于材料牌号的特制编辑器，需要单独设置当前文本
        if isinstance(editor, QComboBox) and field == '材料牌号':
            cur = (index.data() or "").strip()
            if cur:
                pos = editor.findText(cur)
                if pos >= 0:
                    editor.setCurrentIndex(pos)
            return
        # 其他情况使用父类逻辑
        return super().setEditorData(editor, index)

    def setModelData(self, editor, model, index):
        """保存数据并批量联动"""
        from PyQt5.QtWidgets import QComboBox
        field = self._field_of_row(index.row())
        # 材料牌号特制编辑器的数据保存
        if isinstance(editor, QComboBox) and field == '材料牌号':
            txt = editor.currentText() or ""
            model.setData(index, txt)
            # 调用父类保存到表格（确保UI同步）
            super().setModelData(editor, model, index)
        else:
            # 其他字段正常保存
            super().setModelData(editor, model, index)

        # 以下保持原有的批量联动逻辑
        row, col = index.row(), index.column()
        sender_field = self._field_of_row(row)
        # 只处理材料字段
        if sender_field not in ('材料类型', '材料牌号', '材料标准', '供货状态'):
            return

        # 获取需要批量写入的目标列（使用缓存，如果没有则重新快照）
        targets = list(getattr(self, "_targets_cache", []) or self._snapshot_targets(row))
        self._targets_cache = []   # 清空缓存
        if not targets:
            return   # 没有多选，只修改了当前格，不需要批量

        grp = self._group_map_of_row(row)
        new_val = model.data(index) or ""

        from modules.cailiaodingyi.funcs.funcs_pdf_change import get_filtered_material_options

        # 1) 如果改动了"材料类型"，需要清空其余三项（逐列进行）
        if sender_field == '材料类型':
            type_row = grp.get('材料类型')
            brand_row = grp.get('材料牌号')
            std_row = grp.get('材料标准')
            stat_row = grp.get('供货状态')

            self.table.blockSignals(True)
            try:
                # 将当前列及其他选中的列都纳入清空范围
                cols_to_apply = sorted(set(targets + [col]))
                for cc in cols_to_apply:
                    old_type = ""
                    if type_row is not None:
                        it = self.table.item(type_row, cc)
                        old_type = (it.text().strip() if it else "")
                    # 只有当材料类型确实发生变化时才清空其他字段
                    if (new_val or "") != (old_type or ""):
                        for rr in (brand_row, std_row, stat_row):
                            if rr is None:
                                continue
                            it2 = self.table.item(rr, cc)
                            if it2 is None:
                                it2 = QTableWidgetItem("")
                                it2.setTextAlignment(Qt.AlignCenter)
                                self.table.setItem(rr, cc, it2)
                            if it2.text():
                                it2.setText("")
            finally:
                self.table.blockSignals(False)

        # 2) 批量把"同字段"的值写到其它被选列（并做候选校验）
        touched_cols = []   # 记录实际被写入的列，用于后续联动
        self.table.blockSignals(True)
        try:
            for cc in targets:
                if cc == col:
                    continue   # 当前列已经处理过
                # 该列的当前四字段值
                cur_vals = {}
                for k in ('材料类型', '材料牌号', '材料标准', '供货状态'):
                    rr = grp.get(k)
                    it = self.table.item(rr, cc) if rr is not None else None
                    cur_vals[k] = (it.text().strip() if it else "")

                # 候选生成逻辑（与DynamicOptionsDelegate类似）
                if sender_field == '材料类型':
                    all_map = get_filtered_material_options({}) or {}
                    opts = list(dict.fromkeys(all_map.get('材料类型', [])))
                else:
                    if sender_field == '材料牌号' and cur_vals.get('材料类型'):
                        filtered = get_filtered_material_options({'材料类型': cur_vals['材料类型']}) or {}
                        opts = filtered.get('材料牌号', []) or []
                    else:
                        basis = {k: v for k, v in cur_vals.items() if k != sender_field and v}
                        filtered = get_filtered_material_options(basis) or {}
                        opts = filtered.get(sender_field, []) or []

                if not opts or (opts and opts[0] != ""):
                    opts = [""] + list(dict.fromkeys(opts))

                # 如果新值在候选列表中，则写入该列对应的字段
                if new_val in opts:
                    rr = grp.get(sender_field)
                    if rr is not None:
                        it = self.table.item(rr, cc) or QTableWidgetItem()
                        it.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(rr, cc, it)
                        if it.text().strip() != (new_val or ""):
                            it.setText(new_val or "")
                            touched_cols.append(cc)   # 记录实际发生写入的列
        finally:
            self.table.blockSignals(False)

        # 3) 逐列触发联动回调（清空依赖字段等）
        for cc in touched_cols:
            if cc == col:
                continue
            prev_cc = ""   # 由于没有保存变化前的值，这里传空（联动函数内部会通过当前值判断）
            on_material_field_changed_col(self.table, cc, grp, sender_field, prev_value=prev_cc)













