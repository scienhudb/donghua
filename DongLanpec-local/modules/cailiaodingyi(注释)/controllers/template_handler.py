# ==================== 导入必要的模块 ====================
import re  # 提供正则表达式支持（当前未直接使用，但保留以备后续匹配操作）
from collections import defaultdict  # 提供默认字典，方便键值对自动初始化（当前未直接使用，但保留）
from functools import partial  # 用于冻结函数的某些参数，方便在信号连接时传递额外参数

# PyQt5 相关控件和核心模块
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt, QTimer, QObject

# 项目内部模块：数据管理器（模板加载、切换确认）
from modules.cailiaodingyi.controllers.datamanager import (
    load_data_by_template, ask_before_switch_template_against_current
)
# 自定义的无滚轮组合框过滤器（防止鼠标滚轮意外改变下拉项）
from modules.cailiaodingyi.demo import NoWheelComboBoxFilter
# 与管口定义相关的数据库操作函数
from modules.cailiaodingyi.funcs.funcs_pdf_change import (
    update_guankou_define_data,      # 更新管口零件定义数据
    update_guankou_define_status,    # 更新管口定义状态（是否全部定义完成）
    load_element_data_by_product_id, # 根据产品ID加载元件数据
    is_all_guankou_parts_defined,    # 判断所有管口零件是否已定义完
    get_filtered_material_options,   # 根据筛选条件获取材料可选值（联动）
    query_template_name_by_product    # 查询产品当前使用的模板名称
)
# 与PDF输入相关的辅助函数（移动管口顺序、更新模板可编辑状态）
from modules.cailiaodingyi.funcs.funcs_pdf_input import (
    move_guankou_to_first,              # 将管口元件移到列表第一位
    move_guankou_attachment_to_second,  # 将管口附件移到第二位
    update_template_input_editable_state # 更新模板输入的可编辑状态（保存为模板）
)
# 清除产品的手动修改标志（条件输入模块）
from modules.condition_input.funcs.funcs_cdt_input import clear_manual_flags_for_product


# ==================== 模板切换处理函数 ====================
def handle_template_change(viewer_instance, index):
    print("handle_template_change called with index:", index)

    # 获取选中的模板名称，并去除首尾空格
    selected_template = viewer_instance.comboBox_template.itemText(index).strip()
    # 特殊处理：如果模板名称为空字符串，则设置为"None"（表示无模板状态）
    if not selected_template:
        selected_template = "None"
        print(f"[调试] 模板名称为空，设置为: '{selected_template}'")

    # 获取当前产品ID
    pid = getattr(viewer_instance, "product_id", None)
    # 若没有产品ID，则无法切换模板，弹出错误提示并返回
    if not pid:
        viewer_instance.show_error_message("提示", "未检测到产品ID，无法切换模板")
        return

    # 切换模板相当于重新按新模板初始化，因此清空该产品下所有的手动修改标记（仅内存中的标志）
    clear_manual_flags_for_product(pid)

    # ✅ 先尝试从数据库取
    old_template = query_template_name_by_product(pid)
    print(f"old{old_template}")
    # ✅ 如果取不到，就 fallback 用当前控件保存的 current_template_name
    if not old_template:
        old_template = getattr(viewer_instance, "current_template_name", "").strip()

    # 弹出询问对话框，让用户确认是否在切换模板前保留当前数据（如果有未保存修改）
    ok = ask_before_switch_template_against_current(
        viewer_instance,
        pid,
        base_template_name=old_template,
        target_template_name=selected_template
    )
    # 用户取消切换：恢复下拉框的原有索引，并退出
    if not ok:
        print("[模板切换] 用户取消")
        try:
            viewer_instance._template_reverting = True
            viewer_instance.comboBox_template.blockSignals(True)   # 临时阻断信号
            viewer_instance.comboBox_template.setCurrentIndex(getattr(viewer_instance, "_template_prev_index", 0))
        finally:
            viewer_instance.comboBox_template.blockSignals(False)  # 恢复信号
            viewer_instance._template_reverting = False
        return

    # 用户确认切换：根据选中的模板名称加载对应的数据（重新初始化表格等）
    load_data_by_template(viewer_instance, selected_template)

    # 更新视图实例中记录的当前模板名称和索引，供下次切换时比较
    viewer_instance.current_template_name = selected_template
    viewer_instance._template_prev_index = index


