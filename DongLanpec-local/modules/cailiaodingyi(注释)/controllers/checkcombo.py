"""复选框下拉委托模块 - 实现支持多选的下拉框控件"""
from PyQt5.QtWidgets import QStyledItemDelegate, QComboBox, QTableWidgetItem
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QColor
from PyQt5.QtCore import Qt, QTimer, QItemSelectionModel, QEvent, QModelIndex


class CheckComboDelegate(QStyledItemDelegate):
    def __init__(self, options=None, table=None, sep="、", enable_select_all=False):
        """
        options: list[str]  复选项（作为兜底）；实际会优先读取 table.property('gk_code_candidates')
        table:   QTableWidget 用于行高亮（可为 None）
        sep:     显示/存储分隔符
        enable_select_all: bool  是否启用"全选"功能（默认False）
        
        说明：enable_select_all 参数用于控制是否在下拉框中显示"全选"选项。
        - 管口元件（管口号）：传入 enable_select_all=True，显示"全选"功能，方便一键选择所有管口号
        - 其他元件（支座、铭牌、保温装置等的元件名称）：使用默认值 False，不显示"全选"功能
        """
        super().__init__(table)
        self.options = options or []
        self.table = table
        self.sep = sep
        # 控制是否启用"全选"功能：True=管口元件有全选，False=其他元件无全选
        self.enable_select_all = enable_select_all
        self.select_all_label = "全选"

    # ---------- QStyledItemDelegate ----------
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setEditable(False)
        combo.setInsertPolicy(QComboBox.NoInsert)

        # ★★改动点1：拿"最新候选"——优先从表属性读取，失败用构造时的options兜底
        cands = self._get_candidates(option, index)
        print(f"[CheckComboDelegate] createEditor: 最终使用的候选选项: {cands}")

        # 模型：第0行显示文本；1..n为可勾选项
        model = QStandardItemModel(combo)
        display_item = QStandardItem("")         # 显示聚合文本
        display_item.setFlags(Qt.NoItemFlags)    # 不可选
        model.appendRow(display_item)

        # 追加"全选"行（仅在启用时）
        # 说明：只有管口元件（enable_select_all=True）才会添加"全选"选项
        #       其他元件（支座、铭牌、保温装置等）不会显示"全选"
        if self.enable_select_all and cands:
            select_all_item = QStandardItem(self.select_all_label)
            select_all_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            select_all_item.setData(Qt.Unchecked, Qt.CheckStateRole)
            select_all_item.setData(True, Qt.UserRole)  # 标记为全选行
            model.appendRow(select_all_item)

        for opt in cands:
            it = QStandardItem(str(opt))
            it.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
            it.setData(Qt.Unchecked, Qt.CheckStateRole)
            model.appendRow(it)

        combo.setModel(model)
        combo.setCurrentIndex(0)
        #11.19 设备法兰复选框新增
        try:
            setattr(combo, "_delegate_index", index)
            setattr(combo, "_delegate_model", index.model())
        except Exception:
            pass

        # 点击仅切换勾选，不改变currentIndex，不关闭popup；随后再自动弹出
        combo.view().pressed.connect(lambda mi: self._on_pressed(mi, combo))

        # 进入编辑即弹出
        QTimer.singleShot(0, combo.showPopup)

        # 可选：行高亮
        if self.table:
            sel = self.table.selectionModel()
            if sel:
                sel.clearSelection()
                sel.select(index, QItemSelectionModel.Select | QItemSelectionModel.Rows)
                self.table.setCurrentIndex(index)
            self._highlight_row(index.row())

        return combo

    def setEditorData(self, editor: QComboBox, index):
        """
        将单元格数据回写到编辑器（恢复勾选状态）
        
        当编辑器创建完成后，将单元格中已保存的值（如"N1、N6"）解析为各个选项的勾选状态。
        
        参数:
            editor: QComboBox - 下拉框编辑器
            index: QModelIndex - 单元格索引
        """
        # 把单元格里的 "N1、N6" 回写为勾选状态
        text = (index.model().data(index, Qt.EditRole) or "").strip()
        selected = [t for t in text.split(self.sep) if t]
        for it in self._iter_option_items(editor):
            it.setCheckState(Qt.Checked if it.text() in selected else Qt.Unchecked)
        
        # 只有管口元件才需要同步"全选"状态，其他元件无需此操作
        if self.enable_select_all:
            self._sync_select_all_state(editor)
        
        self._update_display_text(editor)

    def setModelData(self, editor: QComboBox, model, index):
        """
        将编辑器的数据保存到模型
        
        当编辑完成时，将所有勾选的选项用分隔符连接后保存到单元格。
        
        参数:
            editor: QComboBox - 下拉框编辑器
            model: QAbstractItemModel - 数据模型
            index: QModelIndex - 单元格索引
        """
        model.setData(index, self._selected_text(editor), Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        """
        更新编辑器的几何位置
        
        参数:
            editor: QComboBox - 下拉框编辑器
            option: QStyleOptionViewItem - 样式选项
            index: QModelIndex - 单元格索引
        """
        editor.setGeometry(option.rect)

    def editorEvent(self, event, model, option, index):
        """
        处理编辑器事件
        
        拦截鼠标点击事件，使点击单元格即可立即进入编辑模式（弹出下拉框）。
        
        参数:
            event: QEvent - 事件对象
            model: QAbstractItemModel - 数据模型
            option: QStyleOptionViewItem - 样式选项
            index: QModelIndex - 单元格索引
        
        返回:
            bool: 是否处理了事件
        """
        # 点击单元格立即进入编辑（弹出）
        if event.type() == QEvent.MouseButtonPress:
            parent = option.widget
            if parent:
                parent.edit(index)
        return super().editorEvent(event, model, option, index)

    # =========================================================================
    # 辅助方法
    # =========================================================================
    
    def _on_pressed(self, mi: QModelIndex, combo: QComboBox):
        """
        处理下拉框中选项的点击事件
        
        执行流程：
        1. 如果点击的是显示行（第0行），无操作
        2. 如果点击的是"全选"行（且启用全选功能），切换所有选项的勾选状态
        3. 否则，切换当前选项的勾选状态，并同步"全选"行状态
        4. 更新显示文本
        5. 立即提交数据到模型和表格
        6. 保持下拉框打开状态
        
        参数:
            mi: QModelIndex - 被点击的项的索引
            combo: QComboBox - 下拉框编辑器
        """
        row = mi.row()
        if row == 0:                 # 点显示行，无操作
            combo.setCurrentIndex(0)
            return
        
        it = combo.model().item(row)
        
        # "全选"行：全开/全关（仅在启用时）
        # 说明：只有管口元件（enable_select_all=True）才会处理"全选"点击事件
        #       其他元件（支座、铭牌、保温装置等）不会进入此分支
        if self.enable_select_all and self._is_select_all_item(it):
            target = Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked
            it.setCheckState(target)
            for opt in self._iter_option_items(combo):
                opt.setCheckState(target)
        else:
            it.setCheckState(Qt.Unchecked if it.checkState() == Qt.Checked else Qt.Checked)
            # 只有管口元件才需要同步"全选"状态，其他元件无需此操作
            if self.enable_select_all:
                self._sync_select_all_state(combo)
        
        self._update_display_text(combo)
        
        # 11.19 设备法兰复选框新增
        # 立即提交数据，避免必须回车/切焦
        try:
            self.commitData.emit(combo)
        except Exception:
            pass
        
        # 同步写回模型与表格单元格文本
        try:
            txt = self._selected_text(combo)
            idx = getattr(combo, "_delegate_index", None)
            mdl = getattr(combo, "_delegate_model", None)
            if idx is not None and mdl is not None:
                mdl.setData(idx, txt, Qt.EditRole)
            if self.table is not None and idx is not None:
                r, c = idx.row(), idx.column()
                it2 = self.table.item(r, c)
                if it2 is None:
                    it2 = QTableWidgetItem()
                    it2.setTextAlignment(Qt.AlignCenter)
                    it2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    self.table.setItem(r, c, it2)
                it2.setText(txt)
        except Exception:
            pass

        combo.setCurrentIndex(0)
        # 关键：保持下拉不关闭，立刻再弹出
        QTimer.singleShot(0, combo.showPopup)

    def _selected_text(self, combo: QComboBox) -> str:
        """
        获取所有勾选选项的连接文本
        
        遍历所有选项项，收集被勾选的选项，用分隔符连接后返回。
        
        参数:
            combo: QComboBox - 下拉框编辑器
        
        返回:
            str: 勾选选项的连接文本，如"N1、N6"
        """
        vals = []
        for it in self._iter_option_items(combo):
            if it.checkState() == Qt.Checked:
                vals.append(it.text())
        return self.sep.join(vals)

    def _update_display_text(self, combo: QComboBox):
        """
        更新下拉框第0行的显示文本
        
        将当前所有勾选的选项用分隔符连接后，显示在第0行（显示行）。
        
        参数:
            combo: QComboBox - 下拉框编辑器
        """
        combo.model().item(0).setText(self._selected_text(combo))
        combo.setCurrentIndex(0)

    def _iter_option_items(self, combo: QComboBox):
        """
        迭代器：返回所有真正的选项项（跳过显示行和"全选"行）
        
        参数:
            combo: QComboBox - 下拉框编辑器
        
        返回:
            generator: 生成QStandardItem对象的迭代器
        """
        model = combo.model()
        for row in range(1, model.rowCount()):
            it = model.item(row)
            if it and not self._is_select_all_item(it):
                yield it

    def _is_select_all_item(self, item: QStandardItem) -> bool:
        """
        判断一个项是否为"全选"项
        
        通过检查Qt.UserRole数据来判断，该角色在创建"全选"项时被设置为True。
        
        参数:
            item: QStandardItem - 要判断的项
        
        返回:
            bool: True表示是"全选"项
        """
        try:
            return bool(item.data(Qt.UserRole))
        except Exception:
            return False

    def _sync_select_all_state(self, combo: QComboBox):
        """
        根据实际选中情况更新"全选"行的勾选状态
        
        如果所有选项都被勾选，则"全选"行也勾选；否则取消勾选。
        
        参数:
            combo: QComboBox - 下拉框编辑器
        """
        model = combo.model()
        # "全选"行位于第1行（如果存在）
        all_item = model.item(1) if model.rowCount() > 1 else None
        if all_item and self._is_select_all_item(all_item):
            opts = list(self._iter_option_items(combo))
            if not opts:
                all_item.setCheckState(Qt.Unchecked)
            else:
                all_checked = all(opt.checkState() == Qt.Checked for opt in opts)
                all_item.setCheckState(Qt.Checked if all_checked else Qt.Unchecked)

    def _highlight_row(self, row: int):
        """
        高亮显示指定行
        
        将表格中指定行的所有单元格背景色设置为浅蓝色（#d0e7ff），
        同时将其他行的背景色恢复为白色。
        
        参数:
            row: int - 要高亮的行号
        """
        if not self.table:
            return
        # 清除所有行的高亮
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                it = self.table.item(r, c)
                if it:
                    it.setBackground(QColor("#ffffff"))
        # 高亮当前行
        for c in range(self.table.columnCount()):
            it = self.table.item(row, c)
            if it:
                it.setBackground(QColor("#d0e7ff"))

    # ★★改动点2：读取最新候选
    def _get_candidates(self, option, index):
        """
        获取最新的候选选项列表
        
        优先级：
        1. 从table.property('gk_code_candidates')读取（动态更新的候选列表）
        2. 回退到构造时传入的self.options（兜底选项）
        
        这种设计允许外部代码动态更新候选选项，而无需重新创建委托对象。
        
        参数:
            option: QStyleOptionViewItem - 样式选项
            index: QModelIndex - 单元格索引
        
        返回:
            list: 候选选项列表
        """
        # 尝试拿到当前表对象
        table = self.table
        if table is None:
            # QTableWidget通常就是option.widget
            table = getattr(option, "widget", None)
        if table is not None:
            cands = table.property("gk_code_candidates")
            if cands:
                # 转为list，确保可迭代
                print(f"[CheckComboDelegate] 从table.property读取候选选项: {list(cands)}")
                return list(cands)
        
        # 兜底：构造时传入的options
        print(f"[CheckComboDelegate] 使用构造时传入的选项: {list(self.options)}")
        return list(self.options)

    @staticmethod
    def _find_row(table, label_text: str):
        """
        在表格的第一列中查找指定文本的行号
        
        参数:
            table: QTableWidget - 表格对象
            label_text: str - 要查找的文本
        
        返回:
            int or None: 找到的行号，未找到返回None
        """
        for r in range(table.rowCount()):
            it = table.item(r, 0)
            if it and it.text().strip() == label_text:
                return r
        return None

    @staticmethod
    def _set_text_center(table, r, c, txt):
        """
        在表格指定单元格设置居中文本
        
        如果单元格不存在，则创建一个新的TableWidgetItem。
        
        参数:
            table: QTableWidget - 表格对象
            r: int - 行号
            c: int - 列号
            txt: str - 要设置的文本
        """
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem()
            it.setTextAlignment(Qt.AlignCenter)
            it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
            table.setItem(r, c, it)
        it.setText(txt or "")
