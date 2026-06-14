from typing import Callable
import weakref

import sip

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QComboBox, QTableWidget


def ensure_table_tooltip_updater(
    table: QTableWidget,
    *,
    combo_formatter=None,
    item_formatter=None,
) -> Callable[[], None]:
    """
    确保为指定的表格安装 tooltip（悬浮提示）自动更新机制
    
    当表格内容变化时，自动更新所有单元格的悬浮提示文本。
    支持普通单元格和下拉框单元格两种类型。
    
    Args:
        table: 需要安装 tooltip 自动更新的表格组件
        combo_formatter: 下拉框 tooltip 格式化函数，接收 (下拉框对象, 行号, 列号)，返回字符串
                        如果返回空字符串或 None，则清空 tooltip
                        默认为使用下拉框当前文本
        item_formatter: 普通单元格 tooltip 格式化函数，接收 (单元格项对象, 行号, 列号)，返回字符串
                       如果返回空字符串或 None，则清空 tooltip
                       默认为使用单元格文本
    
    Returns:
        一个可调用对象，执行后会立即刷新整张表格的 tooltip
    
    Example:
        # 使用默认格式化器
        updater = ensure_table_tooltip_updater(table)
        
        # 自定义格式化器
        def custom_combo_fmt(combo, row, col):
            return f"第{row}行第{col}列: {combo.currentText()}"
        
        updater = ensure_table_tooltip_updater(table, combo_formatter=custom_combo_fmt)
    """

    # 如果没有提供下拉框格式化函数，默认使用下拉框当前显示的文本
    if combo_formatter is None:
        combo_formatter = lambda combo, row, col: combo.currentText().strip()

    # 如果没有提供普通单元格格式化函数，默认使用单元格的文本内容
    if item_formatter is None:
        item_formatter = lambda item, row, col: (item.text() or "").strip()

    # 获取表格上已安装的 tooltip 支持结构（如果有的话）
    support = getattr(table, "_tooltip_support", None)

    # 首次安装：创建 tooltip 自动更新支持结构
    if support is None:
        support = {
            "pending": False,          # 是否有待处理的更新任务
            "destroyed": False,        # 表格是否已被销毁
            "table_ref": weakref.ref(table),  # 表格的弱引用，避免循环引用
        }
        table._tooltip_support = support  # type: ignore[attr-defined]

        # 标记表格已销毁的回调函数
        def mark_destroyed():
            support["destroyed"] = True

        table.destroyed.connect(mark_destroyed)

        # 调度更新函数：延迟到下一个事件循环再执行更新，避免频繁刷新
        def schedule_update():
            if support["pending"] or support["destroyed"]:
                return

            support["pending"] = True

            def _run():
                support["pending"] = False
                if not support["destroyed"]:
                    update_all()

            QTimer.singleShot(0, _run)

        support["schedule_update"] = schedule_update

        # 绑定下拉框的信号，使其内容变化时触发 tooltip 更新
        def bind_combo(combo: QComboBox):
            # 如果已经连接过信号，跳过
            if getattr(combo, "_tooltip_support_connected", False):
                return

            # 检查控件是否已被删除
            if sip.isdeleted(combo):
                return

            # 连接文本变化信号到更新调度器
            combo.currentTextChanged.connect(schedule_update)
            combo.editTextChanged.connect(schedule_update)
            combo._tooltip_support_connected = True  # type: ignore[attr-defined]

        support["bind_combo"] = bind_combo

        # 更新所有单元格的 tooltip
        def update_all():
            # 通过弱引用获取表格对象
            table_ref = support["table_ref"]()
            if table_ref is None or sip.isdeleted(table_ref):
                support["destroyed"] = True
                return

            combo_fmt = support["combo_formatter"]
            item_fmt = support["item_formatter"]

            # 遍历所有单元格，设置 tooltip
            for row in range(table_ref.rowCount()):
                for col in range(table_ref.columnCount()):
                    cell_widget = table_ref.cellWidget(row, col)
                    if isinstance(cell_widget, QComboBox):
                        # 处理下拉框单元格
                        if sip.isdeleted(cell_widget):
                            continue

                        # 使用格式化函数生成 tooltip 文本
                        tooltip = combo_fmt(cell_widget, row, col)
                        cell_widget.setToolTip("" if tooltip is None else str(tooltip))
                        # 确保下拉框已绑定更新信号
                        bind_combo(cell_widget)
                    else:
                        # 处理普通文本单元格
                        item = table_ref.item(row, col)
                        if not item:
                            continue
                        if sip.isdeleted(item):
                            continue
                        tooltip = item_fmt(item, row, col)
                        item.setToolTip("" if tooltip is None else str(tooltip))

        support["update_all"] = update_all

        # 只在首次安装时连接信号，监听表格数据变化
        model = table.model()
        schedule = support["schedule_update"]
        if model:
            model.dataChanged.connect(lambda *args: schedule())      # 数据改变
            model.rowsInserted.connect(lambda *args: schedule())     # 行插入
            model.rowsRemoved.connect(lambda *args: schedule())      # 行删除
            model.modelReset.connect(schedule)                       # 模型重置
            model.layoutChanged.connect(lambda *args: schedule())    # 布局改变

        table.itemChanged.connect(lambda *args: schedule())   # 单元格项改变
        table.cellChanged.connect(lambda *args: schedule())   # 单元格内容改变

    # 更新格式化函数并立即刷新一次
    support["combo_formatter"] = combo_formatter
    support["item_formatter"] = item_formatter

    update_now = support["update_all"]
    update_now()

    return update_now