# ==================== 初始化模板下拉框的钩子 ====================
def init_template_combo_hooks(self):
    """
    在界面建立好且下拉框已有值之后调用一次，用于绑定模板切换的信号槽，
    并保存初始状态以便取消切换时恢复。
    :param self: 通常是主窗口实例（或视图实例）
    """
    # 记录当前模板名称（去除首尾空格）
    self.current_template_name = self.comboBox_template.currentText().strip()
    # 记录当前下拉框的索引，用于取消切换时恢复
    self._template_prev_index = self.comboBox_template.currentIndex()
    # 标记当前是否正在执行模板恢复操作（防止递归）
    self._template_reverting = False
    # 当下拉框的 activated 信号触发时（用户选择新索引），调用 handle_template_change
    self.comboBox_template.activated.connect(
        lambda idx: handle_template_change(self, idx)
    )


# ==================== 为“管口材料分类”表格注入刷新函数（旧式，已弃用但保留） ====================
def inject_material_refresh(combo: QComboBox, table: QTableWidget, row: int, col: int):
    """
    重写组合框的 mousePressEvent，使得在下拉菜单弹出前先刷新选项列表。
    此函数目前未被新版本使用，保留仅为兼容性。
    :param combo: 需要注入刷新的组合框
    :param table: 所属表格
    :param row: 行索引
    :param col: 列索引
    """
    # 定义刷新选项的回调函数
    def refresh_options_before_dropdown():
        on_pipe_material_combobox_changed(table, row, col)

    # 保存原始的 mousePressEvent 方法
    original_mouse_press = combo.mousePressEvent

    # 定义新的 mousePressEvent
    def new_mouse_press(event):
        refresh_options_before_dropdown()  # 先刷新选项
        original_mouse_press(event)        # 再执行原始事件（弹出下拉列表）

    combo.mousePressEvent = new_mouse_press

# def apply_combobox_to_table(table: QTableWidget, column_data_map: dict,
#                             guankou_define_info, product_id,
#                             viewer_instance, category_label: str):
#     """
#     给管口零件表格的定义设置下拉框
#     """
#     # ✅ 彻底清除旧控件
#     for row in range(table.rowCount()):
#         for col in range(table.columnCount()):
#             table.removeCellWidget(row, col)
#
#     # ✅ 确保每个单元格有 QTableWidgetItem（避免 .text() 报错）
#     for row in range(table.rowCount()):
#         for col in range(table.columnCount()):
#             if not table.item(row, col):
#                 table.setItem(row, col, QTableWidgetItem(""))
#
#     # ✅ 插入 ComboBox 并绑定信号
#     for row in range(table.rowCount()):
#         for col, items in column_data_map.items():
#             # 获取当前单元格显示文本（使用 viewport 渲染过的数据）
#             item = table.item(row, col)
#             current_text = item.text().strip() if item else ""
#
#             # 创建下拉框
#             combo = QComboBox()
#             combo.addItem("")
#             combo.setEditable(True)
#             combo.lineEdit().setAlignment(Qt.AlignCenter)
#             combo.setStyleSheet("""
#                 QComboBox {
#                     border: none;
#                     background-color: transparent;
#                     font-size: 9pt;
#                     font-family: "Microsoft YaHei";
#                     padding-left: 2px;
#                 }
#             """)
#             combo.addItems(items)
#
#             combo.blockSignals(True)
#             if current_text in items:
#                 combo.setCurrentText(current_text)
#             else:
#                 combo.setCurrentIndex(0)
#             combo.blockSignals(False)
#
#             # print(f"row {row}, col {col} 原始值：'{current_text}'，选中下拉值：'{combo.currentText()}'")
#
#             # 设置下拉框替代原单元格内容
#             table.setItem(row, col, None)
#             table.setCellWidget(row, col, combo)
#
#             combo.currentIndexChanged.connect(partial(
#                 on_combo_changed, guankou_define_info, table, row, col,
#                 product_id, viewer_instance, category_label
#             ))
#             combo.currentIndexChanged.connect(partial(
#                 on_pipe_material_combobox_changed, table, row, col
#             ))
#
#             QTimer.singleShot(0, lambda r=row, c=col: on_pipe_material_combobox_changed(table, r, c))
#
#         # # ✅ 每行控件设置完后，主动刷新一次联动逻辑
#         # on_material_field_changed_row(table, row)
def apply_combobox_to_table(table: QTableWidget, column_data_map: dict,
                            guankou_define_info, product_id,
                            viewer_instance, category_label: str):
    """
    设置“管口材料分类”表格的四字段联动下拉框（列式结构）。
    每一行包含四个组合框：材料类型、材料牌号、材料标准、供货状态。
    当任一字段改变时，其他字段的选项会根据数据库中的约束关系自动过滤。
    :param table: 目标表格控件
    :param column_data_map: 列号 -> 该列所有可能选项的列表（例如 {1: ["锻件","铸件"], 2: [...]}）
    :param guankou_define_info: 管口定义数据列表，每行包含“管口零件ID”等信息
    :param product_id: 当前产品ID
    :param viewer_instance: 主窗口实例（用于更新界面和数据库）
    :param category_label: 分类标签（例如“管口”或“附件”）
    """
    # 定义列号到字段名的映射（表格的第1~4列对应四个材料属性）
    col_to_field = {
        1: '材料类型',
        2: '材料牌号',
        3: '材料标准',
        4: '供货状态'
    }
    # 反向映射：字段名 -> 列号
    field_to_col = {v: k for k, v in col_to_field.items()}

    # 先清空表格中所有已有的控件（避免残留的旧组合框）
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            table.removeCellWidget(row, col)
            # 确保每个单元格都有一个 QTableWidgetItem，避免后续 .text() 调用出错
            if not table.item(row, col):
                table.setItem(row, col, QTableWidgetItem(""))

    # 遍历每一行，为每行的四个列分别创建组合框并设置联动
    for row in range(table.rowCount()):
        combo_map = {}  # 用于临时存储该行每个字段对应的组合框对象

        # 为当前行的每个字段列创建组合框
        for col, field in col_to_field.items():
            # 获取当前单元格中已有的文本（来自数据库的数据）
            current_text = table.item(row, col).text().strip()

            # 创建组合框，设置为可编辑（允许用户输入不在列表中的值）
            combo = QComboBox()
            combo.setEditable(True)
            # 设置样式：无边框、透明背景、字体大小和字体族
            combo.setStyleSheet("""
                QComboBox {
                    border: none;
                    background-color: transparent;
                    font-size: 9pt;
                    font-family: "Microsoft YaHei";
                    padding-left: 2px;
                }
            """)
            # 组合框的编辑区文字居中
            combo.lineEdit().setAlignment(Qt.AlignCenter)

            # 获取该列的所有可选值（从 column_data_map 中预加载）
            all_options = column_data_map.get(col, [])
            # 添加一个空项（表示未选择），再添加所有可选值
            combo.addItem("")
            combo.addItems(all_options)
            # 将完整的选项列表保存为组合框的自定义属性，以便后续刷新时使用
            combo.full_options = all_options.copy()

            # 为组合框的每个选项设置 tooltip（悬浮时显示完整文本）
            for i in range(combo.count()):
                combo.setItemData(i, combo.itemText(i), Qt.ToolTipRole)

            # 自动调整下拉列表视图的宽度，使其适应最长的选项文本
            if all_options:
                max_text_width = max([combo.fontMetrics().width(text) for text in all_options] + [0])
                combo.view().setMinimumWidth(max_text_width + 40)  # 加40像素留白，避免贴边

            # 设置当前选中的文本（如果数据库值在选项列表中，则选中它，否则选空）
            if current_text in all_options:
                combo.setCurrentText(current_text)
            else:
                combo.setCurrentIndex(0)

            # 安装事件过滤器，禁止鼠标滚轮滚动时改变组合框的值（防止误操作）
            combo.installEventFilter(NoWheelComboBoxFilter(combo))

            # 将表格的对应列清空，并把组合框作为单元格控件放置进去
            table.setItem(row, col, None)
            table.setCellWidget(row, col, combo)

            # 记录当前字段对应的组合框对象
            combo_map[field] = combo

        # ========== 绑定联动信号 ==========
        # 为每个组合框的文本改变信号（currentTextChanged）连接一个统一的处理函数
        # 该处理函数会刷新整行所有组合框的可用选项
        for field, combo in combo_map.items():
            col = field_to_col[field]
            # 使用 partial 固定部分参数：表格、行号、列到字段映射、列数据映射
            combo.currentTextChanged.connect(
                partial(on_material_combobox_changed_rowwise, table, row, col_to_field, column_data_map)
            )

            # 另外还要连接数据保存的函数：当用户改变下拉值时，更新数据库
            combo.currentIndexChanged.connect(partial(
                on_combo_changed, guankou_define_info, table, row, col,
                product_id, viewer_instance, category_label
            ))

        # 初始化时主动触发一次联动刷新，确保各字段的选项符合当前已选内容（如有初始值）
        QTimer.singleShot(0, partial(on_material_combobox_changed_rowwise, table, row, col_to_field, column_data_map))


# ==================== 下拉框值改变后的数据库更新函数 ====================
def on_combo_changed(guankou_define_info, table, row, col, product_id, viewer_instance, category_label):
    """
    当任意一个材料下拉框的值发生变化时调用，将新值更新到数据库中对应的管口零件记录。
    :param guankou_define_info: 管口定义数据列表（每行包含管口零件ID）
    :param table: 表格控件
    :param row: 行号
    :param col: 列号
    :param product_id: 产品ID
    :param viewer_instance: 主窗口实例
    :param category_label: 分类标签（“管口”或“附件”等）
    """
    # 获取当前单元格中的组合框，并取得当前选中的文本（去除首尾空格）
    combo = table.cellWidget(row, col)
    new_value = combo.currentText().strip()
    print(f"更新的数据{new_value}")

    # 获取当前行的管口定义数据（其中包含“管口零件ID”）
    clicked_guankou_define_data = guankou_define_info[row]
    print(f"点击的行数据: {clicked_guankou_define_data}")

    # 从行数据中取出管口零件ID
    guankou_id = clicked_guankou_define_data.get("管口零件ID", None)
    print(f"获取到的管口零件ID: {guankou_id}")

    # 定义列号与数据库字段名的映射（与表格列顺序一致）
    column_map = {1: '材料类型', 2: '材料牌号', 3: '材料标准', 4: '供货状态'}

    # 获取对应列的字段名
    field_name = column_map.get(col, "未知字段")

    # 为组合框及其编辑框设置 tooltip，鼠标悬浮时显示完整内容
    combo.setToolTip(new_value)
    combo.lineEdit().setToolTip(new_value)
    # 使用 lambda 确保当文本再次变化时，tooltip 也跟着更新
    combo.currentTextChanged.connect(lambda text, c=combo: (
        c.setToolTip(text),
        c.lineEdit().setToolTip(text)
    ))
    print(f"更新的字段: {field_name}")

    # 调用数据库更新函数，将新值写入到对应的管口零件记录的指定字段
    update_guankou_define_data(product_id, new_value, field_name, guankou_id, category_label)

    element_name = "管口"

    # 检查该产品下的所有管口零件是否都已经定义完整（即四个材料字段都有有效值）
    if is_all_guankou_parts_defined(viewer_instance.product_id):
        # 若全部定义完成，则更新管口定义状态（可能触发后续流程）
        # update_guankou_define_status(product_id, element_name)  # 此行被注释，可能暂时不需要
        # 重新加载元件数据
        update_element_info = load_element_data_by_product_id(product_id)
        # 调整元件顺序：将管口元件移到第一位，管口附件移到第二位
        updated_element_info = move_guankou_to_first(update_element_info)
        updated_element_info = move_guankou_attachment_to_second(updated_element_info)
        print(f"更新后的元件列表{updated_element_info}")
        # 将调整后的元件数据重新渲染到主表格中
        viewer_instance.render_data_to_table(updated_element_info)
        # 注：原本有一行 update_template_input_editable_state(viewer_instance) 被注释，表示不自动保存为模板


# ==================== 旧的单行联动刷新函数（已弃用，但保留） ====================
def on_material_field_changed_row(table: QTableWidget, row: int):
    """
    旧版联动逻辑：当某一行某一字段改变时，刷新整行的选项（已弃用，不再被调用）。
    保留仅为历史参考。
    """
    material_fields = {
        '材料类型': 1,
        '材料牌号': 2,
        '材料标准': 3,
        '供货状态': 4
    }
    col_to_field = {v: k for k, v in material_fields.items()}
    field_to_col = {v: k for k, v in col_to_field.items()}
    selected = {}
    combo_map = {}

    sender = table.sender()
    sender_field = ""

    # 读取当前行所有字段的值和组合框对象
    for col, field in col_to_field.items():
        combo = table.cellWidget(row, col)
        if isinstance(combo, QComboBox):
            combo_map[field] = combo
            val = combo.currentText().strip()
            if val:
                selected[field] = val
            if combo is sender:
                sender_field = field

    # 特例：修改材料类型时，若新值为空则清空其他三项；若其他三项不兼容则清空
    if sender_field == "材料类型":
        # 如果材料类型为空，直接清空后三项
        if not selected.get("材料类型", ""):
            for field in ['材料牌号', '材料标准', '供货状态']:
                combo = combo_map[field]
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("")
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))
                combo.blockSignals(False)
            selected = {}  # 全清空
        # 否则如果材料类型不兼容其他三项 → 清空不兼容项
        elif all(k in selected for k in ['材料牌号', '材料标准', '供货状态']):
            filter_basis = {"材料类型": selected["材料类型"]}
            valid_options = get_filtered_material_options(filter_basis)
            if any(selected[k] not in valid_options.get(k, []) for k in ['材料牌号', '材料标准', '供货状态']):
                for field in ['材料牌号', '材料标准', '供货状态']:
                    combo = combo_map[field]
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem("")
                    table.setItem(row, field_to_col[field], QTableWidgetItem(""))
                    combo.blockSignals(False)
                selected = {"材料类型": selected["材料类型"]}

    # 特例：改动材料牌号后不兼容后两项，清空
    if sender_field == "材料牌号" and all(k in selected for k in material_fields.keys()):
        filter_basis = {
            "材料类型": selected["材料类型"],
            "材料牌号": selected["材料牌号"]
        }
        valid = get_filtered_material_options(filter_basis)
        for field in ['材料标准', '供货状态']:
            current_val = selected.get(field, "")
            if current_val not in valid.get(field, []):
                combo = combo_map[field]
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("")
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))
                combo.blockSignals(False)
                selected.pop(field, None)

    # 联动刷新（注意各字段使用不同条件）
    for field, combo in combo_map.items():
        current_val = combo.currentText().strip()
        if field == "材料类型":
            valid_options = combo.full_options if hasattr(combo, 'full_options') else get_filtered_material_options({}).get(field, [])
        elif field == "材料牌号":
            filter_basis = {"材料类型": selected.get("材料类型", "")}
            valid_options = get_filtered_material_options(filter_basis).get(field, [])
        else:
            filter_basis = {k: v for k, v in selected.items() if k != field and k in ["材料标准", "供货状态"]}
            valid_options = get_filtered_material_options(filter_basis).get(field, [])

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(valid_options)
        if current_val in valid_options:
            combo.setCurrentText(current_val)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)


# ==================== 旧式管道材料联动刷新（已弃用） ====================
def on_pipe_material_combobox_changed(table: QTableWidget, row: int, changed_col: int):
    """
    旧版联动刷新（与 inject_material_refresh 配合使用），基于改变的列重新过滤所有列。
    现已不被新版调用，保留仅为参考。
    """
    col_to_field = {
        1: '材料类型',
        2: '材料牌号',
        3: '材料标准',
        4: '供货状态'
    }

    selected = {}
    combo_map = {}

    # 读取当前行所有组合框的当前值
    for col, field in col_to_field.items():
        combo = table.cellWidget(row, col)
        if isinstance(combo, QComboBox):
            combo_map[field] = combo
            val = combo.currentText().strip()
            if val:
                selected[field] = val

    # 根据当前选中的字段（排除自身）过滤每个字段的选项列表
    for col, field in col_to_field.items():
        combo = combo_map[field]
        current_val = combo.currentText().strip()

        filter_basis = {k: v for k, v in selected.items() if k != field}
        filtered = get_filtered_material_options(filter_basis)
        valid_options = filtered.get(field, [])

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(valid_options)

        if current_val in valid_options:
            combo.setCurrentText(current_val)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)


# ==================== 新版联动刷新函数（按行） ====================
def on_material_combobox_changed_rowwise(table: QTableWidget, row: int,
                                         col_to_field: dict, column_data_map: dict):
    """
    新版联动逻辑：当某一行内任意一个材料字段组合框的文本改变时，重新计算所有四个字段的可用选项，
    并根据依赖关系自动清空不兼容的选项或自动填入唯一值。
    :param table: 表格控件
    :param row: 当前行号
    :param col_to_field: 列号到字段名的映射（如 {1:'材料类型', 2:'材料牌号', ...}）
    :param column_data_map: 列号到该列所有原始选项的映射（用于刷新“材料类型”的完整列表）
    """
    selected = {}          # 存储当前行各字段已选中的值（非空）
    combo_map = {}         # 存储字段名 -> 组合框对象的映射
    field_to_col = {v: k for k, v in col_to_field.items()}  # 字段名 -> 列号

    # 1. 收集当前行所有组合框的当前文本
    for col, field in col_to_field.items():
        combo = table.cellWidget(row, col)
        if isinstance(combo, QComboBox):
            combo_map[field] = combo
            val = combo.currentText().strip()
            if val:
                selected[field] = val

    # 2. 识别是哪个组合框触发了本次刷新（通过信号发送者）
    sender_combo = QObject.sender(table)  # 获取发出信号的控件
    sender_field = ""                     # 记录触发的字段名
    for field, combo in combo_map.items():
        if combo is sender_combo:
            sender_field = field
            break

    # ✅ 材料类型始终显示全部
    if "材料类型" in combo_map:
        combo = combo_map["材料类型"]
        current_val = combo.currentText().strip()
        full_options = column_data_map.get(field_to_col["材料类型"], [])
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(full_options)
        combo.setCurrentText(current_val if current_val in full_options else "")
        combo.blockSignals(False)

    # ✅ 材料类型为空 → 清空后三项
    if sender_field == "材料类型":
        if not selected.get("材料类型", ""):
            for field in ["材料牌号", "材料标准", "供货状态"]:
                combo = combo_map[field]
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("")
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))
                combo.blockSignals(False)
            selected = {}  # 清空已选字典
        # 如果材料类型有值，但其他三个字段当前值与此材料类型不兼容 → 清空它们
        elif all(k in selected for k in ["材料牌号", "材料标准", "供货状态"]):
            filter_basis = {"材料类型": selected["材料类型"]}
            valid_options = get_filtered_material_options(filter_basis)
            if any(selected[k] not in valid_options.get(k, []) for k in ["材料牌号", "材料标准", "供货状态"]):
                for field in ["材料牌号", "材料标准", "供货状态"]:
                    combo = combo_map[field]
                    combo.blockSignals(True)
                    combo.clear()
                    combo.addItem("")
                    table.setItem(row, field_to_col[field], QTableWidgetItem(""))
                    combo.blockSignals(False)
                selected = {"材料类型": selected["材料类型"]}  # 只保留材料类型

    # 5. 如果触发的字段是“材料牌号” → 清空“材料标准”和“供货状态”（因为牌号改变后，标准和状态通常需要重新选择）
    if sender_field == "材料牌号":
        for field in ["材料标准", "供货状态"]:
            combo = combo_map[field]
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("")
            table.setItem(row, field_to_col[field], QTableWidgetItem(""))
            combo.blockSignals(False)
        selected.pop("材料标准", None)
        selected.pop("供货状态", None)

    # ✅ 联动刷新其余字段，自动填入唯一选项
    for field in ["材料牌号", "材料标准", "供货状态"]:
        combo = combo_map[field]
        current_val = combo.currentText().strip()

        # 根据字段的不同，构建不同的筛选条件
        if field == "材料牌号":
            filter_basis = {"材料类型": selected.get("材料类型", "")}
        elif field == "材料标准":
            filter_basis = {
                "材料类型": selected.get("材料类型", ""),
                "材料牌号": selected.get("材料牌号", "")
            }
        elif field == "供货状态":
            filter_basis = {
                "材料类型": selected.get("材料类型", ""),
                "材料牌号": selected.get("材料牌号", ""),
                "材料标准": selected.get("材料标准", "")
            }
        else:
            filter_basis = {}

        # 从数据库获取经过筛选后的有效选项列表
        valid_options = get_filtered_material_options(filter_basis).get(field, [])

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(valid_options)

        # 智能设置当前选中值：
        #   - 如果原来的值仍在有效列表中，保留它
        #   - 否则，如果有效列表只有一个选项，自动填入该唯一值（提升用户体验）
        #   - 否则，置为空
        if current_val in valid_options:
            combo.setCurrentText(current_val)
        elif len(valid_options) == 1:
            combo.setCurrentText(valid_options[0])  # ✅ 自动填入唯一值
        else:
            combo.setCurrentIndex(0)
            table.setItem(row, field_to_col[field], QTableWidgetItem(""))
        combo.blockSignals(False)


# ==================== 为表格所有单元格设置 Tooltip ====================
def set_table_tooltips(table: QTableWidget):
    """
    遍历整个表格，为每个单元格（包括普通单元格和组合框控件）设置悬浮提示（tooltip）。
    对于普通单元格，提示内容即为单元格文本；对于组合框，提示当前选中的文本。
    :param table: 要设置 tooltip 的表格控件
    """
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            # 如果该单元格放置的是一个组合框控件
            cell_widget = table.cellWidget(row, col)
            if isinstance(cell_widget, QComboBox):
                current_text = cell_widget.currentText()
                if current_text.strip():
                    cell_widget.setToolTip(current_text)
            else:
                # 否则是普通的 QTableWidgetItem
                item = table.item(row, col)
                if item and item.text().strip():
                    item.setToolTip(item.text())