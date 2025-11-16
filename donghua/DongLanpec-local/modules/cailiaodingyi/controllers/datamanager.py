import re
from functools import partial
from typing import Optional

from PyQt5 import QtWidgets, QtCore
from PyQt5.QtCore import Qt, QTimer, QEvent
from PyQt5.QtGui import QDoubleValidator
from PyQt5.QtWidgets import QTableWidgetItem, QTableWidget, QComboBox, QDoubleSpinBox, QMessageBox, QLineEdit, QLabel, \
    QAbstractItemView, QStyledItemDelegate, QDialog, QVBoxLayout, QPushButton, QWidget

from modules.cailiaodingyi.controllers.checkcombo import CheckComboDelegate
from modules.cailiaodingyi.controllers.combo import ComboDelegate, MaterialInstantDelegate
from modules.cailiaodingyi.db_cnt import get_connection
from modules.cailiaodingyi.demo import NoWheelComboBoxFilter
from modules.cailiaodingyi.funcs.funcs_pdf_change import (
    load_element_additional_data,
    load_guankou_define_data,
    load_guankou_para_data,
    insert_or_update_element_data,
    insert_or_update_guankou_material_data,
    insert_or_update_guankou_para_data,
    insert_or_update_element_para_data,
    update_param_table_data,
    update_left_table_db_from_param_table,
    toggle_covering_fields,
    load_element_data_by_product_id,
    load_element_additional_data_by_product,
    update_guankou_define_data,
    update_guankou_define_status,
    load_updated_guankou_define_data,
    update_guankou_param,
    load_updated_guankou_param_data,
    load_guankou_para_data_leibie, is_all_guankou_parts_defined, get_filtered_material_options, save_image,
    query_image_from_database, get_dependency_mapping_from_db, toggle_dependent_fields,
    toggle_dependent_fields_multi_value, query_param_by_component_id, get_gasket_param_from_db,
    get_design_params_from_db, get_gasket_contact_dims_from_db, query_template_id, query_guankou_image_from_database,
    update_element_para_data, toggle_dependent_fields_complex, get_corrosion_allowance_from_db,
    update_guankou_category_for_tab, save_guankou_codes_for_tab, query_template_codes,
    update_guankou_params_bulk, get_numeric_rules, load_update_guankou_para_data,
    clear_guankou_category, evaluate_visibility_rules_from_db, query_guankou_codes, fetch_product_element_materials,
    fetch_template_element_materials, diff_product_vs_template, query_tube_specs_by_level_and_od,
    map_gasket_name_code, map_gasket_type_code_from_db,
    query_gasket_D_d_d1_from_size, get_dn_for_gasket, get_pn_for_gasket, resolve_gasket_dimensions,
    query_extra_param_value, query_gasket_material_options_by_type_std, db_config_1, db_config_2, sync_baffle_thickness_to_db,
    update_spacer_tube_status_to_undefined, restore_spacer_tube_status_to_defined
)
from modules.cailiaodingyi.funcs.funcs_pdf_input import (
    load_elementoriginal_data,
    move_guankou_to_first,
    load_guankou_material_detail,
    query_template_guankou_para_data,
    query_template_element_para_data,
    load_material_dropdown_values, query_guankou_define_data_by_category, update_template_input_editable_state,
    load_guankou_material_detail_template, get_options_for_param, get_all_param_name,
    is_flatcover_trim_param_applicable, query_unassigned_codes, load_tab_assigned_codes, query_guankou_default,
    insert_guankou_info
)
from modules.cailiaodingyi.funcs.funcs_pdf_render import render_guankou_param_to_ui, FreezeUI
from modules.condition_input.funcs.funcs_cdt_input import sync_design_params_to_element_params, \
    sync_corrosion_to_guankou_param


# def apply_combobox_to_table(table: QTableWidget, column_data_map: dict, viewer_instance, category_label: str):
#     """
#     给管口零件表格的定义设置下拉框
#     """
#     # 字段列索引和字段名映射
#     col_to_field = {1: '材料类型', 2: '材料牌号', 3: '材料标准', 4: '供货状态'}
#
#     # 初始化下拉框
#     for row in range(table.rowCount()):
#         for col, options in column_data_map.items():
#             current_text = table.item(row, col).text().strip() if table.item(row, col) else ""
#
#             # 创建下拉框
#             combo = QComboBox()
#             combo.addItem("")
#             combo.addItems(options)
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
#
#             combo.blockSignals(True)
#             index = combo.findText(current_text.strip(), Qt.MatchFixedString)
#             if index >= 0:
#                 combo.setCurrentIndex(index)
#             else:
#                 combo.setCurrentIndex(0)
#             combo.blockSignals(False)
#
#             table.setItem(row, col, None)
#             table.setCellWidget(row, col, combo)
#
#             # 绑定保存逻辑
#             combo.currentIndexChanged.connect(partial(on_combo_changed, viewer_instance, table, col, category_label))
#
#
#             # 绑定联动逻辑（只绑定，不执行）
#             if col in col_to_field:
#                 combo.currentTextChanged.connect(partial(on_material_field_changed_row, table, row))
#
#     # 👉 使用 QTimer 延后触发联动初始化，避免信号冲突
#     def delayed_linkage():
#         for row in range(table.rowCount()):
#             on_material_field_changed_row(table, row)
#
#     QTimer.singleShot(0, delayed_linkage)
def apply_combobox_to_table(table: QTableWidget, column_data_map: dict, viewer_instance, category_label: str):
    """
    设置“管口材料分类”表格的四字段联动下拉框（列式结构），绑定保存 + 联动逻辑
    """
    col_to_field = {1: '材料类型', 2: '材料牌号', 3: '材料标准', 4: '供货状态'}
    field_to_col = {v: k for k, v in col_to_field.items()}

    for row in range(table.rowCount()):
        for col, options in column_data_map.items():
            current_text = table.item(row, col).text().strip() if table.item(row, col) else ""

            combo = QComboBox()
            combo.setEditable(True)
            combo.addItem("")
            combo.addItems(options)
            combo.lineEdit().setAlignment(Qt.AlignCenter)
            combo.setStyleSheet("""
                QComboBox {
                    border: none;
                    background-color: transparent;
                    font-size: 9pt;
                    font-family: "Microsoft YaHei";
                    padding-left: 2px;
                }
            """)
            combo.full_options = options.copy()

            combo.blockSignals(True)
            combo.installEventFilter(NoWheelComboBoxFilter(combo))
            index = combo.findText(current_text.strip(), Qt.MatchFixedString)
            combo.setCurrentIndex(index if index >= 0 else 0)
            combo.blockSignals(False)

            table.setItem(row, col, None)
            table.setCellWidget(row, col, combo)

            # ✨设置 tooltip
            for i in range(combo.count()):
                combo.setItemData(i, combo.itemText(i), Qt.ToolTipRole)

            # ✅ 设置下拉框宽度适配最长项
            max_text_width = max([combo.fontMetrics().width(text) for text in combo.full_options] + [0])
            combo.view().setMinimumWidth(max_text_width + 40)  # 加40避免贴边

            # ✅ 保存逻辑
            combo.currentIndexChanged.connect(partial(
                on_combo_changed, viewer_instance, table, col, category_label
            ))

            # ✅ 联动逻辑（行联动，点击或选值均触发）
            if col in col_to_field:
                combo.currentTextChanged.connect(partial(
                    on_material_field_changed_row, table, row
                ))

    # ✅ 初始化完成后延迟触发一次联动（防止加载时闪跳）
    def delayed_init():
        for row in range(table.rowCount()):
            on_material_field_changed_row(table, row)

    QTimer.singleShot(0, delayed_init)


# def on_material_field_changed_row(table: QTableWidget, row: int):
#     material_fields = {
#         '材料类型': 1,
#         '材料牌号': 2,
#         '材料标准': 3,
#         '供货状态': 4
#     }
#     col_to_field = {v: k for k, v in material_fields.items()}
#     selected = {}
#
#     # 获取当前行已有值
#     for col, field in col_to_field.items():
#         combo = table.cellWidget(row, col)
#         if isinstance(combo, QComboBox):
#             val = combo.currentText().strip()
#             if val:
#                 selected[field] = val
#
#     filtered_options = get_filtered_material_options(selected)
#
#     # 更新字段
#     for col, field in col_to_field.items():
#         combo = table.cellWidget(row, col)
#         if not isinstance(combo, QComboBox):
#             continue
#         current_val = combo.currentText().strip()
#         new_options = filtered_options.get(field, [])
#
#         combo.blockSignals(True)
#         combo.clear()
#         combo.addItem("")
#         combo.addItems(new_options)
#         if current_val in new_options:
#             combo.setCurrentText(current_val)
#         else:
#             combo.setCurrentIndex(0)
#         combo.blockSignals(False)
def on_material_field_changed_row(table: QTableWidget, row: int):
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
    cleared_fields = set()  # ⬅️ 新增：记录哪些字段被清空

    sender = table.sender()
    sender_field = ""

    # 读取当前行所有字段值 & 控件
    for col, field in col_to_field.items():
        combo = table.cellWidget(row, col)
        if isinstance(combo, QComboBox):
            combo_map[field] = combo
            val = combo.currentText().strip()
            if val:
                selected[field] = val
            if combo is sender:
                sender_field = field

    # 强制清空材料类型变更时的后三项（无论值合不合法）
    if sender_field == "材料类型":
        for field in ["材料牌号", "材料标准", "供货状态"]:
            for r in range(table.rowCount()):
                param_item = table.item(r, 0)
                if param_item and param_item.text().strip() == field:
                    combo = table.cellWidget(r, 1)
                    if isinstance(combo, QComboBox):
                        combo.blockSignals(True)
                        combo.clear()
                        combo.addItem("")
                        combo.setCurrentIndex(0)
                        combo.lineEdit().clear()  # ✅ 关键：清除 lineEdit 显示内容
                        combo.blockSignals(False)
                    table.setItem(r, 1, QTableWidgetItem(""))  # 确保 TableItem 也清空
                    break

    # ✅ 材料牌号改动 → 若不兼容 → 清空标准、供货状态
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
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))  # 清除文本
                combo.blockSignals(False)
                cleared_fields.add(field)  # ⬅️ 标记为清空
                selected.pop(field, None)

    # ✅ 联动刷新
    for field, combo in combo_map.items():
        current_val = combo.currentText().strip()
        all_options = getattr(combo, "full_options", [])

        # 生成筛选条件
        if field == "材料类型":
            valid_options = all_options  # 不限制
        elif field == "材料牌号":
            filter_basis = {
                "材料类型": selected.get("材料类型", "")
            }
            valid_options = get_filtered_material_options(filter_basis).get(field, [])
        elif field == "材料标准":
            filter_basis = {
                "材料类型": selected.get("材料类型", ""),
                "材料牌号": selected.get("材料牌号", "")
            }
            valid_options = get_filtered_material_options(filter_basis).get(field, [])
        elif field == "供货状态":
            filter_basis = {
                "材料类型": selected.get("材料类型", ""),
                "材料牌号": selected.get("材料牌号", ""),
                "材料标准": selected.get("材料标准", "")
            }
            valid_options = get_filtered_material_options(filter_basis).get(field, [])
        else:
            valid_options = []

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(valid_options)

        # ✅ 每次材料类型变更后，强制清空后三项；其余字段则根据选项数量决定是否自动填入
        if sender_field == "材料类型" and field in ["材料牌号", "材料标准", "供货状态"]:
            if len(valid_options) == 1:
                combo.blockSignals(True)
                combo.setCurrentText(valid_options[0])
                combo.blockSignals(False)
            else:
                combo.setCurrentIndex(0)
                combo.lineEdit().clear()
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))
        elif field not in cleared_fields:
            # 非材料类型发起时：若旧值合法 → 保留；否则清空
            if current_val in valid_options:
                combo.setCurrentText(current_val)
            elif len(valid_options) == 1:
                combo.setCurrentText(valid_options[0])
            else:
                combo.setCurrentIndex(0)
                combo.lineEdit().clear()
                table.setItem(row, field_to_col[field], QTableWidgetItem(""))

        combo.blockSignals(False)


def on_clear_param_update(viewer_instance):
    """
    清空参数数值列，写库并刷新界面（不清空“元件名称”）
    """
    param_table = viewer_instance.tableWidget_detail
    row_count = param_table.rowCount()
    param_value_col = 1
    param_name_col  = 0

    preserved_params = {"管程侧是否添加覆层", "壳程侧是否添加覆层", "是否添加覆层"}
    skip_params_ui_db = {"元件名称"}   # ✅ UI 与 DB 都保留

    # 信息样式确认弹窗
    box = QtWidgets.QMessageBox(
        QtWidgets.QMessageBox.Information,
        "清空确认",
        "清空后不可撤销，是否继续？",
        QtWidgets.QMessageBox.NoButton,
        param_table
    )
    btn_ok = box.addButton("确认", QtWidgets.QMessageBox.YesRole)
    btn_cancel = box.addButton("取消", QtWidgets.QMessageBox.NoRole)
    box.setDefaultButton(btn_cancel)
    box.exec_()
    if box.clickedButton() is not btn_ok:
        print("[清空] 用户取消操作")
        return

    # 清空参数数值列（处理文本和控件）
    for row in range(row_count):
        name_item = param_table.item(row, param_name_col)
        param_name = name_item.text().strip() if name_item else ""

        # ✅ 跳过“元件名称”
        if param_name in skip_params_ui_db:
            continue

        cell_widget = param_table.cellWidget(row, param_value_col)
        if cell_widget:
            if isinstance(cell_widget, QtWidgets.QComboBox):
                if param_name in preserved_params:
                    idx = cell_widget.findText("否")
                    cell_widget.setCurrentIndex(idx if idx >= 0 else 0)
                else:
                    cell_widget.setCurrentIndex(0)
            elif isinstance(cell_widget, QtWidgets.QLineEdit):
                if param_name in preserved_params:
                    cell_widget.setText("否")
                else:
                    cell_widget.clear()
            elif isinstance(cell_widget, QtWidgets.QSpinBox):
                # 统一清 0，若要最小值可改回 minimum()
                cell_widget.setValue(0 if param_name not in preserved_params else 0)
            else:
                pass
        else:
            item = param_table.item(row, param_value_col)
            if not item:
                item = QtWidgets.QTableWidgetItem("")
                param_table.setItem(row, param_value_col, item)
            item.setText("否" if param_name in preserved_params else "")

    # 写库
    selected_ids = getattr(viewer_instance, "selected_element_ids", [])
    if len(selected_ids) > 1:
        print(f"[多选] 批量清空元件ID: {selected_ids}")
        for eid in selected_ids:
            update_param_table_data(param_table, viewer_instance.product_id, eid)
            part_info = next((it for it in viewer_instance.element_data if it["元件ID"] == eid), {})
            update_left_table_db_from_param_table(param_table, viewer_instance.product_id, eid, part_info.get("零件名称", ""))
    else:
        clicked = viewer_instance.clicked_element_data
        element_id = clicked.get("元件ID")
        part_name  = clicked.get("零件名称")
        update_param_table_data(param_table, viewer_instance.product_id, element_id)
        update_left_table_db_from_param_table(param_table, viewer_instance.product_id, element_id, part_name)

    # 刷新左表
    updated = load_element_data_by_product_id(viewer_instance.product_id)
    updated = move_guankou_to_first(updated)
    viewer_instance.element_data = updated
    viewer_instance.render_data_to_table(updated)

    # 恢复点击绑定
    try:
        viewer_instance.tableWidget_parts.itemClicked.disconnect()
    except Exception:
        pass
    try:
        viewer_instance.tableWidget_parts.itemClicked.connect(
            lambda item: handle_table_click(viewer_instance, item.row(), item.column())
        )
    except Exception:
        pass




def on_clear_guankou_param_update(viewer_instance):
    """
    安全清空管口参数表格，并同步数据库（使用与保存相同的映射/展开规则）
    """
    # 1) 询问确认 —— 使用标准信息样式的确认框（与“完成”外观一致）
    table = getattr(viewer_instance, "tableWidget_guankou", None)
    if table is None:
        return

    box = QMessageBox(QMessageBox.Information, "清空确认",
                      "清空后不可撤销，是否继续？",
                      QMessageBox.NoButton, table)
    btn_ok = box.addButton("确认", QMessageBox.YesRole)
    btn_cancel = box.addButton("取消", QMessageBox.NoRole)
    box.setDefaultButton(btn_cancel)  # 默认光标在“取消”，更安全
    box.exec_()
    if box.clickedButton() is not btn_ok:
        print("[清空] 用户取消操作")
        return

    # 2) 当前 Tab / 表
    tw = getattr(viewer_instance, "guankou_tabWidget", None)
    if tw is None or tw.currentIndex() < 0:
        print("[清空] 无法定位当前管口Tab")
        return
    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()
    table_param = _get_tab_table(viewer_instance, cur_idx)
    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return

    # 3) UI 清空（不销毁委托/控件，只清文本；两条覆层开关置“否”）
    preserved_params = {"接管是否添加覆层", "接管法兰是否添加覆层"}
    table_param.blockSignals(True)
    try:
        for r in range(table_param.rowCount()):
            it0 = table_param.item(r, 0)
            label_ui = it0.text().strip() if it0 else ""
            if not label_ui:
                continue

            if _is_multi_col_row(table_param, r):
                # 多列行：1/2/3 列全部置空
                for c in (1, 2, 3):
                    it = table_param.item(r, c)
                    if it:
                        it.setText("")
                    else:
                        table_param.setItem(r, c, QTableWidgetItem(""))
            else:
                # 单值行：覆层开关置“否”，其余置空
                v = "否" if label_ui in preserved_params else ""
                it = table_param.item(r, 1)
                if it:
                    it.setText(v)
                else:
                    table_param.setItem(r, 1, QTableWidgetItem(v))
    finally:
        table_param.blockSignals(False)

    # 4) DB 批量清空（与“确定”存库同路径：_ui2db_name + 多列展开）
    try:
        _clear_other_params_for_tab_mapped(
            viewer_instance, table_param,
            viewer_instance.product_id, tab_name,
            preserved_params=preserved_params
        )
    except Exception as e:
        print("[数据库错误] 清空管口参数失败：", e)

    # 5) 同时清空管口占用（管口号）
    try:
        clear_guankou_category(viewer_instance.product_id, tab_name)
    except Exception as e:
        print("[数据库错误] 当前材料清空管口分类失败：", e)




def _clear_other_params_for_tab_mapped(viewer_instance, table_param, product_id, tab_name,
                                       preserved_params: set):
    """
    与 save_other_params_for_tab 同样的映射/展开规则来清空：
      - 单值行 -> (product_id, tab_name, label_db, value='')
      - 多列行 -> (product_id, tab_name, f'{label_db}{i}', value_i='')  i=1..3
      - 覆层开关（preserved_params）写入 '否'
    实际落库时使用 update_guankou_params_bulk(..., treat_empty_as_null=True)，
    让空串写成 NULL（开关除外）。
    """
    rows_to_save = []

    for r in range(table_param.rowCount()):
        it0 = table_param.item(r, 0)
        label_ui = it0.text().strip() if it0 else ""
        if not label_ui or label_ui == "管口号":
            continue

        label_db_base = _ui2db_name(label_ui, viewer_instance)

        if _is_multi_col_row(table_param, r):
            # 多列行：展开 label1/label2/label3 -> 全置空
            value_cols = [1, 2, 3] if table_param.columnCount() >= 4 else [1, 2]
            for i, _c in enumerate(value_cols, start=1):
                rows_to_save.append((product_id, tab_name, f"{label_db_base}{i}", ""))
        else:
            # 单值行：覆层开关=“否”，其它=空
            v1 = "否" if label_ui in preserved_params else ""
            rows_to_save.append((product_id, tab_name, label_db_base, v1))

    # 批量更新为 NULL（空串）或“否”
    ret = update_guankou_params_bulk(rows_to_save, treat_empty_as_null=True)
    print(f"[清空-调试] Tab={tab_name} 更新 {ret['updated']} 行, 未命中 {len(ret['missing'])} 行")






def on_combo_changed(viewer_instance, table, col, category_label):

    combo = table.sender()
    if not isinstance(combo, QComboBox):
        return

    for row in range(table.rowCount()):
        if table.cellWidget(row, col) == combo:
            break
    else:
        print("未找到 combo 所在行，跳过")
        return

    new_value = combo.currentText().strip()
    combo.setToolTip(new_value)
    combo.lineEdit().setToolTip(new_value)
    combo.currentTextChanged.connect(lambda text, c=combo: (
        c.setToolTip(text),
        c.lineEdit().setToolTip(text)
    ))

    # print(f"更新的数据: {new_value}")
    # print(f"找到行号: {row}")
    # print(f"{viewer_instance.guankou_define_info}")

    try:
        clicked_guankou_define_data = viewer_instance.guankou_define_info[row]
        # print(f"当前行数据: {clicked_guankou_define_data}")
    except Exception as e:
        print(f"[错误] 获取行数据失败: {e}")
        return

    try:
        guankou_id = clicked_guankou_define_data.get("管口零件ID", None)
        # print(f"获取到的管口零件ID: {guankou_id}")
    except Exception as e:
        print(f"[错误] 获取管口零件ID失败: {e}")
        return

    column_map = {1: '材料类型', 2: '材料牌号', 3: '材料标准', 4: '供货状态'}
    field_name = column_map.get(col, "未知字段")
    # print(f"更新的字段: {field_name}")

    # guankou_additional_info = load_guankou_para_data(guankou_id)
    update_guankou_define_data(viewer_instance.product_id, new_value, field_name, guankou_id, category_label)

    element_name = "管口"

    if (is_all_guankou_parts_defined(viewer_instance.product_id)):
        define_status = "已定义"
    else:
        define_status = "未定义"

    update_guankou_define_status(viewer_instance.product_id, element_name, define_status)
    update_element_info = load_element_data_by_product_id(viewer_instance.product_id)
    update_element_info = move_guankou_to_first(update_element_info)
    viewer_instance.render_data_to_table(update_element_info)
    # 存为模板
    # update_template_input_editable_state(viewer_instance)






# def on_guankou_param_changed(self, row, col, product_id):
#
#     item = self.tableWidget_guankou_param.item(row, col)
#     if not item:
#         return
#
#     new_value = item.text()
#     print(f"新的值{new_value}")
#
#     # 假设第0列是参数名，第1列是参数值
#     param_name = self.tableWidget_guankou_param.item(row, 0).text()
#     print(f"参数名{param_name}")
#     product_id = product_id
#
#     print(f"产品ID: {product_id}, 参数: {param_name}, 值: {new_value}")



def set_table_tooltips(table: QTableWidget):
    """
    为 QTableWidget 所有单元格设置 tooltip（悬浮提示），包含普通单元格和下拉框。
    """
    for row in range(table.rowCount()):
        for col in range(table.columnCount()):
            # 如果单元格是 QComboBox（widget）
            cell_widget = table.cellWidget(row, col)
            if isinstance(cell_widget, QComboBox):
                current_text = cell_widget.currentText()
                if current_text.strip():
                    cell_widget.setToolTip(current_text)
            else:
                item = table.item(row, col)
                if item and item.text().strip():
                    item.setToolTip(item.text())


def apply_paramname_dependent_combobox(table: QTableWidget,
                                       param_col: int,
                                       value_col: int,
                                       param_options: dict,
                                       component_info: dict = None,
                                       viewer_instance = None):
    """
    设置除管口外的零件对应参数信息的下拉框，包括“是否有覆层”固定选项
    """
    material_fields = ['材料类型', '材料牌号', '材料标准', '供货状态']

    for row in range(table.rowCount()):
        try:
            param_item = table.item(row, param_col)
            param_name = param_item.text().strip() if param_item else ""

            # ✅ 材料字段（支持联动）
            if param_name in param_options and param_name in material_fields:
                options = param_options[param_name]

                value_item = table.item(row, value_col)
                current_value = value_item.text().strip() if value_item else ""

                combo = QComboBox()
                combo.addItem("")
                combo.setEditable(True)
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                                QComboBox {
                                    border: none;
                                    background-color: transparent;
                                    font-size: 9pt;
                                    font-family: "Microsoft YaHei";
                                    padding-left: 2px;
                                }
                            """)
                combo.addItems(options)
                combo.full_options = options.copy()

                matched = False
                for i in range(combo.count()):
                    if combo.itemText(i).strip() == current_value:
                        combo.setCurrentIndex(i)
                        matched = True
                        break
                if not matched:
                    combo.setCurrentIndex(0)

                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)
                combo.currentTextChanged.connect(partial(
                    on_material_combobox_changed, table, row, param_col, value_col, 2
                ))
                QTimer.singleShot(0, lambda r=row: on_material_combobox_changed(
                    table, r, param_col, value_col, 2
                ))

            if param_name == "材料类型":
                # 绑定联动逻辑：材料类型为“钢锻件”时，显示“锻件级别”
                combo.currentTextChanged.connect(
                    partial(toggle_dependent_fields, table, combo, "钢锻件", ["锻件级别"], logic="==")
                )
                toggle_dependent_fields(table, combo, "钢锻件", ["锻件级别"], logic="==")

                # ⚠ 如果当前不是“钢锻件”，则清空“锻件级别”字段并写入数据库
                def clear_forging_level_if_needed(val):
                    if val.strip() != "钢锻件":
                        for r in range(table.rowCount()):
                            pname_item = table.item(r, param_col)
                            if pname_item and pname_item.text().strip() == "锻件级别":
                                table.setRowHidden(r, True)

                                # 清空 UI 值
                                combo2 = table.cellWidget(r, value_col)
                                if isinstance(combo2, QComboBox):
                                    combo2.blockSignals(True)
                                    combo2.setCurrentIndex(0)
                                    combo2.lineEdit().clear()
                                    combo2.blockSignals(False)
                                table.setItem(r, value_col, QTableWidgetItem(""))

                                # 清空数据库
                                try:
                                    product_id = viewer_instance.product_id
                                    element_id = viewer_instance.clicked_element_data.get("元件ID", "")
                                    update_element_para_data(product_id, element_id, "锻件级别", "")
                                except Exception as e:
                                    print(f"[清空锻件级别失败] {e}")

                combo.currentTextChanged.connect(clear_forging_level_if_needed)
                # 初始化时触发一次
                clear_forging_level_if_needed(combo.currentText().strip())



            elif param_name == "是否添加覆层":
                value_item = table.item(row, value_col)
                current_value = value_item.text().strip() if value_item else ""
                combo = QComboBox()
                combo.addItems(["是", "否"])
                combo.setEditable(True)
                combo.setCurrentText("是" if current_value == "是" else "否")
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox { border: none; background-color: transparent; font-size: 9pt; font-family: "Microsoft YaHei"; padding-left: 2px; }
                """)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)

                handler = make_on_covering_changed(component_info, viewer_instance, row)
                handler2= make_on_flange_face_changed(component_info, viewer_instance, row)
                handler3 = make_on_head_type_changed(component_info, viewer_instance, row)
                handler4 = make_on_fangchongban_face_changed(component_info, viewer_instance, row)
                handler5 = make_on_fenchenggeban_changed(component_info, viewer_instance, row)

                combo.currentTextChanged.connect(handler)

                handler(combo.currentText())
                handler2(combo.currentText())
                handler3(combo.currentText())
                handler4(combo.currentText())
                handler5(combo.currentText())

                combo.currentTextChanged.connect(
                    lambda _, c=combo, p=param_name: toggle_covering_fields(table, c, p)
                )
                toggle_covering_fields(table, combo, param_name)

            elif param_name in ["管程侧是否添加覆层", "壳程侧是否添加覆层"]:
                value_item = table.item(row, value_col)
                current_value = value_item.text().strip() if value_item else ""
                combo = QComboBox()
                combo.addItems(["是", "否"])
                combo.setEditable(True)
                combo.setCurrentText("是" if current_value == "是" else "否")
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox { border: none; background-color: transparent; font-size: 9pt; font-family: "Microsoft YaHei"; padding-left: 2px; }
                """)

                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)
                combo.currentTextChanged.connect(
                    lambda _, c=combo, p=param_name: toggle_covering_fields(table, c, p)
                )
                toggle_covering_fields(table, combo, param_name)

        except Exception as e:
            print(f"[错误] 第{row}行处理失败：{e}")

    # ⚠ 统一在循环后绑定固定管板双字段逻辑
    if component_info and viewer_instance:
        fields = [table.item(r, param_col).text().strip() for r in range(table.rowCount())]
        if "管程侧是否添加覆层" in fields and "壳程侧是否添加覆层" in fields:
            handler = make_on_fixed_tube_covering_changed_v2(component_info, viewer_instance, table, param_col, value_col)
            handler()

_IMAGE_PATH_CACHE = {}  # key = (template_name, element_id, has_covering, mode) → path

def _query_image_cached(template_name, element_id, has_covering, mode="global"):
    key = (template_name or "", str(element_id or ""), bool(has_covering), mode)
    if key in _IMAGE_PATH_CACHE:
        return _IMAGE_PATH_CACHE[key]
    p = query_image_from_database(template_name, element_id, has_covering)
    _IMAGE_PATH_CACHE[key] = p
    return p

def _set_pixmap_if_changed(viewer_instance, image_path: str):
    """仅当路径变化时才刷新，避免卡顿；空路径则清空。"""
    cur = getattr(viewer_instance, "current_image_path", None)
    if not image_path:
        viewer_instance.label_part_image.clear()
        viewer_instance.current_image_path = None
        return
    if cur == image_path:
        return
    viewer_instance.display_image(image_path)
    viewer_instance.current_image_path = image_path


# ✅ 模块级缓存（记住每行的状态）
# 全局缓存
# 全局缓存（推荐用 comp_name 作为 key，而不是 row_index）
_flange_state_cache = {}
_head_state_cache = {}
_fangchongban_state_cache = {}
_fenchenggeban_state_cache ={}
def make_on_head_type_changed(component_info_copy, viewer_instance_copy, row_index):
    """封头类型代号 → 图片刷新（缓存 head_type_code）"""

    def handler(value, pname):
        def _do():
            try:
                comp_name = (component_info_copy.get("零件名称") or "").strip()
                if comp_name not in ("壳体封头", "管箱封头", "外头盖封头"):
                    return

                # 初始化/更新缓存
                state = _head_state_cache.setdefault(comp_name, {
                    "head_type": "",
                    "covering": "否"
                })

                if pname == "封头类型代号":
                    state["head_type"] = (value or "").strip()
                elif pname in ("是否添加覆层", "是否覆层", "覆层"):
                    state["covering"] = "是" if (value or "").strip() == "是" else "否"
                # 使用缓存里的值
                head_type_code = state["head_type"]
                covering_flag = state["covering"]

                if not head_type_code or not viewer_instance_copy:
                    return

                image_path = _query_head_image(head_type_code, covering_flag, comp_name)
                print("head_type_code:", head_type_code)
                print("comp_name:", comp_name)
                _set_pixmap_if_changed(viewer_instance_copy, image_path)

            except Exception as e:
                print(f"[错误] 第{row_index}行处理封头类型图片失败: {e}")

        QTimer.singleShot(60, _do)

    return handler


def _query_head_image(head_type_code, covering_flag, component_name):
    """材料库：封头示意图表 → 匹配封头类型代号 + 元件名称"""
    connection = None
    try:
        connection = get_connection(**db_config_2)
        with connection.cursor() as cursor:
            sql = """
                SELECT 示意图 FROM 封头示意图表
                WHERE 封头类型代号=%s AND 有无覆层=%s AND 元件名称=%s
                LIMIT 1
            """
            cursor.execute(sql, (head_type_code, covering_flag, component_name))
            row = cursor.fetchone()
            print(row)
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("示意图")
        return row[0] if len(row) > 0 else None

    except Exception as e:
        print(f"[错误] 封头示意图查询失败: {e}")
        return None
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass

def make_on_flange_face_changed(component_info_copy, viewer_instance_copy, row_index):
    """法兰密封面 → 图片刷新（缓存 seal_face_name + covering_flag）"""

    def handler(value, pname):
        def _do():
            try:
                comp_name = (component_info_copy.get("零件名称") or "").strip()
                if "法兰" not in comp_name:
                    return

                # 取/初始化缓存
                state = _flange_state_cache.setdefault(comp_name, {
                    "seal_face": "",
                    "covering": "否"
                })

                # 根据当前行更新状态
                if pname == "法兰密封面":
                    state["seal_face"] = (value or "").strip()

                elif pname in ("是否添加覆层", "是否覆层", "覆层"):
                    state["covering"] = "是" if (value or "").strip() == "是" else "否"

                # 使用缓存里的值
                seal_face_name = state["seal_face"]
                covering_flag = state["covering"]

                if not seal_face_name or not viewer_instance_copy:
                    return

                image_path = _query_flange_image(seal_face_name, covering_flag, comp_name)
                print("seal_face_name:", seal_face_name)
                print("covering_flag:", covering_flag)
                print("comp_name:", comp_name)
                _set_pixmap_if_changed(viewer_instance_copy, image_path)

            except Exception as e:
                print(f"[错误] 第{row_index}行处理法兰密封面图片失败: {e}")

        QTimer.singleShot(60, _do)

    return handler




def _query_flange_image(seal_face_name, covering_flag, component_name):
    """材料库：法兰示意图表 → 匹配密封面名称 + 有无覆层 + 元件名称"""
    connection = None
    try:
        connection = get_connection(**db_config_2)
        with connection.cursor() as cursor:
            sql = """
                SELECT 示意图 FROM 法兰示意图表
                WHERE 密封面名称=%s AND 有无覆层=%s AND 元件名称=%s
                LIMIT 1
            """
            cursor.execute(sql, (seal_face_name, covering_flag, component_name))
            row = cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("示意图")
        return row[0] if len(row) > 0 else None

    except Exception as e:
        print(f"[错误] 法兰示意图查询失败: {e}")
        return None
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
def make_on_fenchenggeban_changed(component_info_copy, viewer_instance_copy, row_index):
    """法兰密封面 → 图片刷新（缓存 seal_face_name + covering_flag）"""

    def handler(value, pname):
        def _do():
            try:
                comp_name = (component_info_copy.get("零件名称") or "").strip()
                if "分程隔板" not in comp_name:
                    return

                # 取/初始化缓存
                state = _fenchenggeban_state_cache.setdefault(comp_name, {
                    "seal_face": "",
                })

                # 根据当前行更新状态
                if pname == "排净孔型式":
                    state["seal_face"] = (value or "").strip()



                # 使用缓存里的值
                seal_face_name = state["seal_face"]

                if not seal_face_name or not viewer_instance_copy:
                    return

                image_path = _query_fenchenggeban_image(seal_face_name, comp_name)

                _set_pixmap_if_changed(viewer_instance_copy, image_path)

            except Exception as e:
                print(f"[错误] 第{row_index}行处理法兰密封面图片失败: {e}")

        QTimer.singleShot(60, _do)

    return handler




def _query_fenchenggeban_image(seal_face_name, component_name):
    """材料库：法兰示意图表 → 匹配密封面名称 + 有无覆层 + 元件名称"""
    connection = None
    try:
        connection = get_connection(**db_config_2)
        with connection.cursor() as cursor:
            sql = """
                SELECT 示意图 FROM 分程隔板示意图表
                WHERE 排净孔型式=%s AND 元件名称=%s
                LIMIT 1
            """
            cursor.execute(sql, (seal_face_name, component_name))
            row = cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("示意图")
        return row[0] if len(row) > 0 else None

    except Exception as e:
        print(f"[错误] 法兰示意图查询失败: {e}")
        return None
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
def make_on_fangchongban_face_changed(component_info_copy, viewer_instance_copy, row_index):
    """法兰密封面 → 图片刷新（缓存 seal_face_name + covering_flag）"""

    def handler(value, pname):
        def _do():
            try:
                comp_name = (component_info_copy.get("零件名称") or "").strip()
                if "防冲板" not in comp_name:
                    return

                # 取/初始化缓存
                state = _fangchongban_state_cache.setdefault(comp_name, {
                    "seal_face": "",
                })

                # 根据当前行更新状态
                if pname == "防冲板形式":
                    state["seal_face"] = (value or "").strip()



                # 使用缓存里的值
                seal_face_name = state["seal_face"]

                if not seal_face_name or not viewer_instance_copy:
                    return

                image_path = _query_fangchongban_image(seal_face_name, comp_name)

                _set_pixmap_if_changed(viewer_instance_copy, image_path)

            except Exception as e:
                print(f"[错误] 第{row_index}行处理法兰密封面图片失败: {e}")

        QTimer.singleShot(60, _do)

    return handler




def _query_fangchongban_image(seal_face_name, component_name):
    """材料库：法兰示意图表 → 匹配密封面名称 + 有无覆层 + 元件名称"""
    connection = None
    try:
        connection = get_connection(**db_config_2)
        with connection.cursor() as cursor:
            sql = """
                SELECT 示意图 FROM 防冲板示意图表
                WHERE 防冲板形式=%s AND 元件名称=%s
                LIMIT 1
            """
            cursor.execute(sql, (seal_face_name, component_name))
            row = cursor.fetchone()
        if not row:
            return None
        if isinstance(row, dict):
            return row.get("示意图")
        return row[0] if len(row) > 0 else None

    except Exception as e:
        print(f"[错误] 法兰示意图查询失败: {e}")
        return None
    finally:
        if connection:
            try:
                connection.close()
            except Exception:
                pass
# ✅ 封装处理函数：绑定每行独立信息，避免闭包错误
def make_on_covering_changed(component_info_copy, viewer_instance_copy, row_index, table=None):
    """全局‘是否添加覆层’ → 图片刷新（一次性去抖，无连接累积）"""
    def handler(value):
        def _do():
            try:
                if not component_info_copy or not viewer_instance_copy:
                    return

                comp_name = component_info_copy.get("零件名称") or ""
                # 如果零件名称中含有"法兰"，则调用法兰处理逻辑
                if "法兰" in comp_name:
                    # 调用 make_on_flange_face_changed 逻辑
                    make_on_flange_face_changed(component_info_copy, viewer_instance_copy, row_index)(value,None)

                    return  # 法兰处理完后不执行原本覆层逻辑
                if "防冲板" in comp_name:
                    make_on_fangchongban_face_changed(component_info_copy, viewer_instance_copy, row_index)(value,None)
                if "分程隔板" in comp_name:
                    make_on_fenchenggeban_changed(component_info_copy, viewer_instance_copy, row_index)(value,None)

                if comp_name in ("壳体封头", "管箱封头", "外头盖封头"):
                    make_on_head_type_changed(component_info_copy, viewer_instance_copy, row_index)(value,None)
                # 原覆层处理逻辑
                has_covering = (value or "").strip() == "是"

                image_path = (component_info_copy.get("零件示意图覆层") if has_covering
                              else component_info_copy.get("零件示意图"))
                if not image_path:
                    template_name = component_info_copy.get("模板名称")
                    element_id = component_info_copy.get("元件ID")
                    image_path = _query_image_cached(template_name, element_id, has_covering, mode="global")
                _set_pixmap_if_changed(viewer_instance_copy, image_path)

            except Exception as e:
                print(f"[错误] 第{row_index}行处理图片失败: {e}")

        QTimer.singleShot(60, _do)

    return handler




def make_on_fixed_tube_covering_changed_v2(component_info_copy, viewer_instance_copy,
                                           table: QTableWidget, param_col: int, value_col: int):
    """固定管板‘管程侧/壳程侧是否添加覆层’ → 图片刷新（无连接累积、不卡顿）"""

    def _compute():
        g_row = k_row = None
        for r in range(table.rowCount()):
            it = table.item(r, param_col)
            if not it:
                continue
            name = it.text().strip()
            if name == "管程侧是否添加覆层":
                g_row = r
            elif name == "壳程侧是否添加覆层":
                k_row = r
        if g_row is None or k_row is None:
            return None

        def _is_yes(row):
            vitem = table.item(row, value_col)
            return (vitem.text().strip() if vitem else "") == "是"

        g_yes = _is_yes(g_row)
        k_yes = _is_yes(k_row)

        default_img = component_info_copy.get("零件示意图") or _query_image_cached(
            component_info_copy.get("模板名称"), component_info_copy.get("元件ID"),
            False, mode="fixed-default"
        )

        if not g_yes and not k_yes:
            return default_img

        image_covering_str = component_info_copy.get("零件示意图覆层", "")
        if not image_covering_str:
            image_covering_str = _query_image_cached(
                component_info_copy.get("模板名称"), component_info_copy.get("元件ID"),
                True, mode="fixed-covering"
            )

        parts = (image_covering_str or "").split('/')
        guancheng_img = parts[0].strip() if len(parts) > 0 and parts[0] else None
        kecheng_img   = parts[1].strip() if len(parts) > 1 and parts[1] else None
        both_img      = parts[2].strip() if len(parts) > 2 and parts[2] else None

        if g_yes and not k_yes:
            return guancheng_img or default_img
        if not g_yes and k_yes:
            return kecheng_img or default_img
        if g_yes and k_yes:
            return both_img or default_img
        return default_img

    def refresh_image():
        # 60ms 去抖；不会产生额外的信号连接
        QTimer.singleShot(60, lambda: _set_pixmap_if_changed(
            viewer_instance_copy, _compute()
        ))

    return refresh_image






def make_on_covering_changed_guankou(component_info_copy, viewer_instance_copy, row_index):
    def handler(value):
        try:
            print(f"[右上表触发图片刷新] 当前 combo 值: '{value}'")
            has_covering = value.strip() == "是"
            print(f"guankou{component_info_copy}")

            if not component_info_copy or not viewer_instance_copy:
                print(f"[跳过] 第{row_index}行：未绑定component_info")
                return

            # 右上表逻辑你现在已经有模板名和ID了
            template_name = component_info_copy.get("模板名称")
            template_id = query_template_id(template_name)
            element_id = component_info_copy.get("管口零件ID")  # 注意这里字段名你已经提供了

            # 查询数据库拿图片路径
            image_path = query_guankou_image_from_database(template_id, element_id, has_covering)
            print(f"材料库中图片路径: {image_path}")

            if image_path:
                viewer_instance_copy.display_image(image_path)
            else:
                print(f"[提示] 第{row_index}行无图片路径")

        except Exception as e:
            print(f"[右上表错误] 第{row_index}行图片处理失败: {e}")

    return handler




def on_material_combobox_changed(table: QTableWidget, changed_row: int, param_col: int, value_col: int, part_col: int):
    material_fields = ['材料类型', '材料牌号', '材料标准', '供货状态']

    part_item = table.item(changed_row, part_col)
    if not part_item:
        return
    part_name = part_item.text().strip()

    selected = {}
    combo_map = {}
    target_rows = []

    for row in range(table.rowCount()):
        if not table.item(row, part_col) or table.item(row, part_col).text().strip() != part_name:
            continue
        param_item = table.item(row, param_col)
        if not param_item:
            continue
        param_name = param_item.text().strip()

        if param_name in material_fields:
            combo = table.cellWidget(row, value_col)
            if not isinstance(combo, QComboBox):
                continue
            val = combo.currentText().strip()
            selected[param_name] = val
            combo_map[param_name] = combo
            target_rows.append((row, param_name, combo))

    changed_field = table.item(changed_row, param_col).text().strip()

    # --- 材料类型为空：直接清空其余三项
    if changed_field == "材料类型" and not selected.get("材料类型"):
        for f in ['材料牌号', '材料标准', '供货状态']:
            combo = combo_map.get(f)
            if combo:
                combo.blockSignals(True)
                combo.setCurrentIndex(0)
                table.setItem(changed_row, value_col, QTableWidgetItem(""))  # 清空表格文字
                combo.blockSignals(False)
        selected.clear()

    # --- 材料类型改动：不受限制，其它三项若不兼容就清空
    if changed_field == "材料类型":
        if all(f in selected for f in ['材料牌号', '材料标准', '供货状态']):
            for f in ['材料牌号', '材料标准', '供货状态']:
                test_basis = {
                    '材料类型': selected['材料类型'],
                    f: selected[f]
                }
                valid = get_filtered_material_options(test_basis).get(f, [])
                if selected[f] not in valid:
                    combo = combo_map[f]
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                    table.setItem(changed_row, value_col, QTableWidgetItem(""))  # 清空表格文字
                    combo.blockSignals(False)
                    selected.pop(f)

    # --- 材料牌号改动：只受材料类型限制，其它两项若不兼容就清空
    if changed_field == "材料牌号":
        if all(f in selected for f in ['材料类型', '材料牌号', '材料标准', '供货状态']):
            for f in ['材料标准', '供货状态']:
                test_basis = {
                    '材料类型': selected['材料类型'],
                    '材料牌号': selected['材料牌号'],
                    f: selected[f]
                }
                valid = get_filtered_material_options(test_basis).get(f, [])
                if selected[f] not in valid:
                    combo = combo_map[f]
                    combo.blockSignals(True)
                    combo.setCurrentIndex(0)
                    table.setItem(changed_row, value_col, QTableWidgetItem(""))  # 清空表格文字
                    combo.blockSignals(False)
                    selected.pop(f)

    # --- 联动字段刷新，自动带入唯一值
    for row, param_name, combo in target_rows:
        current_val = combo.currentText().strip()
        all_options = getattr(combo, "full_options", [])

        if param_name == "材料类型":
            valid_options = all_options  # 不受限制
        elif param_name == "材料牌号":
            filter_basis = {'材料类型': selected.get('材料类型', '')}
            valid_options = get_filtered_material_options(filter_basis).get(param_name, [])
        else:
            filter_basis = {
                '材料类型': selected.get('材料类型', ''),
                '材料牌号': selected.get('材料牌号', '')
            }
            valid_options = get_filtered_material_options(filter_basis).get(param_name, [])

        combo.blockSignals(True)
        combo.clear()
        combo.addItem("")
        combo.addItems(valid_options)

        # ✅ 自动填入逻辑（唯一时自动赋值并写入）
        if current_val in valid_options:
            combo.setCurrentText(current_val)
        elif len(valid_options) == 1:
            unique_val = valid_options[0]
            combo.setCurrentText(unique_val)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

MATERIAL_FIELDS = ("材料类型", "材料牌号", "材料标准", "供货状态")

def _find_row_by_param(table, param_col, name: str) -> int:
    for r in range(table.rowCount()):
        it = table.item(r, param_col)
        if it and it.text().strip() == name:
            return r
    return -1

def _ensure_editable_item(table, row, col):
    it = table.item(row, col)
    if it is None:
        it = QTableWidgetItem("")
        table.setItem(row, col, it)
    it.setTextAlignment(Qt.AlignCenter)
    it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
    return it


class InstantCommitComboDelegate:
    pass


def _set_row_delegate(table, row, options, keep_current=False, current_text="", on_change=None):
    # 去空去重省略...
    if keep_current and current_text and current_text not in options:
        options = [current_text] + options

    if on_change is not None:
        table.setItemDelegateForRow(row, InstantCommitComboDelegate(options, table, on_change=on_change))
    else:
        table.setItemDelegateForRow(row, ComboDelegate(options, table))




def install_material_delegate_linkage(table, param_col, value_col, viewer_instance=None):
    """
    渲染完成后调用：
      - 只处理 【材料类型/牌号/标准/供货状态】 和 【垫板材料类型/牌号/标准/供货状态】
      - 给这 8 行安装 MaterialInstantDelegate
      - A 组触发锻件级别显隐，B 组不触发
      - ✅ 新增：进入单元格前动态刷新，但仅限这 8 行
    """
    from PyQt5.QtWidgets import QAbstractItemView, QTableWidgetItem
    from PyQt5.QtCore import Qt

    table.setEditTriggers(QAbstractItemView.SelectedClicked)

    # ---------- 白名单参数名 ----------
    NAMES_ALL = [
        "材料类型","材料牌号","材料标准","供货状态",
        "垫板材料类型","垫板材料牌号","垫板材料标准","垫板材料供货状态"
    ]
    NAMES_SET = set(NAMES_ALL)  # 用于快速判断

    # ---------- 工具函数 ----------
    def _row(name: str) -> int:
        """查找指定参数名对应的行号"""
        r = _find_row_by_param(table, param_col, name)
        return r if (r is not None and r >= 0) else -1

    def _ensure_editable(r: int):
        if r < 0:
            return
        if table.cellWidget(r, value_col):
            table.setCellWidget(r, value_col, None)
        _ensure_editable_item(table, r, value_col)

    def _get(r: int):
        it = table.item(r, value_col)
        return (it.text().strip() if it else "")

    def _set(r: int, txt: str):
        if r < 0:
            return
        it = table.item(r, value_col)
        if it is None:
            it = QTableWidgetItem()
            it.setTextAlignment(Qt.AlignCenter)
            table.setItem(r, value_col, it)
        it.setText(txt or "")

    def _install_row_delegate(field_name, row_idx, options, on_pick):
        """为指定行安装下拉 delegate"""
        if row_idx < 0:
            return
        if field_name not in NAMES_SET:  # ✅ 白名单过滤，非 8 行跳过
            return
        seen, opts = set(), []
        for o in list(options or []):
            s = (o or "").strip()
            if s and s not in seen:
                seen.add(s)
                opts.append(s)
        table.setItemDelegateForRow(row_idx, MaterialInstantDelegate(opts, table, field_name, on_pick))

    # ---------- 公共组装 ----------
    def _install_group(name_type, name_brand, name_std, name_status, forge_flag: bool):
        r_type   = _row(name_type)
        r_brand  = _row(name_brand)
        r_std    = _row(name_std)
        r_status = _row(name_status)
        rows = [r for r in (r_type, r_brand, r_std, r_status) if r >= 0]
        if not rows:
            return set()

        for r in rows:
            _ensure_editable(r)

        cur_type, cur_brand, cur_std = _get(r_type), _get(r_brand), _get(r_std)

        opts_type  = (get_filtered_material_options({}) or {}).get("材料类型", []) or []
        opts_brand = (get_filtered_material_options({"材料类型": cur_type} if cur_type else {}) or {}).get("材料牌号", []) or []
        basis_std  = {k: v for k, v in {"材料类型": cur_type, "材料牌号": cur_brand}.items() if v}
        opts_std   = (get_filtered_material_options(basis_std) or {}).get("材料标准", []) or []
        basis_stat = {k: v for k, v in {"材料类型": cur_type, "材料牌号": cur_brand, "材料标准": cur_std}.items() if v}
        opts_stat  = (get_filtered_material_options(basis_stat) or {}).get("供货状态", []) or []

        def on_pick(field_name: str, new_text: str, row: int, col: int):
            if field_name not in NAMES_SET:  # ✅ 白名单过滤
                return

            cur_t = _get(r_type)
            cur_b = _get(r_brand)
            if field_name == name_type:
                for rr in (r_brand, r_std, r_status):
                    _set(rr, "")
                b = get_filtered_material_options({"材料类型": new_text}) or {}
                _install_row_delegate(name_brand,  r_brand,  b.get("材料牌号", []), on_pick)
                _install_row_delegate(name_std,    r_std,    [], on_pick)
                _install_row_delegate(name_status, r_status, [], on_pick)
            elif field_name == name_brand:
                f = get_filtered_material_options({"材料类型": cur_t, "材料牌号": new_text}) or {}
                std_opts  = f.get("材料标准", []) or []
                stat_opts = f.get("供货状态", []) or []
                _install_row_delegate(name_std,    r_std,    std_opts,  on_pick)
                _install_row_delegate(name_status, r_status, stat_opts, on_pick)
                if (not _get(r_std))    and len(std_opts)  == 1: _set(r_std, std_opts[0])
                if (not _get(r_status)) and len(stat_opts) == 1: _set(r_status, stat_opts[0])
            elif field_name == name_std:
                f = get_filtered_material_options({"材料类型": cur_t, "材料牌号": cur_b, "材料标准": new_text}) or {}
                stat_opts = f.get("供货状态", []) or []
                _install_row_delegate(name_status, r_status, stat_opts, on_pick)
                if (not _get(r_status)) and len(stat_opts) == 1:
                    _set(r_status, stat_opts[0])

            if forge_flag and field_name == name_type:
                _apply_forging_visibility(table, param_col, value_col, viewer_instance, new_text, write_db=True)

            table.viewport().update()

        # 初次安装
        _install_row_delegate(name_type,   r_type,   opts_type,  on_pick)
        _install_row_delegate(name_brand,  r_brand,  opts_brand, on_pick)
        _install_row_delegate(name_std,    r_std,    opts_std,   on_pick)
        _install_row_delegate(name_status, r_status, opts_stat,  on_pick)

        # 锻件级别显隐
        if forge_flag:
            _apply_forging_visibility(table, param_col, value_col, viewer_instance, cur_type, write_db=False)

        return set(rows)

    # ---------- 执行两组 ----------
    rows_a = _install_group("材料类型","材料牌号","材料标准","供货状态", forge_flag=True)
    rows_b = _install_group("垫板材料类型","垫板材料牌号","垫板材料标准","垫板材料供货状态", forge_flag=False)

    # ✅ 只对这 8 行绑定动态刷新
    target_rows = rows_a.union(rows_b)
    if not getattr(table, "_material_dynamic_hook_installed", False):
        def _on_cell_pressed(r, c):
            if c != value_col or r not in target_rows:  # ✅ 限定只作用于 8 行
                return
            pname_item = table.item(r, param_col)
            pname = pname_item.text().strip() if pname_item else ""
            if pname not in NAMES_SET:
                return
            # 简单策略：重新执行安装逻辑
            install_material_delegate_linkage(table, param_col, value_col, viewer_instance)
        table.cellPressed.connect(_on_cell_pressed)
        table._material_dynamic_hook_installed = True


def install_covering_delegate_linkage(table: QTableWidget,
                                      param_col: int,
                                      value_col: int,
                                      component_info: dict,
                                      viewer_instance):
    """
    给 ‘是否添加覆层 / 管程侧是否添加覆层 / 壳程侧是否添加覆层’ 安装行委托，并用 itemChanged 驱动
    toggle_covering_fields() 与图片刷新（兼容代理，不依赖 QComboBox 控件）。
    """
    if getattr(table, "_covering_delegates_installed", False):
        return
    def _find_row(name: str) -> int:
        for r in range(table.rowCount()):
            it = table.item(r, param_col)
            if it and it.text().strip() == name:
                return r
        return -1

    r_global = _find_row("是否添加覆层")
    r_g = _find_row("管程侧是否添加覆层")
    r_k = _find_row("壳程侧是否添加覆层")

    # 1) 给三行装下拉代理（仍然使用你现有的 ComboDelegate；不新增代理类）
    for rr in [r_global, r_g, r_k]:
        if rr >= 0:
            # 确保 value 列有可编辑 item（代理才能工作）
            it = table.item(rr, value_col)
            if it is None:
                it = QTableWidgetItem("")
                it.setTextAlignment(Qt.AlignCenter)
                table.setItem(rr, value_col, it)
            # 行代理：是/否
            table.setItemDelegateForRow(rr, ComboDelegate(["是", "否"], table))

    # 2) 统一的 itemChanged 处理（避免重复绑定）
    def _on_item_changed(item: QTableWidgetItem):
        if item.column() != value_col:
            return
        r = item.row()
        name_it = table.item(r, param_col)
        if not name_it:
            return
        pname = name_it.text().strip()
        val   = item.text().strip()

        # 显隐逻辑（直接调用你原有的方法）
        if pname in ("是否添加覆层", "管程侧是否添加覆层", "壳程侧是否添加覆层"):
            # 用一个“假的 combo”接口传给 toggle_covering_fields（它只用到了 currentText）
            class _Fake:
                def __init__(self, t): self._t=t
                def currentText(self): return self._t
            toggle_covering_fields(table, _Fake(val), pname)

            # 固定管板：双侧任意变化 → 刷新图片
            if component_info and viewer_instance and (r_g >= 0 and r_k >= 0):
                handler = make_on_fixed_tube_covering_changed_v2(
                    component_info, viewer_instance, table, param_col, value_col
                )
                handler()

            # 全局单开关：刷新图片
            if component_info and viewer_instance and pname == "是否添加覆层":
                h = make_on_covering_changed(component_info, viewer_instance, r, table=table)
                h2 = make_on_flange_face_changed(component_info, viewer_instance, r)
                h3 = make_on_head_type_changed(component_info, viewer_instance, r)
                h4 = make_on_fangchongban_face_changed(component_info, viewer_instance, r)
                h5 = make_on_fenchenggeban_changed(component_info, viewer_instance, r)

                h(val)
                h2(val)
                h3(val)
                h4(val)
                h5(val)
    # 断开旧连接，防重复触发
    try:
        table.itemChanged.disconnect(_on_item_changed)
    except Exception:
        pass
    table.itemChanged.connect(_on_item_changed)

    # 3) 初始化：根据当前值做一次显隐与图片刷新
    def _init_apply(row_idx: int, pname: str):
        if row_idx < 0:
            return
        vitem = table.item(row_idx, value_col)
        cur = vitem.text().strip() if vitem else ""
        class _Fake:
            def __init__(self, t): self._t=t
            def currentText(self): return self._t
        toggle_covering_fields(table, _Fake(cur), pname)

    _init_apply(r_global, "是否添加覆层")
    _init_apply(r_g,      "管程侧是否添加覆层")
    _init_apply(r_k,      "壳程侧是否添加覆层")

    # 固定管板：初始化图片
    if component_info and viewer_instance and (r_g >= 0 and r_k >= 0):
        handler = make_on_fixed_tube_covering_changed_v2(component_info, viewer_instance, table, param_col, value_col)
        handler()









def _apply_forging_visibility(table, param_col, value_col, viewer_instance, material_type_text, write_db=True):
    """材料类型≠钢锻件 → 隐藏‘锻件级别’并清空（可选写库）"""
    show = (material_type_text == "钢锻件")
    for rr in range(table.rowCount()):
        pit = table.item(rr, param_col)
        if pit and pit.text().strip() == "锻件级别":
            table.setRowHidden(rr, not show)
            if not show:
                try:
                    table.blockSignals(True)
                    iv = table.item(rr, value_col)
                    if iv: iv.setText("")
                finally:
                    table.blockSignals(False)
                if write_db:
                    try:
                        product_id = getattr(viewer_instance, "product_id", "")
                        element_id = getattr(viewer_instance, "clicked_element_data", {}).get("元件ID", "")
                        update_element_para_data(product_id, element_id, "锻件级别", "")
                    except Exception as e:
                        print(f"[清空锻件级别失败] {e}")
            break


def _norm(s: str) -> str:
    return (s or "").strip()

def _clean_options(options):
    # 去 None/空串，去重保序
    seen, out = set(), []
    for o in options or []:
        t = _norm(o)
        if not t:
            continue
        if t not in seen:
            seen.add(t); out.append(o)   # 保留原字符串，但用于比较走 _norm
    return out

def _in_options(val: str, options) -> bool:
    v = _norm(val)
    return any(_norm(x) == v for x in (options or []))




def on_material_delegate_changed(table, item, param_col, value_col, viewer_instance=None):
    if item.column() != value_col:
        return

    rows_map = table.property("material_rows") or {}
    if not rows_map:
        return

    r_type   = rows_map.get("材料类型",  -1)
    r_brand  = rows_map.get("材料牌号",  -1)
    r_std    = rows_map.get("材料标准",  -1)
    r_status = rows_map.get("供货状态", -1)
    if item.row() not in {r_type, r_brand, r_std, r_status}:
        return

    init_mode = bool(table.property("material_init_mode"))
    getv = lambda rr: (table.item(rr, value_col).text().strip() if rr >= 0 else "")
    cur_type, cur_brand, cur_std, cur_status = getv(r_type), getv(r_brand), getv(r_std), getv(r_status)

    def _reinstall_and_fix(row, options, current_text):
        if row < 0:
            return
        # 重新装代理（非编辑态也能立即生效）
        _set_row_delegate(table, row, options, keep_current=init_mode, current_text=current_text)

        cur = (current_text or "").strip()
        opts = [x for x in (options or []) if str(x).strip()]
        new_val, need_fix = cur, False

        if not init_mode:
            if cur and cur not in opts:
                new_val = (opts[0] if len(opts) == 1 else "")
                need_fix = True
            elif not cur and len(opts) == 1:
                new_val = opts[0]
                need_fix = True
        else:
            if not cur and len(opts) == 1:
                new_val = opts[0]
                need_fix = True

        if need_fix:
            table.blockSignals(True)
            try:
                table.item(row, value_col).setText(new_val)
            finally:
                table.blockSignals(False)

    # 1) 类型
    opts_type = get_filtered_material_options({}).get("材料类型", [])
    _reinstall_and_fix(r_type, opts_type, cur_type)

    # 2) 牌号（受类型）
    cur_type = getv(r_type)
    basis_brand = {"材料类型": cur_type} if cur_type else {}
    opts_brand  = get_filtered_material_options(basis_brand).get("材料牌号", [])
    _reinstall_and_fix(r_brand, opts_brand, cur_brand)

    # 3) 标准（受类型+牌号）
    cur_brand = getv(r_brand)
    basis_std = {"材料类型": cur_type, "材料牌号": cur_brand}
    basis_std = {k: v for k, v in basis_std.items() if v}
    opts_std  = get_filtered_material_options(basis_std).get("材料标准", [])
    _reinstall_and_fix(r_std, opts_std, cur_std)

    # 4) 供货状态（受类型+牌号+标准）
    cur_std   = getv(r_std)
    basis_stat = {"材料类型": cur_type, "材料牌号": cur_brand, "材料标准": cur_std}
    basis_stat = {k: v for k, v in basis_stat.items() if v}
    opts_stat  = get_filtered_material_options(basis_stat).get("供货状态", [])
    _reinstall_and_fix(r_status, opts_stat, cur_status)

    # 材料类型变更时的“锻件级别”显隐/清空
    if item.row() == r_type:
        _apply_forging_visibility(table, param_col, value_col, viewer_instance, getv(r_type), write_db=(not init_mode))





def update_combo_options(combo: QComboBox, all_options, valid_options, current_val: str):
    combo.blockSignals(True)
    combo.clear()
    combo.addItem("")

    if valid_options:
        combo.addItems(valid_options)
    else:
        combo.addItem("（无匹配项）")
        combo.model().item(combo.count() - 1).setEnabled(False)

    valid_set = valid_options if valid_options else all_options
    if current_val and current_val in valid_set:
        combo.setCurrentText(current_val)
    else:
        combo.setCurrentIndex(0)

    combo.blockSignals(False)

    # ✅ 不再 emit 信号！只刷新显示
    combo.repaint()
    combo.update()

def bind_define_table_click(self, table_define, table_param, define_data, category_label):
    """
    绑定左侧定义表格点击事件，每次绑定前先断开旧连接，防止多次触发。
    """
    try:
        table_define.cellClicked.disconnect()
        print("[解绑成功] 原有 cellClicked 信号已断开")
    except Exception as e:
        print("[解绑跳过] 无旧信号或断开失败", e)

    def handler(row, col):
        self.on_define_table_clicked(row, define_data, table_param, category_label)

    table_define.cellClicked.connect(handler)
    print("[绑定完成] 已绑定新的 cellClicked 事件")


def generate_unique_guankou_label(self) -> str:
    """
    基于当前 tab 上的已有标题自动取下一个序号。
    无需全局计数器，切换模板后自然从 2 开始。
    """
    tw = self.guankou_tabWidget
    used = set()
    max_idx = 1

    for i in range(tw.count()):
        text = tw.tabText(i)
        used.add(text)
        m = re.match(r"^管口材料分类(\d+)$", text)
        if m:
            try:
                max_idx = max(max_idx, int(m.group(1)))
            except ValueError:
                pass

    # 末尾有 '+' 的话，不影响取号
    next_idx = max_idx + 1
    while True:
        label = f"管口材料分类{next_idx}"
        if label not in used:
            # 你如果维护了 used_labels，可顺手登记一下（可选）
            if hasattr(self, "guankou_used_labels"):
                self.guankou_used_labels.add(label)
            return label
        next_idx += 1


def refresh_guankou_tabs_from_db(viewer_instance):
    """
    读取数据库 → 统一刷新每个tab：
      显示：若该tab在库里有已保存集合 → 按库里为准（保序显示）；
           否则显示为空（或你愿意可显示=当前∩未分配）
      候选：未分配 ∪ 本tab已保存
    同时写 table.property('gk_code_candidates') 给委托读取，不更换委托。
    """
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5.QtCore import Qt

    product_id = getattr(viewer_instance, "product_id", None)
    if not product_id:
        return

    # ① 未分配集合
    try:
        unassigned = set(query_unassigned_codes(product_id) or [])
    except Exception as e:
        print(f"[警告] 查询未分配失败：{e}")
        unassigned = set()

    # ② tab → 已保存集合（你上一条我已给了实现）
    try:
        tab_to_saved = load_tab_assigned_codes(product_id) or {}
        tab_to_saved = {str(k).strip(): set(v or []) for k, v in tab_to_saved.items()}
    except Exception as e:
        print(f"[警告] 读取tab分配映射失败：{e}")
        tab_to_saved = {}

    def _find_row(table, label: str) -> int:
        for r in range(table.rowCount()):
            it = table.item(r, 0)
            if it and it.text().strip() == label:
                return r
        return -1

    def _set_candidates(table, cands):
        table.setProperty("gk_code_candidates", tuple(sorted(set(cands))))
        table.setProperty("gk_code_candidates_ready", True)

    tw = viewer_instance.guankou_tabWidget
    for i in range(tw.count()):
        tab_name = tw.tabText(i).strip()
        if tab_name in {"+", "＋"}:
            continue

        # 取本tab的表
        table = _get_tab_table(viewer_instance, i)
        if table is None:
            print(f"[提示] 第{i}页({tab_name}) 未绑定 param_table")
            continue

        row_idx = _find_row(table, "管口号")
        if row_idx < 0:
            continue

        # 本tab在库里的已保存集合
        saved = tab_to_saved.get(tab_name, set())

        # 显示：以库里为准（换模板后通常为空）
        display_text = "、".join([x for x in saved])

        # 候选：未分配 ∪ 本tab已保存
        candidates = unassigned | saved

        # 写入显示与候选（不触发信号）
        table.blockSignals(True)
        try:
            item_val = table.item(row_idx, 1)
            if item_val:
                item_val.setText(display_text)
            else:
                it = QTableWidgetItem(display_text)
                it.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_idx, 1, it)
        finally:
            table.blockSignals(False)

        _set_candidates(table, candidates)
        table.viewport().update()


def _show_full_diff_dialog(parent, diffs, template_name):
    dlg = QDialog(parent)
    dlg.setWindowTitle(f"与模板 {template_name} 的差异明细")
    layout = QVBoxLayout(dlg)
    table = QTableWidget(dlg)
    table.setColumnCount(4)
    table.setHorizontalHeaderLabels(["元件名称","字段","当前值","模板值"])
    table.setRowCount(len(diffs))
    for i, d in enumerate(diffs):
        table.setItem(i, 0, QTableWidgetItem(d["name"]))
        table.setItem(i, 1, QTableWidgetItem(d["field"]))
        table.setItem(i, 2, QTableWidgetItem(str(d["old"])))
        table.setItem(i, 3, QTableWidgetItem(str(d["new"])))
    table.resizeColumnsToContents()
    layout.addWidget(table)

    btn = QPushButton("关闭", dlg)
    btn.clicked.connect(dlg.accept)
    layout.addWidget(btn)
    dlg.resize(860, 520)
    dlg.exec_()


def ask_before_switch_template_against_current(parent, product_id: str,
                                               base_template_name: str,
                                               target_template_name: str) -> bool:
    """
    切换之前提示：比较 “产品当前数据” vs “当前模板(base_template_name) 的模板基准”
    显示差异后问是否继续切换到 target_template_name
    """
    # 读库
    prod_map = fetch_product_element_materials(product_id)
    tpl_map  = fetch_template_element_materials(base_template_name)

    diffs = diff_product_vs_template(prod_map, tpl_map)

    if not diffs:
        # 没差异，直接允许切换
        return True

    preview = diffs[:8]
    lines = [f"• {d['name']}：{d['field']}：当前“{d['old']}” → 模板“{d['new']}”" for d in preview]
    more  = "" if len(diffs) <= 8 else f"<br>…… 还有 {len(diffs)-8} 处差异"

    msg = QMessageBox(parent)
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("模板切换差异提示")
    msg.setTextFormat(Qt.RichText)
    msg.setText(
        f"将切换到模板 <b>{target_template_name}</b>。<br>"
        f"在切换前，基于“当前模板 <b>{base_template_name or '（空）'}</b>”的模板基准，"
        f"检测到与当前产品数据存在如下差异：<br><br>"
        + "<br>".join(lines) + more +
        "<br><br><i>此提示仅用于告知差异，不会修改你的现有数据。</i>"
    )
    btn_continue = msg.addButton("继续切换", QMessageBox.AcceptRole)
    btn_detail   = msg.addButton("查看全部", QMessageBox.ActionRole)
    msg.addButton("取消", QMessageBox.RejectRole)
    msg.exec_()

    if msg.clickedButton() == btn_detail:
        _show_full_diff_dialog(parent, diffs, base_template_name)  # 这里展示“和当前模板”的全部差异
        # 再问一次
        msg2 = QMessageBox(parent)
        msg2.setIcon(QMessageBox.Question)
        msg2.setWindowTitle("确认切换")
        msg2.setText(f"是否继续切换到模板 “{target_template_name}”？")
        ok2 = msg2.addButton("继续切换", QMessageBox.AcceptRole)
        msg2.addButton("取消", QMessageBox.RejectRole)
        msg2.exec_()
        return msg2.clickedButton() == ok2

    return msg.clickedButton() == btn_continue





def load_data_by_template(viewer_instance, template_name):

    while viewer_instance.guankou_tabWidget.count() > 1:
        viewer_instance.guankou_tabWidget.removeTab(1)

    # 删除动态添加的 tab
    for tab in viewer_instance.dynamic_guankou_tabs:
        index = viewer_instance.guankou_tabWidget.indexOf(tab)
        if index != -1:
            viewer_instance.guankou_tabWidget.removeTab(index)
    viewer_instance.dynamic_guankou_tabs.clear()

    viewer_instance.dynamic_guankou_param_tabs.clear()
    # 默认tab重新登记
    viewer_instance.dynamic_guankou_param_tabs["管口材料分类1"] = viewer_instance.tableWidget_guankou

    if hasattr(viewer_instance, "plus_mgr") and viewer_instance.plus_mgr:
        viewer_instance.plus_mgr.refresh_after_model_change()

    if not template_name:
        template_name = "None"

    # print(f"模板名称{template_name}")

    product_type = viewer_instance.product_type
    product_form = viewer_instance.product_form
    product_id = viewer_instance.product_id
    # print(f"产品ID{product_id}")

    if product_type and product_form:
        element_original_info = load_elementoriginal_data(template_name, product_type, product_form)
        viewer_instance.element_data = element_original_info  # 存储到实例变量

        # 管口类别表的读取插入
        guankou_info = query_template_codes(product_id)

        if not guankou_info:
            guankou_info = query_guankou_default(viewer_instance.product_type, viewer_instance.product_form)

        insert_guankou_info(product_id, guankou_info)

        if element_original_info:
            element_original_info = move_guankou_to_first(element_original_info)
            # print(f"选择模板后的元件列表{element_original_info}")
            viewer_instance.element_original_info_template = element_original_info
            # print(f"传入模板的元件列表{viewer_instance.element_original_info_template}")
            insert_or_update_element_data(element_original_info, product_id, template_name)

            viewer_instance.image_paths = [item.get('零件示意图', '') for item in element_original_info]
            viewer_instance.render_data_to_table(element_original_info)
            if len(element_original_info) > 0:
                first_part_image_path = element_original_info[0].get('零件示意图', '')
                viewer_instance.display_image(first_part_image_path)
                viewer_instance.first_element_id = element_original_info[0].get('元件ID', None)
            else:
                print(f"警告：模板 {template_name} 没有元素")

            # 获取更新模板后的对应的模板ID
            first_template_id = element_original_info[0].get('模板ID', None)
            print(f"[调试] 模板ID: {first_template_id}")

            # 获取当前模板ID对应的元件附加参数信息
            element_para_info = query_template_element_para_data(first_template_id)
            # print(f"更新后的零件列表信息{element_para_info}")
            # 更新产品活动库中的元件附加参数表
            insert_or_update_element_para_data(product_id, element_para_info)
            sync_design_params_to_element_params(product_id)

            # 获取当前模板ID对应的管口参数信息
            guankou_para_info = query_template_guankou_para_data(first_template_id)

            # ✅ 新增：批量处理所有有附加参数合并表的元件
            batch_insert_element_merged_para_data(product_id, first_template_id, template_name)

            # 将当前模板ID对应的管口参数信息写入到产品设计活动库中
            insert_or_update_guankou_para_data(product_id, guankou_para_info, template_name)
            # sync_corrosion_to_guankou_param(product_id)
            if viewer_instance.guankou_tabWidget.count() > 0:
                current_index = viewer_instance.guankou_tabWidget.currentIndex()  # 当前选中 tab
                category_label = viewer_instance.guankou_tabWidget.tabText(current_index)
            else:
                category_label = "管口材料分类1"  # fallback

                # 打印当前分类标签（category_label）
            print(f"[调试] 当前的分类标签是: {category_label}")

            guankou_codes = query_guankou_codes(product_id, category_label)
            # 打印查询到的管口号
            print(f"[调试] 查询到的管口号: {guankou_codes}")
            sync_corrosion_to_guankou_param(product_id, guankou_codes, category_label)

            refresh_guankou_tabs_from_db(viewer_instance)
            guankou_define_info = load_guankou_define_data(product_id)

            viewer_instance.guankou_define_info = guankou_define_info
            # 批量加上模板名称
            for item in viewer_instance.guankou_define_info:
                item['模板ID'] = first_template_id

            print("更新模板后管口定义信息：", viewer_instance.guankou_define_info)

            if guankou_define_info:

                render_guankou_param_to_ui(viewer_instance, guankou_define_info)

                # # 管口零件表格中的下拉框
                # dropdown_data = load_material_dropdown_values()
                # column_index_map = {'材料类型': 1, '材料牌号': 2, '材料标准': 3, '供货状态': 4}
                # column_data_map = {column_index_map[k]: v for k, v in dropdown_data.items()}
                # apply_combobox_to_table(viewer_instance.tableWidget_guankou_define, column_data_map, viewer_instance, category_label="管口材料分类1")
                # set_table_tooltips(viewer_instance.tableWidget_guankou_define)

                # #更新产品活动库中的管口零件材料表
                # insert_or_update_guankou_material_data(guankou_define_info, product_id, template_name)
                # # print(f"管口零件更新信息{guankou_define_info}")
                #
                # first_guankou_element = guankou_define_info[0]
                # viewer_instance.guankou_define_info = guankou_define_info
                # # print(f"第一条管口零件信息{first_guankou_element}")
                # first_guankou_element_id = first_guankou_element.get("管口零件ID", None)
                # # print(f"第一条管口零件对应的管口零件ID{first_guankou_element_id}")
                # if first_guankou_element_id:
                #     guankou_material_details = load_guankou_material_detail_template(first_guankou_element_id, first_template_id)
                #     # print(f"第一个管口零件对应的参数信息{guankou_material_details}")
                #     if guankou_material_details:
                #         render_guankou_info_table(viewer_instance, guankou_material_details)
                #         param_options = load_material_dropdown_values()
                #         apply_paramname_dependent_combobox(
                #             viewer_instance.tableWidget_para_define,
                #             param_col=0,
                #             value_col=1,
                #             param_options=param_options
                #         )
                #         apply_paramname_dependent_combobox(
                #             viewer_instance.tableWidget_guankou_param,
                #             param_col=0,
                #             value_col=1,
                #             param_options=param_options
                #         )
                #         apply_gk_paramname_combobox(
                #             viewer_instance.tableWidget_guankou_param,
                #             param_col=0,
                #             value_col=1
                #         )
                #
                #
                #         set_table_tooltips(viewer_instance.tableWidget_para_define)
                #     else:
                #         print("没有查到第一个管口零件材料的详细数据")
                # else:
                #     print("第一个管口零件没有ID")
            else:
                print("没有查到管口定义数据")

        else:
            viewer_instance.show_error_message("数据加载错误", f"模板 {template_name} 未找到元件数据")
    else:
        viewer_instance.show_error_message("输入错误", "产品类型或形式未找到")

    # # 存为模板
    # # update_template_input_editable_state(viewer_instance)
    # bind_define_table_click(
    #     viewer_instance,
    #     viewer_instance.tableWidget_guankou_define,
    #     viewer_instance.tableWidget_guankou_param,
    #     guankou_define_info,  # 模板切换后的新数据
    #     category_label="管口材料分类1"
    # )


    # def force_select_guankou_and_trigger():
    #     print("✅ 自动选中管口并触发刷新")
    #
    #     # 1. 先从左侧表格中查找“管口”行号
    #     table = viewer_instance.tableWidget_parts
    #     for r in range(table.rowCount()):
    #         item = table.item(r, 1)  # 第1列为“零件名称”
    #         if item and item.text().strip() == "管口":
    #             table.setCurrentCell(r, 0)
    #             viewer_instance.handle_table_click_guankou(r, 0)  # ✅ 切换到“管口”
    #             handle_table_click(viewer_instance, r, 0)  # ✅ 加载管口定义数据
    #             break
    #
    #     # 2. 再模拟点击右侧“管口定义”表第一行
    #     QTimer.singleShot(10, lambda: viewer_instance.on_define_table_clicked(
    #         0,
    #         viewer_instance.guankou_define_info,
    #         viewer_instance.tableWidget_guankou_param,
    #         "管口材料分类1"
    #     ))
    #
    # QTimer.singleShot(10, force_select_guankou_and_trigger)


def render_common_material_editor(viewer_instance):
    """渲染多选统一编辑面板（4项下拉框）"""
    parts_table = viewer_instance.tableWidget_parts
    param_table = viewer_instance.tableWidget_para_define

    selected_indexes = parts_table.selectedIndexes()
    selected_rows = list(sorted(set(index.row() for index in selected_indexes)))

    if not selected_rows:
        return

    # 记录选中元件数据（便于确认时保存）
    viewer_instance.selected_elements_data = [
        viewer_instance.element_data[r] for r in selected_rows
    ]

    # 准备表格结构
    param_table.clear()
    param_table.setColumnCount(3)
    param_table.setRowCount(4)
    param_table.setHorizontalHeaderLabels(["参数名称", "参数值", "参数单位"])

    fields = ["材料类型", "材料牌号", "材料标准", "供货状态"]
    param_col = 0  # 参数名列
    value_col = 1
    part_col = 2

    # 读取下拉选项
    dropdown_data = load_material_dropdown_values()

    for i, field in enumerate(fields):
        # 参数名列
        name_item = QTableWidgetItem(field)
        name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        name_item.setTextAlignment(Qt.AlignCenter)
        param_table.setItem(i, 0, name_item)

        # 下拉框控件
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("")
        options = dropdown_data.get(field, [])
        combo.addItems(options)
        combo.full_options = options.copy()

        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo.setStyleSheet("""
            QComboBox {
                border: none;
                background-color: transparent;
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding-left: 2px;
            }
        """)

        combo.currentTextChanged.connect(partial(
            on_material_combobox_changed, param_table, i, param_col, value_col, part_col
        ))

        # 添加下拉框到表格中
        param_table.setCellWidget(i, 1, combo)

        # 单位列空置
        unit_item = QTableWidgetItem("")
        unit_item.setFlags(Qt.ItemIsEnabled)
        unit_item.setTextAlignment(Qt.AlignCenter)
        param_table.setItem(i, 2, unit_item)

    param_table.setEditTriggers(QTableWidget.NoEditTriggers)


def handle_table_click(viewer_instance, row, col):
    """处理点击零件列表的逻辑"""
    # ✅ 统计当前选中的所有“行”索引
    selected_indexes = viewer_instance.tableWidget_parts.selectedIndexes()
    selected_rows = list(set(index.row() for index in selected_indexes))  # 去重得到选中行号列表

    # ✅ 收集所有选中元件的零件名称
    selected_names = [viewer_instance.element_data[r].get("零件名称", "") for r in selected_rows]

    # ✅ 判断是否包含“管口”或“垫片”
    if any("管口" in name or "垫片" in name for name in selected_names):
        print("[跳过多选] 包含‘管口’或‘垫片’，强制回退为单选")
        selected_rows = [row]  # 强制只保留当前点击行
        viewer_instance.tableWidget_parts.clearSelection()
        viewer_instance.tableWidget_parts.selectRow(row)

    # ✅ 重新读取点击行数据
    viewer_instance.selected_element_ids = []
    for index in selected_rows:
        element_id = viewer_instance.element_data[index].get("元件ID")
        if element_id:
            viewer_instance.selected_element_ids.append(element_id)

    if len(selected_rows) > 1:
        print("[多选模式] 渲染四字段材料信息")
        viewer_instance.label_part_image.clear()
        viewer_instance.stackedWidget.setCurrentIndex(1)
        render_common_material_editor(viewer_instance)
        return

    # 获取当前点击行的数据
    clicked_element_data = viewer_instance.element_data[row]  # 获取已经存储的行数据
    print(f"零件表格点击的行数据: {clicked_element_data}")
    viewer_instance.clicked_element_data = clicked_element_data

    # ✅ 设置当前激活元件ID（用于图片逻辑判断）
    viewer_instance.current_component_id = clicked_element_data.get("元件ID")
    viewer_instance.current_image_path = None  # ✅ 清除上一个图路径

    product_type = viewer_instance.product_type
    product_form = viewer_instance.product_form


    # 获取元件ID和模板ID
    element_id = clicked_element_data.get("元件ID", None)
    template_id = clicked_element_data.get("模板ID", None)
    element_name = clicked_element_data.get("零件名称", "")
    # print(f"元件ID{element_id}")

    # 判断是否为管口
    if element_name == "管口":
        # guankou_define_info = load_guankou_define_data(template_id, "1")
        # print(f"管口{guankou_define_info}")
        updated_guankou_define_info = load_updated_guankou_define_data(viewer_instance.product_id, "管口材料分类1")
        print(f"更新{updated_guankou_define_info}")
        render_guankou_param_to_ui(viewer_instance, updated_guankou_define_info)
        viewer_instance.guankou_define_info = updated_guankou_define_info

        # ✅ 关键：首次点击时也刷新“管口号”的显示值与候选
        tw = getattr(viewer_instance, "guankou_tabWidget", None)
        cur_tab = (tw.tabText(tw.currentIndex()).strip()
                   if tw and tw.currentIndex() >= 0 else "管口材料分类1")

        try:
            viewer_instance.patch_codes_for_current_tab(viewer_instance.tableWidget_guankou, cur_tab)
        except Exception as e:
            print(f"[GUANKOU] 首次补刷失败：{e}")

        # 再用 0ms 兜底刷一次，确保在所有委托安装完成后也生效
        QTimer.singleShot(0, lambda:
        viewer_instance.patch_codes_for_current_tab(viewer_instance.tableWidget_guankou, cur_tab)
                          )

        # if not guankou_define_info:
        #     guankou_define_info = query_guankou_define_data_by_category(viewer_instance.product_id, "管口材料分类1")
        #     render_guankou_param_table(viewer_instance, guankou_define_info)
        # else:
        #     guankou_ID = guankou_define_info[0].get("管口零件ID", None)
        #     # guankou_additional_info = load_guankou_para_data(guankou_ID, "管口材料分类1")
        #     guankou_additional_info = load_guankou_para_data(guankou_ID, viewer_instance.product_id, "管口材料分类1")

        #     if guankou_additional_info:
        #         render_guankou_info_table(viewer_instance, guankou_additional_info)
        #
        #         # ✅ 关键改动：不论初始化还是切换，都插入控件
        #         param_options = load_material_dropdown_values()
        #
        #         apply_paramname_dependent_combobox(
        #             viewer_instance.tableWidget_guankou_param,
        #             param_col=0,
        #             value_col=1,
        #             param_options=param_options,
        #             component_info=viewer_instance.clicked_element_data,
        #             viewer_instance=viewer_instance
        #         )
        #         apply_gk_paramname_combobox(
        #             viewer_instance.tableWidget_guankou_param,
        #             param_col=0,
        #             value_col=1
        #         )
        #         set_table_tooltips(viewer_instance.tableWidget_guankou_param)
        #     else:
        #         guankou_para_table = viewer_instance.tableWidget_guankou_param
        #         guankou_para_table.setRowCount(0)
        #         guankou_para_table.clearContents()
        #
        # # ✅ 不管有没有零件信息，define表也一样正常渲染
        # dropdown_data = load_material_dropdown_values()
        # column_index_map = {'材料类型': 1, '材料牌号': 2, '材料标准': 3, '供货状态': 4}
        # column_data_map = {column_index_map[k]: v for k, v in dropdown_data.items()}
        # apply_combobox_to_table(viewer_instance.tableWidget_guankou_define, column_data_map, viewer_instance,
        #                         category_label="管口材料分类1")
        # set_table_tooltips(viewer_instance.tableWidget_guankou_define)

        return

    if not element_id:
        print("没有找到有效的元件ID，跳过查询！")
        return

    additional_info = load_element_additional_data_by_product(viewer_instance.product_id, element_id)


    render_additional_info_table(viewer_instance, additional_info)
    param_options = load_material_dropdown_values()
    # apply_paramname_dependent_combobox(
    #     viewer_instance.tableWidget_para_define,
    #     param_col=0,
    #     value_col=1,
    #     param_options=param_options,
    #     component_info=viewer_instance.clicked_element_data,
    #     viewer_instance=viewer_instance
    # )
    install_material_delegate_linkage(
        table=viewer_instance.tableWidget_para_define,
        param_col=0,
        value_col=1,
        viewer_instance=viewer_instance,  # 用于“锻件级别”清库时的 product_id / element_id
    )
    # install_covering_delegate_linkage(
    #     table=viewer_instance.tableWidget_para_define,
    #     param_col=0,
    #     value_col=1,
    #     component_info=viewer_instance.clicked_element_data,
    #     viewer_instance=viewer_instance
    # )
    apply_paramname_combobox(
        viewer_instance.tableWidget_para_define,
        param_col=0,
        value_col=1,
        viewer_instance=viewer_instance
    )

    mapping = get_dependency_mapping_from_db()
    apply_linked_param_combobox(viewer_instance.tableWidget_para_define, param_col=0, value_col=1, mapping=mapping)
    set_table_tooltips(viewer_instance.tableWidget_para_define)


def _trigger_gasket_standard_update_on_type_change(table):
    """垫片类型变化时主动触发垫片标准的更新"""
    try:
        from modules.cailiaodingyi.funcs.funcs_pdf_change import get_dependency_mapping_from_db

        # 获取依赖映射
        mapping = get_dependency_mapping_from_db()

        # 字符规范化的简化版本
        def _canon_simple(text):
            return (text or "").strip().replace(" ", "").replace("　", "")

        # 找到垫片标准行
        def _row_of(param):
            for i in range(table.rowCount()):
                it = table.item(i, 0)
                if it and _canon_simple(it.text()) == _canon_simple(param):
                    return i
            return -1

        def _get(row):
            it = table.item(row, 1)
            return (it.text() if it else "").strip()

        def _set(row, val):
            it = table.item(row, 1)
            if it:
                it.setText(val)

        # 获取当前垫片类型
        current_type = _get(_row_of("垫片类型")) or _get(_row_of("垫片型式"))
        if not current_type:
            return

        print(f"[DBG] 垫片标准主动更新: 垫片类型变化为'{current_type}'，触发垫片标准默认值更新")

        # 获取当前垫片类型对应的垫片标准选项
        type_map = mapping.get("垫片类型", {})
        type_deps = type_map.get(current_type, {})
        standard_opts = type_deps.get("垫片标准", [])

        # 获取垫片标准行
        r_standard = _row_of("垫片标准")
        if r_standard >= 0 and standard_opts:
            # 清空当前垫片标准并设置为第一个默认选项
            _set(r_standard, "")  # 先清空
            _set(r_standard, standard_opts[0] if standard_opts else "")  # 设置为第一个选项
            print(f"[DBG] 垫片标准主动更新: 已设置为默认值'{standard_opts[0] if standard_opts else ''}'")

    except Exception as e:
        print(f"[DBG] 垫片标准主动更新失败: {e}")


def display_param_dict_on_right_panel(viewer_instance, param_dict):
    table = viewer_instance.tableWidget_para_define
    table.setRowCount(0)
    for i, (k, v) in enumerate(param_dict.items()):
        table.insertRow(i)
        table.setItem(i, 0, QTableWidgetItem(k))
        table.setItem(i, 1, QTableWidgetItem(str(v)))
        table.setItem(i, 2, QTableWidgetItem(""))  # 单位可补充


def clear_right_panel(viewer_instance):
    table = viewer_instance.tableWidget_para_define
    table.setRowCount(0)
    table.clearContents()



def on_confirm_param_update(viewer_instance):
    # 普通元件的确定按钮
    table = viewer_instance.tableWidget_detail

    # === 新增：成对联动配置 & 小工具 ===
    PAIR_MAP = {"管箱垫片": "管箱侧垫片", "管箱侧垫片": "管箱垫片"}
    SKIP_PARAMS = {"元件名称", "零件名称"}  # 不允许改名

    def _find_element_id_by_name(name: str):
        """在当前内存的 element_data 里按 元件/零件名称 找到 元件ID"""
        name = (name or "").strip()
        for it in getattr(viewer_instance, "element_data", []) or []:
            if (it.get("零件名称") or "").strip() == name or (it.get("元件名称") or "").strip() == name:
                return it.get("元件ID")
        return None

    # 放在 on_confirm_param_update 内，替换你原来的 _sync_pair_if_needed
    def _col_index_by_header(tbl, candidates, default=0):
        # 通过表头名找列号，避免把列号写死
        for i in range(tbl.columnCount()):
            it = tbl.horizontalHeaderItem(i)
            if it and (it.text() or "").strip() in candidates:
                return i
        return default

    def _sync_pair_if_needed(src_part_name: str):
        """
        若当前元件是 管箱垫片/管箱侧垫片：
        - 从当前明细表逐行读取（参数名称 → 参数值）
        - 写入到“对应的另一个元件”
        - 跳过名称类字段（不改对方的名称）
        - 不从数据库读取
        """
        target_name = PAIR_MAP.get((src_part_name or "").strip())
        if not target_name:
            return
        target_eid = _find_element_id_by_name(target_name)
        if not target_eid:
            print(f"[管箱垫片联动] 未找到对应元件：{target_name}")
            return

        # 找到 “参数名称/参数值” 两列
        param_col = _col_index_by_header(table, {"参数名称", "参数名", "名称"}, default=0)
        value_col = _col_index_by_header(table, {"参数值", "值", "当前值"}, default=1)

        wrote = 0
        for r in range(table.rowCount()):
            pitem = table.item(r, param_col)
            vitem = table.item(r, value_col)
            pname = (pitem.text() if pitem else "").strip()
            if not pname or pname in SKIP_PARAMS:
                continue  # ★ 跳过“元件名称/零件名称”，不改名
            pval = (vitem.text() if vitem else "")
            try:
                update_element_para_data(viewer_instance.product_id, target_eid, pname, pval)
                wrote += 1
            except Exception as e:
                print(f"[管箱垫片联动] 写入失败 {target_name}::{pname} = {pval} -> {e}")

        print(f"[管箱垫片联动] {src_part_name} → {target_name} 已同步 {wrote} 项（已排除名称字段）。")

    # 🚩 提交正在编辑的单元格
    if table.state() == QAbstractItemView.EditingState:
        table.closePersistentEditor(table.currentItem())
        table.setFocus()

    # 🚩 保存前检查：是否有滑道角度需要确认
    if hasattr(table, "_angle_needs_confirm") and table._angle_needs_confirm:
        r, c = table._angle_needs_confirm
        item = table.item(r, c)
        txt = item.text().strip() if item else ""
        if txt:
            try:
                val = float(txt)
            except ValueError:
                val = None
            if val is not None and (val < 15 or val > 25):
                box = QMessageBox(table)
                box.setIcon(QMessageBox.Question)
                box.setWindowTitle("提示")
                box.setText("[滑道-滑道与竖直中心线夹角]\n标准推荐值在15°至25°之间，是否继续？")

                btn_yes = box.addButton("是", QMessageBox.YesRole)
                btn_no = box.addButton("否", QMessageBox.NoRole)
                box.setDefaultButton(btn_no)

                box.exec_()

                if box.clickedButton() == btn_no:
                    # 用户拒绝 → 清空输入，数据库保存空
                    item.setText("")

        # 清理标记
        table._angle_needs_confirm = None

    # 🚩 到这里统一进入保存流程（不再中断）
    table._saving_now = True
    save_ok = False
    try:
        image_path = getattr(viewer_instance, "current_image_path", None)
        selected_ids = getattr(viewer_instance, "selected_element_ids", [])

        if len(selected_ids) > 1:
            print(f"[多选] 批量处理元件ID: {selected_ids}")
            for eid in selected_ids:
                update_param_table_data(
                    viewer_instance.tableWidget_detail,
                    viewer_instance.product_id,
                    eid
                )
                part_info = next((item for item in viewer_instance.element_data if item["元件ID"] == eid), {})
                part_name = part_info.get("零件名称", "")
                update_left_table_db_from_param_table(
                    viewer_instance.tableWidget_detail,
                    viewer_instance.product_id,
                    eid,
                    part_name
                )
                # ★ 新增：批量场景也做成对联动
                _sync_pair_if_needed(part_name)

        else:
            clicked_data = viewer_instance.clicked_element_data
            print(f"当前元件信息{clicked_data}")
            element_id = clicked_data.get("元件ID")
            part_name = clicked_data.get("零件名称")
            save_image(element_id, image_path, viewer_instance.product_id)
            update_param_table_data(
                viewer_instance.tableWidget_detail,
                viewer_instance.product_id,
                element_id
            )
            update_left_table_db_from_param_table(
                viewer_instance.tableWidget_detail,
                viewer_instance.product_id,
                element_id,
                part_name
            )

            # ★ 新增：单选场景的成对联动（在刷新左表之前做，这样等会儿刷新能一起反映出来）
            _sync_pair_if_needed(part_name)

        # 刷新左表（放在所有写库动作之后，这样一次刷新拿到两边的最新值）
        updated_element_info = load_element_data_by_product_id(viewer_instance.product_id)
        updated_element_info = move_guankou_to_first(updated_element_info)
        viewer_instance.element_data = updated_element_info
        viewer_instance.render_data_to_table(updated_element_info)

        save_ok = True

        # 联动布管参数表
        sync_component_params_to_buguan(viewer_instance.tableWidget_detail, viewer_instance.product_id)

    finally:
        table._saving_now = False

    # ★★★ 新增：统一在这里给底部提示栏写“保存成功”
    try:
        tip = getattr(viewer_instance, "line_tip", None)
        if tip:
            if save_ok:
                # 成功 — 黑色提示；批量时带数量
                n = len(getattr(viewer_instance, "selected_element_ids", []))
                msg = "保存成功" if n <= 1 else f"保存成功（批量 {n} 项）"
                tip.setStyleSheet("color:black;")
                tip.setText(msg)
                # 5秒后自动清空（如果你不想自动清空，删掉这三行）
                QTimer.singleShot(5000, lambda: tip.setText(""))
            else:
                # 若刷新左表中途失败，可给红色错误提示（可选）
                tip.setStyleSheet("color:red;")
                tip.setText("保存失败：左表刷新未完成")
                QTimer.singleShot(5000, lambda: tip.setText(""))
    except Exception as e:
        print(f"[提示栏写入失败] {e}")

    # 恢复点击绑定（保持你的原逻辑不变）
    try:
        viewer_instance.tableWidget_parts.itemClicked.disconnect()
    except Exception as e:
        print(f"[调试] 点击事件解绑失败: {e}")
    try:
        viewer_instance.tableWidget_parts.itemClicked.connect(
            lambda item: handle_table_click(viewer_instance, item.row(), item.column())
        )
    except Exception as e:
        print(f"[调试] 点击事件绑定失败: {e}")




def show_success_message_auto(parent, message="保存成功！", timeout=2000):
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Information)
    box.setWindowTitle("成功")
    box.setText(message)
    box.setStandardButtons(QMessageBox.NoButton)

    # ✅ 设置提示文字字体大小 & 控制整体宽度
    box.setStyleSheet("""
        QMessageBox {
            min-width: 200px;
            max-width: 300px;
        }
        QMessageBox QLabel {
            font-size: 18px;
            padding: 8px;
        }
    """)

    box.setWindowModality(False)  # 非阻塞
    box.show()
    QTimer.singleShot(timeout, box.accept)


def _get_tab_table(viewer_instance, i: int):
    tw = getattr(viewer_instance, "guankou_tabWidget", None)
    if tw is None or i < 0 or i >= tw.count():
        return None
    page = tw.widget(i)
    t = page.property('param_table') if page else None
    if t is None and i == 0:
        t = getattr(viewer_instance, "tableWidget_guankou", None)  # 首 tab 兜底
    return t


def refresh_all_tabs_after_save(viewer_instance, current_tab_index: int, current_selected_codes: set):
    """
    规则：
      - 显示：优先以“库里已保存集合”为准；若该tab尚未保存，则显示=当前显示∩未分配（并剔除他tab新占用）
      - 候选：所有tab统一为 未分配 ∪ 本tab已保存
    不更换委托，只更新单元格文本与表属性 gk_code_candidates。
    """
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5.QtCore import Qt
    import re

    product_id = getattr(viewer_instance, "product_id", None)
    if not product_id:
        return

    # ① 库里未分配集合
    try:
        unassigned = set(query_unassigned_codes(product_id) or [])
    except Exception as e:
        print(f"[警告] 查询未分配失败：{e}")
        unassigned = set()

    # ② 库里“tab → 已分配集合”映射（需要你实现：返回 dict[str, set[str]]）
    #    要求：键使用【tab页当前标题】保存和读取保持一致。
    try:
        tab_to_saved = load_tab_assigned_codes(product_id) or {}   # e.g. {"管口材料分类1": {"N1","N2"}, ...}
        # 规范成 set
        tab_to_saved = {str(k).strip(): set(v or []) for k, v in tab_to_saved.items()}
    except Exception as e:
        print(f"[警告] 读取tab分配映射失败：{e}")
        tab_to_saved = {}

    def parse_codes(s: str):
        return [x for x in re.split(r"[、，,\s]+", (s or "").strip()) if x]

    def merge_in_display_order(cur_list, keep_set):
        head = [x for x in cur_list if x in keep_set]
        tail = [x for x in keep_set if x not in cur_list]
        return head + tail

    def _set_candidates_property(table, cands):
        table.setProperty("gk_code_candidates", tuple(sorted(set(cands))))
        table.setProperty("gk_code_candidates_ready", True)

    tw = viewer_instance.guankou_tabWidget
    for i in range(tw.count()):
        name = tw.tabText(i).strip()
        if name in {"+", "＋"}:
            continue

        table = _get_tab_table(viewer_instance, i)
        if table is None:
            print(f"[提示] 第{i}页({name}) 未绑定 param_table")
            continue

        # 找“管口号”行
        row_idx = -1
        for r in range(table.rowCount()):
            it0 = table.item(r, 0)
            if it0 and it0.text().strip() == "管口号":
                row_idx = r
                break
        if row_idx < 0:
            continue

        item_val = table.item(row_idx, 1)
        cur_text = item_val.text().strip() if (item_val and item_val.text()) else ""
        cur_list = parse_codes(cur_text)

        # 本tab在库里的已保存集合
        saved_set = set(tab_to_saved.get(name, set()))

        if saved_set:
            # ✅ 已经保存过：显示=库里为准（按原顺序保序）
            keep_list = merge_in_display_order(cur_list, saved_set)
        else:
            # ⬜ 尚未保存：显示=当前显示 ∩ 未分配（并剔除本次新占用）
            #   （当次保存发生在 current_tab_index，已被写入库的其它tab会走上面的分支）
            tmp = [x for x in cur_list if x not in (current_selected_codes or set())]
            keep_list = [x for x in tmp if x in unassigned]

        new_text = "、".join(keep_list)

        # 候选 = 未分配 ∪ 本tab已保存（无论是否当前tab，都一样）
        cand = unassigned | saved_set

        table.blockSignals(True)
        try:
            if item_val:
                item_val.setText(new_text)
            else:
                it = QTableWidgetItem(new_text)
                it.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_idx, 1, it)
        finally:
            table.blockSignals(False)

        _set_candidates_property(table, cand)
        table.viewport().update()



SEP = "、"

def _cell_text(table, r: int, c: int) -> str:
    w = table.cellWidget(r, c)
    if isinstance(w, QComboBox):
        return (w.currentText() or "").strip()
    it = table.item(r, c)
    return (it.text() or "").strip() if isinstance(it, QTableWidgetItem) else ""

def _is_multi_col_row(table, r: int) -> bool:
    """
    更稳妥的多列判定：如果第1个值单元格 (col=1) 没有被横向合并（span==1），
    且总列数>=4，则认为是 3 列值的“多列行”。
    —— 你的两列行是把 (r,1) 跨 3 列合并的；多列行则不会合并。
    """
    try:
        return table.columnCount() >= 4 and table.columnSpan(r, 1) == 1
    except Exception:
        # 某些版本没有 columnSpan 或异常时退回到旧判定
        return table.columnCount() > 2 and any(_cell_text(table, r, c) != "" for c in range(2, table.columnCount()))

def _dedup_keep_order(items):
    seen = set(); out = []
    for x in items or []:
        x = (x or "").strip()
        if x and x not in seen:
            seen.add(x); out.append(x)
    return out

_BRACKETS = [('（','）'), ('(',')'), ('[',']')]

def _strip_units_from_label(label: str) -> str:
    """
    去掉 UI 字段名尾部的单位标注：
    - 壁厚（mm） -> 壁厚
    - 温度(℃) -> 温度
    - 流量 kg/s -> 流量
    - 压力 MPa -> 压力
    """
    s = (label or "").strip()

    # 1) 末尾括号单位： 名称（mm） / 名称(mm) / 名称[mm]
    for L, R in _BRACKETS:
        m = re.match(rf"^(.*?){re.escape(L)}\s*[^ {re.escape(L+R)}]*\s*{re.escape(R)}\s*$", s)
        if m:
            return m.group(1).rstrip(" ：:")

    # 2) 尾部空格+单位（无括号）： 名称 kg/s、名称 MPa、名称 ℃
    m = re.match(r"^(.*?)(?:\s|[：:])+[a-zA-Zμµ%°℃℉/·\-\*\^0-9]+$", s)
    if m and m.group(1).strip():
        return m.group(1).strip()

    return s

def _ui2db_name(label: str, viewer_instance=None) -> str:
    """
    UI → DB 基础名：
    1) 先剥单位
    2) 再查可选的自定义映射 name_map_ui2db（如需特殊保留/改名）
    """
    base = _strip_units_from_label(label)
    name_map = getattr(viewer_instance, "name_map_ui2db", None) or {}
    return name_map.get(base, base)

def save_other_params_for_tab(viewer_instance, table_param, product_id, tab_name):
    """
    把“除管口号外”的参数行写库：
    - 单列行： (product_id, tab_name, label, value)
    - 多列行： (product_id, tab_name, f"{label}{i}", value_i)  i=1..3
    """
    rows_to_save = []

    for r in range(table_param.rowCount()):
        it0 = table_param.item(r, 0)
        if not it0:
            continue
        label_ui = it0.text().strip()
        if not label_ui:
            continue
        if label_ui == "管口号":
            # “管口号”另有 save_guankou_codes_for_tab 处理，这里跳过
            continue

        label_db_base = _ui2db_name(label_ui, viewer_instance)

        if _is_multi_col_row(table_param, r):
            # —— 多列行：展开 label1/label2/label3 —— #
            # 列序：值列通常是 1、2、3；保证最多取 3 个
            value_cols = [1, 2, 3] if table_param.columnCount() >= 4 else [1, 2]
            for i, c in enumerate(value_cols, start=1):
                v = _cell_text(table_param, r, c)
                # 这里如果你想“空值不写库”，可改成：if v != "": 再 append
                rows_to_save.append((product_id, tab_name, f"{label_db_base}{i}", v))
        else:
            # —— 两列行（(r,1) 跨 3 列）或普通单值行 —— #
            v1 = _cell_text(table_param, r, 1)
            rows_to_save.append((product_id, tab_name, label_db_base, v1))

    # 批量更新
    ret = update_guankou_params_bulk(rows_to_save, treat_empty_as_null=True)
    print(f"[调试] Tab={tab_name} 更新参数 {ret['updated']} 行, 未命中 {len(ret['missing'])} 行")


def on_confirm_guankouparam(viewer_instance):  # 已修改
    print("点击了管口确定按钮")

    # tab_name = viewer_instance.tabWidget.tabText(viewer_instance.tabWidget.currentIndex())
    #
    # if tab_name == "管口材料分类1":
    #     table_param = viewer_instance.tableWidget_guankou
    # else:
    #     table_param = viewer_instance.dynamic_guankou_param_tabs.get(tab_name)
    #
    # if table_param is None:
    #     table_param = viewer_instance.tableWidget_guankou

    tw = getattr(viewer_instance, "guankou_tabWidget", None)
    if tw is None:
        return

    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()

    table_param = _get_tab_table(viewer_instance, cur_idx)  # 统一用按索引取表
    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return

    # 读“管口号”
    selected_text = ""
    for r in range(table_param.rowCount()):
        it0 = table_param.item(r, 0)
        if it0 and it0.text().strip() == "管口号":
            it1 = table_param.item(r, 1)
            selected_text = (it1.text().strip() if (it1 and it1.text()) else "")
            break

    import re
    def parse_codes(s: str):
        return [x for x in re.split(r"[、，,\s]+", s.strip()) if x]

    selected_codes = parse_codes(selected_text)
    # print(f"[DBG] 当前 tab={tab_name}, UI 选中的管口号={selected_codes}")  # 【新增1】

    product_id = getattr(viewer_instance, "product_id", None)
    # 1) 保存占用（确保 commit）
    try:
        save_guankou_codes_for_tab(getattr(viewer_instance, "product_id", None), tab_name, selected_codes)
        # print(f"[DBG] 已保存管口号到DB: {selected_codes}")  # 【新增2】
        if hasattr(viewer_instance, "force_commit"):
            viewer_instance.force_commit()  # 如有这个方法就调用；没有就忽略
            # print("[DBG] 已执行 force_commit()")  # 【新增3】

        save_other_params_for_tab(viewer_instance, table_param, viewer_instance.product_id, tab_name)
        # print("[DBG] 已保存其他参数")  # 【新增5】

        # 【修改】紧接着同步腐蚀裕量（依赖管口号）
        try:
            print(f"[DBG] 同步腐蚀裕量: product={product_id}, tab={tab_name}, codes={selected_codes}")
            sync_corrosion_to_guankou_param(product_id, selected_codes, tab_name)
            # print("[DBG] 已执行 sync_corrosion_to_guankou_param")  # 【新增4】

            # === 只刷新当前 tab ===
            from modules.cailiaodingyi.funcs.funcs_pdf_input import query_guankou_param_by_product
            data = query_guankou_param_by_product(product_id, tab_name) or []

            old_table = getattr(viewer_instance, "tableWidget_guankou", None)
            viewer_instance.tableWidget_guankou = table_param  # 临时绑定
            try:
                render_guankou_param_to_ui(viewer_instance, data)
                print(f"[DBG][refresh] 渲染完成 label={tab_name}, data条数={len(data)}")
                viewer_instance.patch_codes_for_current_tab(table_param, tab_name)
            finally:
                viewer_instance.tableWidget_guankou = old_table

        except Exception as e:
            print(f"[错误] 腐蚀裕量同步失败：{e}")
    except Exception as e:
        print(f"[错误] 保存占用失败：{e}")

    # 2) 刷新（把“本次真正分配集合”传进去）
    refresh_all_tabs_after_save(viewer_instance, cur_idx, set(selected_codes))

    QMessageBox.information(viewer_instance, "提示", f"{tab_name} 已保存管口号：{selected_text or '无'}")
    # 生成压力等级提示
    if selected_codes:
        try:
            pressure_tips = generate_pressure_level_tips_for_guankou_codes(
                viewer_instance.product_id,
                selected_codes
            )
            if pressure_tips:
                show_pressure_level_tips_dialog(viewer_instance, pressure_tips)
        except Exception as e:
            print(f"[警告] 生成压力等级提示失败: {e}")

# ===压力等级提示新增方法:获取管口ID==
def get_guankou_id_by_product_and_code(product_id: str, guankou_code: str) -> str:
    """
    根据产品ID和管口代号从产品设计活动表_管口类别表中获取对应的管口ID

    Args:
        product_id: 产品ID
        guankou_code: 管口代号（如 N1, N2 等）

    Returns:
        str: 管口ID，如果未找到则返回空字符串
    """
    import pymysql
    from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_1

    try:
        # 使用产品设计活动库连接
        connection = pymysql.connect(**db_config_1)
        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # 查询产品设计活动表_管口类别表
                sql = """
                    SELECT 管口ID 
                    FROM 产品设计活动表_管口类别表 
                    WHERE 产品ID = %s AND 管口代号 = %s
                """

                cursor.execute(sql, (product_id, guankou_code))
                result = cursor.fetchone()

                if result:
                    return str(result['管口ID'])
                else:
                    print(f"[提示] 未找到匹配记录 - 产品ID: {product_id}, 管口代号: {guankou_code}")
                    return ""

        finally:
            connection.close()

    except Exception as e:
        print(f"[错误] 查询管口ID失败 - 产品ID: {product_id}, 管口代号: {guankou_code}, 错误: {e}")
        return ""


def generate_pressure_level_tips_for_guankou_codes(product_id: str, guankou_codes: list) -> dict:
    """
    为多个管口代号生成压力等级提示

    Args:
        product_id: 产品ID
        guankou_codes: 管口代号列表，如 ['N1', 'N2', 'N3']

    Returns:
        dict: 管口代号到提示信息的映射，格式：
              {
                  'N1': '提示信息1',
                  'N2': '提示信息2',
                  'error': '错误信息（如果有）'
              }
    """
    from modules.guankoudingyi.funcs.pipe_get_units_types import get_unit_types_from_db
    from modules.cailiaodingyi.funcs.funcs_pdf_change import query_guankou_affiliation
    from modules.guankoudingyi.funcs.funcs_pipe_comboBox_value import generate_pressure_level_tips

    tips_result = {}

    try:
        # 1. 获取公称压力类型
        unit_types = get_unit_types_from_db(product_id)
        if not unit_types:
            #     tips_result['error'] = "无法获取产品的公称尺寸类型信息"
            #     return tips_result
            # pressure_type = unit_types.get('公称压力类型', 'Class')
            # 无法获取单位类型信息时，使用默认的公称压力类型
            pressure_type = 'Class'
        else:
            pressure_type = unit_types.get('公称压力类型', 'Class')

        # 2. 为每个管口代号生成提示
        for guankou_code in guankou_codes:
            try:
                # 获取管口ID
                pipe_id = get_guankou_id_by_product_and_code(product_id, guankou_code)
                if not pipe_id:
                    tips_result[guankou_code] = f"管口代号 {guankou_code} 未找到对应的管口ID"
                    continue

                # 获取管口所属元件
                pipe_belong = query_guankou_affiliation(product_id, guankou_code)
                if not pipe_belong:
                    tips_result[guankou_code] = f"管口代号 {guankou_code} 未找到所属元件信息"
                    continue

                # 映射到管口所属元件格式（适配原有方法）
                if pipe_belong == "管程":
                    pipe_belong_mapped = "管箱圆筒"
                elif pipe_belong == "壳程":
                    pipe_belong_mapped = "壳体圆筒"
                else:
                    pipe_belong_mapped = pipe_belong

                # 生成压力等级提示
                tip_message = generate_pressure_level_tips(
                    product_id,
                    pipe_belong_mapped,
                    pressure_type,
                    pipe_id,
                    guankou_code
                )

                tips_result[guankou_code] = tip_message

            except Exception as e:
                tips_result[guankou_code] = f"管口代号 {guankou_code} 提示生成失败: {str(e)}"
                print(f"[错误] 管口 {guankou_code} 提示生成失败: {e}")

        return tips_result

    except Exception as e:
        tips_result['error'] = f"生成压力等级提示时发生错误: {str(e)}"
        print(f"[错误] 生成压力等级提示失败: {e}")
        return tips_result


def show_pressure_level_tips_dialog(parent, tips_dict: dict):
    """
    将压力等级提示信息显示到line_tip组件中

    Args:
        parent: 父窗口（viewer_instance）
        tips_dict: 提示信息字典，格式同 generate_pressure_level_tips_for_guankou_codes 返回值
    """
    from PyQt5.QtCore import Qt

    if not hasattr(parent, 'line_tip'):
        print("[警告] parent 没有 line_tip 组件")
        return

    # 处理错误信息
    if 'error' in tips_dict:
        error_message = f"压力等级提示错误: {tips_dict['error']}"

        # 使用 QFontMetrics 动态计算截断
        metrics = parent.line_tip.fontMetrics()
        available_width = parent.line_tip.width() - 30  # 给两边留点间距
        elided_text = metrics.elidedText(error_message.replace("\n", " | "), Qt.ElideRight, available_width)

        # 如果被省略了，加上提示
        if elided_text != error_message:
            elided_text += "(鼠标悬停查看完整内容)"

        # 设置显示和悬浮提示
        parent.line_tip.setText(elided_text)
        parent.line_tip.setToolTip(error_message)  # 鼠标悬停完整信息
        parent.line_tip.setStatusTip(error_message)  # 状态栏完整信息
        parent.line_tip.setStyleSheet("color: red;")
        return

    # 合并所有管口的提示信息
    tip_messages = []
    for guankou_code, tip_message in tips_dict.items():
        if guankou_code == 'error':
            continue
        # 为每个管口添加标识，便于区分
        formatted_message = f"【{guankou_code}】{tip_message}"
        tip_messages.append(formatted_message)

    if not tip_messages:
        parent.line_tip.setText("未获取到管口压力等级提示信息")
        parent.line_tip.setToolTip("未获取到管口压力等级提示信息")
        parent.line_tip.setStatusTip("未获取到管口压力等级提示信息")
        parent.line_tip.setStyleSheet("color: orange;")
        return

    # 合并所有提示信息
    full_message = "\n".join(tip_messages)

    try:
        # 使用 QFontMetrics 动态计算文字长度
        metrics = parent.line_tip.fontMetrics()
        available_width = parent.line_tip.width() - 30  # 给左右留点空隙
        elided_text = metrics.elidedText(full_message.replace("\n", " | "), Qt.ElideRight, available_width)

        # 如果被省略了，加上提示
        if elided_text != full_message:
            elided_text += "(鼠标悬停查看完整内容)"

        # 设置显示与悬浮完整提示
        parent.line_tip.setText(elided_text)
        parent.line_tip.setToolTip(full_message)  # 鼠标悬停显示完整内容
        parent.line_tip.setStatusTip(full_message)  # 状态栏也显示完整内容
        parent.line_tip.setStyleSheet("color: orange;")

    except Exception as e:
        error_message = f"显示压力等级提示失败: {str(e)}"

        # 使用 QFontMetrics 动态计算截断
        metrics = parent.line_tip.fontMetrics()
        available_width = parent.line_tip.width() - 30  # 给两边留点间距
        elided_text = metrics.elidedText(error_message.replace("\n", " | "), Qt.ElideRight, available_width)

        # 如果被省略了，加上提示
        if elided_text != error_message:
            elided_text += "(鼠标悬停查看完整内容)"

        # 设置显示和悬浮提示
        parent.line_tip.setText(elided_text)
        parent.line_tip.setToolTip(error_message)  # 鼠标悬停完整信息
        parent.line_tip.setStatusTip(error_message)  # 状态栏完整信息
        parent.line_tip.setStyleSheet("color: red;")


# ===压力等级提示新增方法:获取管口ID==
def get_guankou_id_by_product_and_code(product_id: str, guankou_code: str) -> str:
    """
    根据产品ID和管口代号从产品设计活动表_管口类别表中获取对应的管口ID

    Args:
        product_id: 产品ID
        guankou_code: 管口代号（如 N1, N2 等）

    Returns:
        str: 管口ID，如果未找到则返回空字符串
    """
    import pymysql
    from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_1

    try:
        # 使用产品设计活动库连接
        connection = pymysql.connect(**db_config_1)
        try:
            with connection.cursor(pymysql.cursors.DictCursor) as cursor:
                # 查询产品设计活动表_管口类别表
                sql = """
                    SELECT 管口ID 
                    FROM 产品设计活动表_管口类别表 
                    WHERE 产品ID = %s AND 管口代号 = %s
                """

                cursor.execute(sql, (product_id, guankou_code))
                result = cursor.fetchone()

                if result:
                    return str(result['管口ID'])
                else:
                    print(f"[提示] 未找到匹配记录 - 产品ID: {product_id}, 管口代号: {guankou_code}")
                    return ""

        finally:
            connection.close()

    except Exception as e:
        print(f"[错误] 查询管口ID失败 - 产品ID: {product_id}, 管口代号: {guankou_code}, 错误: {e}")
        return ""








def render_additional_info_table(viewer_instance, additional_info):
    details_table = viewer_instance.tableWidget_detail
    with FreezeUI(details_table):   # 🚩 批量操作前冻结
        details_table.setRowCount(0)
        details_table.clearContents()
        headers = ["参数名称", "参数值", "参数单位"]
        details_table.setColumnCount(len(headers))
        details_table.setHorizontalHeaderLabels(headers)
        details_table.setRowCount(len(additional_info))
        for row_idx, row_data in enumerate(additional_info):
            for col_idx, header_name in enumerate(headers):
                item = QTableWidgetItem(str(row_data.get(header_name, "")))
                item.setTextAlignment(Qt.AlignCenter)
                if col_idx in [0, 2]:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                details_table.setItem(row_idx, col_idx, item)



def render_guankou_param_table(viewer_instance, guankou_param_info):
    """渲染管口参数定义数据到表格"""

    guankou_define = viewer_instance.tableWidget_guankou_define  # 获取右侧的表格控件

    # 清空现有数据
    guankou_define.clear()  # 清除所有行列和表头
    guankou_define.setRowCount(0)
    guankou_define.setColumnCount(0)

    # 设置列标题
    headers = ["零件名称", "材料类型", "材料牌号", "材料标准", "供货状态"]
    guankou_define.setColumnCount(len(headers))
    guankou_define.setRowCount(len(guankou_param_info))  # 设置行数
    guankou_define.setHorizontalHeaderLabels(headers)

    # 自动调整列宽
    header = guankou_define.horizontalHeader()
    for i in range(guankou_define.columnCount()):
        header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

    # 填充表格
    for row_idx, row_data in enumerate(guankou_param_info):
        for col_idx, header_name in enumerate(headers):
            item = QTableWidgetItem(str(row_data.get(header_name, "")))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            guankou_define.setItem(row_idx, col_idx, item)


def handle_guankou_table_click(viewer_instance, row, col):

    print(f"传入数据{viewer_instance.guankou_define_info}")
    """处理点击零件列表的逻辑"""

    # 获取当前点击行的数据
    clicked_guankou_define_data = viewer_instance.guankou_define_info[row]  # 获取已经存储的行数据
    print(f"点击的行数据: {clicked_guankou_define_data}")

    viewer_instance.clicked_guankou_define_data = clicked_guankou_define_data

    # 获取管口零件ID
    guankou_id = clicked_guankou_define_data.get("管口零件ID", None)
    print(f"管口：{guankou_id}")
    # print(f"此时点击{clicked_guankou_define_data}")
    category_label = viewer_instance.label
    print(f"类别1: {category_label}")
    # category_label = clicked_guankou_define_data.get("类别", None)
    # print(f"类别: {category_label}")

    # 查询管口附加参数数据
    guankou_additional_info = load_guankou_para_data_leibie(guankou_id, category_label)
    print(f"管口零件参数信息: {guankou_additional_info}")

    # 渲染附加参数表格
    render_guankou_info_table(viewer_instance, guankou_additional_info)


def render_guankou_info_table(viewer_instance, additional_info):
    """渲染管口零件附加参数信息"""
    print(f"渲染了")
    details_table = viewer_instance.tableWidget_guankou_param
    print(f"当前数据{additional_info}")

    # ✅ 先获取旧行列数
    old_row_count = details_table.rowCount()
    old_col_count = details_table.columnCount()

    # ✅ 清除所有 cellWidgets
    for row in range(old_row_count):
        for col in range(old_col_count):
            widget = details_table.cellWidget(row, col)
            if widget:
                widget.deleteLater()
                details_table.removeCellWidget(row, col)

    # ✅ 再清空所有数据
    details_table.setRowCount(0)
    details_table.clearContents()

    headers = ["参数名称", "参数值", "参数单位"]

    # 隐藏列序号
    details_table.verticalHeader().setVisible(False)

    details_table.setColumnCount(len(headers))
    details_table.setRowCount(len(additional_info))
    details_table.setHorizontalHeaderLabels(headers)
    details_table.verticalHeader().setVisible(False)

    header = details_table.horizontalHeader()
    for i in range(details_table.columnCount()):
        header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

    for row_idx, row_data in enumerate(additional_info):
        for col_idx, header_name in enumerate(headers):
            item = QTableWidgetItem(str(row_data.get(header_name, "")))
            item.setTextAlignment(QtCore.Qt.AlignCenter)
            # ✅ 设置只读（不可编辑）列：参数名称 和 参数单位
            if col_idx in [0, 2]:  # 参数名称列 和 参数单位列
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            details_table.setItem(row_idx, col_idx, item)
        print(f"[插入检查] 行 {row_idx} param: {row_data.get('参数名称')} → 值: {row_data.get('参数值')}")
    details_table.viewport().update()
    details_table.repaint()

    # details_table.setStyleSheet("QHeaderView::section { background-color: lightgreen; }")



def setup_overlay_controls_logic(table, param_col, value_col, param_name, combo, field_widgets):
    material_type_fields = {
        "覆层材料类型": {
            "control_field": "是否添加覆层",
            "level_field": "覆层材料级别",
            "status_field": "覆层使用状态",
            "process_field": "覆层成型工艺"
        },
        "管程侧覆层材料类型": {
            "control_field": "管程侧是否添加覆层",
            "level_field": "管程侧覆层材料级别",
            "status_field": "管程侧覆层使用状态",
            "process_field": "管程侧覆层成型工艺"
        },
        "壳程侧覆层材料类型": {
            "control_field": "壳程侧是否添加覆层",
            "level_field": "壳程侧覆层材料级别",
            "status_field": "壳程侧覆层使用状态",
            "process_field": "壳程侧覆层成型工艺"
        }
    }

    # 1. 对“是否添加覆层”字段的基本控制
    if param_name in ["是否添加覆层", "管程侧是否添加覆层", "壳程侧是否添加覆层"]:
        def on_cover_toggle(index, c=combo):
            value = c.currentText().strip()
            show = value == "是"

            # 根据当前控制字段，隐藏/显示对应字段
            for name, info in material_type_fields.items():
                if info["control_field"] == param_name:
                    targets = [name, info["level_field"], info["status_field"], info["process_field"]]
                    for r in range(table.rowCount()):
                        pitem = table.item(r, param_col)
                        if pitem and pitem.text().strip() in targets:
                            table.setRowHidden(r, not show)

                    if "on_material_type_changed_" + name in field_widgets:
                        field_widgets["on_material_type_changed_" + name](-1)

        combo.currentIndexChanged.connect(on_cover_toggle)
        QTimer.singleShot(0, lambda: on_cover_toggle(combo.currentIndex()))
        return

    # 2. 针对“覆层材料类型”联动成型工艺设置
    if param_name in material_type_fields:
        field_info = material_type_fields[param_name]

        def on_material_type_changed(index, c=combo):
            value = c.currentText().strip()
            print(f"[联动] 当前选择的 {param_name}: {value}")

            # 获取控制字段的值
            control_value = ""
            for rr in range(table.rowCount()):
                item = table.item(rr, param_col)
                if item and item.text().strip() == field_info["control_field"]:
                    widget = table.cellWidget(rr, value_col)
                    if isinstance(widget, QComboBox):
                        control_value = widget.currentText().strip()
                    break

            # 隐藏级别和状态字段（仅当板材+是才显示）
            for r in range(table.rowCount()):
                pitem = table.item(r, param_col)
                if not pitem:
                    continue
                pname = pitem.text().strip()
                if pname == field_info["level_field"]:
                    table.setRowHidden(r, not (control_value == "是" and value == "钢板"))
                if pname == field_info["status_field"]:
                    table.setRowHidden(r, not (control_value == "是" and value == "钢板"))

            # 延迟设置成型工艺
            def delayed_fill():
                widget = field_widgets.get(field_info["process_field"])
                if not widget:
                    print(f"[警告] {field_info['process_field']} 控件未找到")
                    return

                if not isinstance(widget, QComboBox):
                    print(f"[跳过] {field_info['process_field']} 不是 QComboBox")
                    return

                if control_value != "是":
                    print(f"[跳过] {field_info['control_field']} 未选中“是”，跳过设置 {field_info['process_field']}")
                    return

                widget.blockSignals(True)
                widget.clear()
                widget.addItem("")  # 空项，避免锁死

                if value == "钢板":
                    widget.addItems(["轧制复合", "爆炸焊接"])
                    widget.setCurrentText("爆炸焊接")
                elif value == "焊材":
                    widget.addItem("堆焊")
                    widget.setCurrentText("堆焊")
                else:
                    widget.setCurrentText("")
                widget.blockSignals(False)

            QTimer.singleShot(50, delayed_fill)

        # 绑定唯一键，支持多个材料类型字段独立注册
        field_widgets["on_material_type_changed_" + param_name] = on_material_type_changed
        combo.currentIndexChanged.connect(on_material_type_changed)


def find_row_by_param_name(table: QTableWidget, name: str, param_col: int,
                           *, fuzzy: bool = False) -> Optional[int]:
    """
    在参数表中按“参数名称列(param_col)”查找行号。
    - 精确匹配：默认；去掉前后空格后完全相等
    - 模糊匹配：fuzzy=True 时，支持以 name 为前缀（如 '覆层材料级别' 可匹配 '管程侧覆层材料级别'）
    找不到返回 None
    """
    if not table or name is None:
        return None

    target = (str(name)).strip()
    if not target:
        return None

    for r in range(table.rowCount()):
        it = table.item(r, param_col)
        if not it:
            continue
        txt = (it.text() or "").strip()
        if txt == target:
            return r
        if fuzzy and txt.startswith(target):
            return r
    return None

def _apply_cladding_type_logic(table, param_col, value_col, type_field_name: str, type_value: str):
    """
    覆层材料类型联动：
      - = '焊材'  → 隐藏「覆层材料级别」「覆层使用状态」，并把「覆层成型工艺」限定为 ['堆焊'] 且值=堆焊
      - = '板材'  → 显示 上述两项，且「覆层成型工艺」候选 ['轧制复合','爆炸焊接']，默认爆炸焊接
      - 其它/空   → 仅恢复可见，不强制设工艺
    同时支持「管程侧/壳程侧」前缀的同名字段。
    """
    from PyQt5.QtCore import QSignalBlocker
    from PyQt5.QtWidgets import QTableWidgetItem
    # 你项目里已经在本函数中使用过 ComboDelegate，这里直接复用
    # from modules.cailiaodingyi.controllers.combo import ComboDelegate  # 若需要显式导入就解开

    prefix = "管程侧" if type_field_name.startswith("管程侧") else ("壳程侧" if type_field_name.startswith("壳程侧") else "")
    def N(x): return f"{prefix}{x}" if prefix else x

    def _row(label):
        return find_row_by_param_name(table, label, param_col)

    def _set(row, text):
        if row is None: return
        with QSignalBlocker(table):
            it = table.item(row, value_col)
            if it is None:
                it = QTableWidgetItem("")
                table.setItem(row, value_col, it)
            it.setText(text or "")

    level_row = _row(N("覆层材料级别"))
    state_row = _row(N("覆层使用状态"))
    craft_row = _row(N("覆层成型工艺"))

    v = (type_value or "").strip()
    if v == "焊材":
        if level_row is not None: table.setRowHidden(level_row, True)
        if state_row is not None: table.setRowHidden(state_row, True)
        if craft_row is not None:
            # 只允许“堆焊”
            try:
                table.setItemDelegateForRow(craft_row, ComboDelegate(["堆焊"], table))
            except Exception:
                pass
            _set(craft_row, "堆焊")
    elif v in ("板材", "钢板"):
        # 显示“覆层材料级别/覆层使用状态”
        if level_row is not None: table.setRowHidden(level_row, False)
        if state_row is not None: table.setRowHidden(state_row, False)
        # “覆层成型工艺”可选：爆炸焊接、轧制复合；默认爆炸焊接
        if craft_row is not None:
            try:
                # 注意把“爆炸焊接”放前面，便于默认
                table.setItemDelegateForRow(craft_row, ComboDelegate(["爆炸焊接", "轧制复合"], table))
            except Exception:
                pass
            cur = table.item(craft_row, value_col)
            cur_txt = cur.text().strip() if cur else ""
            # 若当前为空或不在可选范围内，则设为默认“爆炸焊接”
            if cur_txt not in ("爆炸焊接", "轧制复合"):
                _set(craft_row, "爆炸焊接")
    else:
        # 恢复可见，不强制设值
        if level_row is not None: table.setRowHidden(level_row, False)
        if state_row is not None: table.setRowHidden(state_row, False)









def apply_paramname_combobox(table: QTableWidget, param_col: int, value_col: int, viewer_instance):
    """
    最终版：
      - 普通下拉：使用现有 ComboDelegate(options)
      - 材料四字段：install_material_delegate_linkage() 统一安装代理 + 建立联动
      - 数值字段：QLineEdit + 校验（含腐蚀裕量自动带入）
      - 覆层开关：使用 ComboDelegate(['是','否']) + itemChanged 联动/写库/刷新
      - 其它元件的“显隐联动”：evaluate_visibility_rules_from_db()（查库+计算封装）
    """
    # ===== 必要导入 =====
    from PyQt5.QtCore import Qt, QEvent, QTimer
    from PyQt5.QtWidgets import (
        QStyledItemDelegate, QLineEdit, QTableWidgetItem, QAbstractItemView
    )

    # ===== 常量集合 =====
    MATERIAL_FIELDS = {
        "材料类型", "材料牌号", "材料标准", "供货状态",
        "垫板材料类型", "垫板材料牌号", "垫板材料标准", "垫板材料供货状态"
    }
    COVERING_SWITCH_GLOBAL = {"是否添加覆层"}
    COVERING_SWITCH_SIDED  = {"管程侧是否添加覆层", "壳程侧是否添加覆层"}
    CLADDING_TYPE_FIELDS = {"覆层材料类型", "管程侧覆层材料类型", "壳程侧覆层材料类型"}
    READONLY_PARAMS = {"元件名称", "零件名称"}   # 这里把“零件名称”也列为只读
    SYNC_THICK_PARAMS = {"内折流板厚度", "异形折流板厚度", "弓形折流板厚度", "支持板厚度"}

    # ===== 统一的来源/签名角色 =====
    ROLE_SRC = Qt.UserRole          # "auto"/"manual"
    ROLE_SIG = Qt.UserRole + 1      # “驱动签名”：名称|标准|型式
    AUTO_TAG = "auto"
    MANUAL_TAG = "manual"
    WEAK_VALS = {"", "程序推荐"}     # 可被自动覆盖的弱值
    DIM_PARAMS = {"垫片名义外径D2n","垫片名义内径D1n","环内径d1","垫片外径D","垫片内径d","外径D","内径d","d1"}

    # ---------- 工具：安全获取当前元件名称 ----------
    def _current_element_name() -> str:
        name = ""
        try:
            ced = getattr(viewer_instance, "clicked_element_data", None) or {}
            # ① 先从 clicked_element_data 里拿
            for key in ("元件名称", "零件名称"):
                if key in ced and str(ced.get(key) or "").strip():
                    name = str(ced.get(key)).strip()
                    break
            # ② 拿不到就从表里读“元件名称/零件名称”的值列
            if not name:
                for key in ("元件名称", "零件名称"):
                    r = find_row_by_param_name(table, key, param_col)
                    if r is not None:
                        itv = table.item(r, value_col)
                        txt = (itv.text() if itv else "") if itv else ""
                        if txt and str(txt).strip():
                            name = str(txt).strip()
                            break
        except Exception as e:
            print(f"[显隐规则] 元件名获取异常: {e}")
        if not name:
            print("[显隐规则] 未获取到元件名称（规则将不生效）")
        return name

    # == 当前垫片签名 ==
    def _current_gasket_signature() -> str:
        """返回当前上下文的垫片驱动签名：名称|标准|型式（名称缺失时用元件名）"""
        try:
            ele_name = _current_element_name() or ""
            def _val(param):
                r = find_row_by_param_name(table, param, param_col)
                it = table.item(r, value_col) if r is not None else None
                return (it.text() if it else "").strip()
            gasket_name     = _val("垫片名称") or ele_name
            gasket_standard = _val("垫片标准")
            gasket_type     = _val("垫片型式") or _val("垫片类型")
            return f"{gasket_name}|{gasket_standard}|{gasket_type}"
        except Exception:
            return ""

    # == 行级锁容器 & 上次签名缓存 ==
    if not hasattr(table, "_gasket_user_lock"):
        table._gasket_user_lock = {}   # {参数名: 签名}
    if not hasattr(table, "_gasket_last_sig"):
        table._gasket_last_sig = ""

    # ---------- 数值代理 ----------
    class NumericDelegate(QStyledItemDelegate):
        def __init__(self, rule: str, pname_for_tip: str, minmax=None, allowed_texts=None):
            super().__init__(table)
            self.rule = rule
            self.pname = pname_for_tip
            self.minmax = minmax or (None, None, True, True)
            self.allowed_texts = set(allowed_texts or [])

        def createEditor(self, parent, option, index):
            le = QLineEdit(parent)
            le.setAlignment(Qt.AlignCenter)
            le.setAutoFillBackground(True)
            le.setStyleSheet("""
                QLineEdit{
                    border:none;
                    background:palette(base);
                    font-size:9pt;
                    font-family:"Microsoft YaHei";
                    padding-left:2px;
                }
            """)
            le.editingFinished.connect(lambda: self.commitData.emit(le))
            le.returnPressed.connect(lambda: (self.commitData.emit(le),
                                              self.closeEditor.emit(le, QStyledItemDelegate.NoHint)))
            le.installEventFilter(self)
            return le

        def eventFilter(self, editor, ev):
            if isinstance(editor, QLineEdit) and ev.type() == QEvent.FocusOut:
                try:
                    self.commitData.emit(editor)
                except Exception:
                    pass
            return super().eventFilter(editor, ev)

        def setEditorData(self, editor, index):
            editor.setText(index.data() or "")
            editor.selectAll()

        def updateEditorGeometry(self, editor, option, index):
            editor.setGeometry(option.rect)

        def setModelData(self, editor, model, index):
            tip = getattr(viewer_instance, "line_tip", None)
            txt = (editor.text() or "").strip()

            def show_tip(msg: str):
                if not tip: return
                tip.setStyleSheet("color:red;")
                tip.setText(msg)
                QTimer.singleShot(0, lambda: (tip.setStyleSheet("color:red;"), tip.setText(msg)))
                QTimer.singleShot(50, lambda: (tip.setStyleSheet("color:red;"), tip.setText(msg)))

            def clear_tip():
                if tip: tip.setText("")

            if txt == "":
                model.setData(index, "")
                clear_tip()
                return

            # ✅ 放行允许字面值
            if txt in self.allowed_texts:
                clear_tip()
                model.setData(index, txt)
                return

            try:
                val = float(txt)
                ok = True
                limit_msg = "有效数值"
                if self.rule == "gt0":
                    ok = (val > 0);
                    limit_msg = "大于 0"
                elif self.rule == "ge0":
                    ok = (val >= 0);
                    limit_msg = "大于等于 0"
                elif self.rule == "range":
                    lo, hi, lo_inc, hi_inc = self.minmax;
                    parts = []
                    if lo is not None:
                        ok = ok and (val >= lo if lo_inc else val > lo);
                        parts.append(("≥" if lo_inc else ">") + str(lo))
                    if hi is not None:
                        ok = ok and (val <= hi if hi_inc else val < hi);
                        parts.append(("≤" if hi_inc else "<") + str(hi))
                    limit_msg = " 且 ".join(parts) if parts else "有效范围"

                # 🚩 特殊处理：滑道与竖直中心线夹角
                if self.pname == "滑道与竖直中心线夹角":
                    if val < 15 or val > 25:
                        # 不直接弹窗，交给 on_confirm_param_update 去处理
                        model.setData(index, txt)
                        table._angle_needs_confirm = (index.row(), index.column())
                        return

                if not ok:
                    extra = f"，或输入：{'、'.join(sorted(self.allowed_texts))}" if self.allowed_texts else ""
                    show_tip(f"第 {index.row() + 1} 行参数'{self.pname}'的值应为{limit_msg}的数字{extra}！")
                    model.setData(index, "")
                    return

                clear_tip()
                model.setData(index, txt)
            except Exception:
                extra = f"，或输入：{'、'.join(sorted(self.allowed_texts))}" if self.allowed_texts else ""
                show_tip(f"第 {index.row() + 1} 行参数'{self.pname}'的值应为数字{extra}！")
                model.setData(index, "")

    def _prefix_from(name: str) -> str:
        return "管程侧" if name.startswith("管程侧") else ("壳程侧" if name.startswith("壳程侧") else "")

    def _is_covering_enabled_for(field_name: str) -> bool:
        prefix = _prefix_from(field_name)
        switch = f"{prefix}是否添加覆层" if prefix else "是否添加覆层"
        r_sw = find_row_by_param_name(table, switch, param_col)
        if r_sw is None: return False
        it_sw = table.item(r_sw, value_col)
        return bool(it_sw and it_sw.text().strip() == "是")

    # ---------- 锻件级别显隐：仅当材料类型=钢锻件时显示 ----------
    def _apply_forging_visibility_local():
        try:
            r_mat_type = find_row_by_param_name(table, "材料类型", param_col)
            r_forging = find_row_by_param_name(table, "锻件级别", param_col)
            if r_forging is None:
                return
            mat_txt = ""
            if r_mat_type is not None:
                it = table.item(r_mat_type, value_col)
                mat_txt = (it.text() if it else "").strip()
            show = (mat_txt == "钢锻件")
            table.setRowHidden(r_forging, not show)
        except Exception as e:
            print(f"[锻件级别显隐] 处理失败：{e}")

    # 可能会用到的外部数据
    try:
        param_names = set(get_all_param_name() or [])
    except Exception:
        param_names = set()
    gt0_params, ge0_params, range_params, allowed_map = get_numeric_rules()
    print("[rules] gt0:", len(gt0_params), " ge0:", len(ge0_params),
          " range:", len(range_params), " allowed_map:", len(allowed_map))


    # 1) 单击进入编辑
    table.setEditTriggers(QAbstractItemView.SelectedClicked)

    # 2) 清理 value 列 cellWidget
    for r in range(table.rowCount()):
        if table.cellWidget(r, value_col):
            table.setCellWidget(r, value_col, None)

    # 简化的小工具
    def ensure_editable_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt); table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        return it
    def ensure_readonly_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt); table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return it

    # 3) 初次渲染：用总闸防误触发
    table._loading = True
    table.blockSignals(True)
    try:
        for row in range(table.rowCount()):
            pitem = table.item(row, param_col)
            pname = pitem.text().strip() if pitem else ""

            if pname == "滑道与竖直中心线夹角":
                cur_text = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                ensure_editable_item(row, value_col, cur_text)
                table.setItemDelegateForRow(row, NumericDelegate("range", pname, (15, 25, True, True)))
                continue

            if pname in READONLY_PARAMS:
                table.setItemDelegateForRow(row, None)
                if table.cellWidget(row, value_col): table.setCellWidget(row, value_col, None)
                cur = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                ensure_readonly_item(row, value_col, cur); continue

            if pname in MATERIAL_FIELDS:
                cur_text = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                ensure_editable_item(row, value_col, cur_text); continue

            if (pname in gt0_params) or (pname in ge0_params) or (pname in range_params):
                vitem = table.item(row, value_col); cur_text = vitem.text().strip() if vitem else ""
                if pname in ["管程侧腐蚀裕量", "壳程侧腐蚀裕量"]:
                    try:
                        ct, cs = get_corrosion_allowance_from_db(viewer_instance.product_id)
                        element_id = viewer_instance.clicked_element_data.get("元件ID", "")
                        if pname == "管程侧腐蚀裕量" and ct is not None:
                            cur_text = str(ct); update_element_para_data(viewer_instance.product_id, element_id, pname, cur_text)
                        if pname == "壳程侧腐蚀裕量" and cs is not None:
                            cur_text = str(cs); update_element_para_data(viewer_instance.product_id, element_id, pname, cur_text)
                    except Exception as e:
                        print(f"[腐蚀裕量带入失败] {e}")
                ensure_editable_item(row, value_col, cur_text)
                if pname in gt0_params: rule, minmax = "gt0", None
                elif pname in ge0_params: rule, minmax = "ge0", None
                else: rule, minmax = "range", range_params.get(pname)
                allowed_texts_this_param = allowed_map.get(pname, set())
                table.setItemDelegateForRow(row, NumericDelegate(rule, pname, minmax, allowed_texts=allowed_texts_this_param))
                continue

            if pname in COVERING_SWITCH_GLOBAL or pname in COVERING_SWITCH_SIDED:
                vitem = table.item(row, value_col); cur_text = "是" if (vitem and vitem.text().strip() == "是") else "否"
                ensure_editable_item(row, value_col, cur_text)
                table.setItemDelegateForRow(row, ComboDelegate(["是", "否"], table)); continue

            # 普通下拉
            options = []
            try:
                if pname in param_names: options = get_options_for_param(pname) or []
            except Exception: options = []
            cur_text = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
            ensure_editable_item(row, value_col, cur_text)
            options = [o for o in dict.fromkeys([str(x).strip() for x in options]) if o != ""]
            if options: table.setItemDelegateForRow(row, ComboDelegate(options, table))
            else:       table.setItemDelegateForRow(row, None)

        # 初次显隐
        try:
            ele_name = _current_element_name()
            if ele_name:
                effects = evaluate_visibility_rules_from_db(
                    ele_name, table=table, param_col=param_col, value_col=value_col, viewer_instance=viewer_instance
                )
                with FreezeUI(table):
                    for tgt_param, act in effects.items():
                        rr = find_row_by_param_name(table, tgt_param, param_col)
                        if rr is not None:
                            table.setRowHidden(rr, act == "HIDE")
        except Exception as e:
            print(f"[显隐规则-初次评估失败] {e}")

    finally:
        table.blockSignals(False)
        table._loading = False

    _apply_forging_visibility_local()

    # 4) itemChanged：覆层联动 + 写库 + 图片刷新 + 再评估显隐
    def _on_item_changed(item: QTableWidgetItem):
        # 总闸
        if getattr(table, "_loading", False):
            return

        if item.column() != value_col:
            return

        r = item.row()
        pitem = table.item(r, param_col)
        if not pitem:
            return
        pname = pitem.text().strip()
        val = (item.text() or "").strip()

        # === 手改 D2n/D1n/d1：标记 MANUAL + 写入锁；空/推荐 → AUTO + 解锁 ===
        if pname in DIM_PARAMS:
            cur_sig = _current_gasket_signature()
            table.blockSignals(True)
            try:
                if val and (val not in WEAK_VALS):
                    item.setData(ROLE_SRC, MANUAL_TAG)
                    item.setData(ROLE_SIG, cur_sig)
                    table._gasket_user_lock[pname] = cur_sig
                else:
                    item.setData(ROLE_SRC, AUTO_TAG)
                    item.setData(ROLE_SIG, None)
                    table._gasket_user_lock.pop(pname, None)
            finally:
                table.blockSignals(False)

        # === 其它联动 ===
        if pname == "材料类型":
            _apply_forging_visibility_local()
            
        # === 固定鞍座参数同步：支座型式、支座标准、支座型号、鞍座高度 ===
        if pname in {"支座型式", "支座标准", "支座型号", "鞍座高度"}:
            try:
                sync_fixed_saddle_param_across_tabs(viewer_instance, pname, val)
            except Exception as e:
                print(f"[固定鞍座参数同步] 失败: {e}")

        # === 拉杆型式变化：更新定距管元件的定义状态 ===
        if pname == "拉杆型式":
            try:
                if val == "焊接拉杆":
                    # 焊接拉杆不需要定距管，将相关元件设为未定义
                    update_spacer_tube_status_to_undefined(viewer_instance.product_id)
                elif val == "螺纹拉杆":
                    # 螺纹拉杆需要定距管，将相关元件恢复为已定义
                    restore_spacer_tube_status_to_defined(viewer_instance.product_id)
            except Exception as e:
                print(f"[拉杆型式手动修改-定距管状态更新失败] {e}")

        if pname in CLADDING_TYPE_FIELDS:
            if not _is_covering_enabled_for(pname):
                pass
            else:
                with FreezeUI(table):
                    _apply_cladding_type_logic(table, param_col, value_col, pname, val)

        if pname in COVERING_SWITCH_GLOBAL or pname in COVERING_SWITCH_SIDED:
            try:
                product_id = viewer_instance.product_id
                element_id = viewer_instance.clicked_element_data.get("元件ID", "")
                update_element_para_data(product_id, element_id, pname, val)
            except Exception as e:
                print(f"[写库失败] {pname}={val}: {e}")

        if pname in COVERING_SWITCH_GLOBAL:
            handler = make_on_covering_changed(viewer_instance.clicked_element_data, viewer_instance, r, table=table)
            handler(val)
            handler2 = make_on_flange_face_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler2(val, pname)
            handler3 = make_on_head_type_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler3(val, pname)
            handler4 = make_on_fangchongban_face_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler4(val, pname)
            handler5 = make_on_fenchenggeban_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler5(val, pname)
            class _Fake:
                def __init__(self, t): self._t = t
                def currentText(self): return self._t
            with FreezeUI(table):
                toggle_covering_fields(table, _Fake(val), pname)
                if val == "是":
                    type_field = "覆层材料类型"
                    r_type = find_row_by_param_name(table, type_field, param_col)
                    if r_type is not None:
                        it_type = table.item(r_type, value_col)
                        cur_type = it_type.text().strip() if it_type else ""
                        _apply_cladding_type_logic(table, param_col, value_col, type_field, cur_type)

        # 这三个原来你用的是 `if pname in "法兰密封面"`（会按字符匹配），这里修正为相等判断
        if pname == "法兰密封面":
            handler = make_on_flange_face_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler(val, pname)
        if pname == "封头类型代号":
            handler = make_on_head_type_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler(val, pname)
        if pname == "防冲板形式":
            handler = make_on_fangchongban_face_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler(val, pname)
        if pname == "排净孔型式":
            handler = make_on_fenchenggeban_changed(viewer_instance.clicked_element_data, viewer_instance, r)
            handler(val, pname)
        if pname in COVERING_SWITCH_SIDED:
            refresh = make_on_fixed_tube_covering_changed_v2(
                viewer_instance.clicked_element_data, viewer_instance, table, param_col, value_col
            ); refresh()
            class _Fake:
                def __init__(self, t): self._t = t
                def currentText(self): return self._t
            with FreezeUI(table):
                toggle_covering_fields(table, _Fake(val), pname)
                if val == "是":
                    prefix = "管程侧" if pname.startswith("管程侧") else "壳程侧"
                    type_field = f"{prefix}覆层材料类型"
                    r_type = find_row_by_param_name(table, type_field, param_col)
                    if r_type is not None:
                        it_type = table.item(r_type, value_col)
                        cur_type = it_type.text().strip() if it_type else ""
                        _apply_cladding_type_logic(table, param_col, value_col, type_field, cur_type)

        # ==== 折流/支持板厚度四项：任一改动 → 其它三项跟随 + 同步写库 ====
        try:
            if pname in SYNC_THICK_PARAMS:
                # 1) UI 同步：其它三个参数的值设为当前 val（避免递归：blockSignals）
                others = SYNC_THICK_PARAMS - {pname}
                table.blockSignals(True)
                try:
                    for tgt in others:
                        rr = find_row_by_param_name(table, tgt, param_col)
                        if rr is not None:
                            if table.item(rr, value_col) is None:
                                ensure_editable_item(rr, value_col, "")
                            table.item(rr, value_col).setText(val)
                finally:
                    table.blockSignals(False)

                # 2) DB 同步：四个参数统一写入（按 产品ID + 参数名称）
                try:
                    pid = getattr(viewer_instance, "product_id", None)
                    if pid:
                        sync_baffle_thickness_to_db(pid, SYNC_THICK_PARAMS, val)
                except Exception as ee:
                    print(f"[厚度同步写库失败] {ee}")
        except Exception as e:
            print(f"[厚度联动失败] {e}")

        # ==== 管板强度削弱系数μ → 联动刚度削弱系数η（仅UI，不写库） ====
        if pname.strip() == "管板强度削弱系数μ":
            try:
                r_eta = find_row_by_param_name(table, "管板刚度度削弱系数", param_col)
                if r_eta is not None:
                    if table.item(r_eta, value_col) is None:
                        ensure_editable_item(r_eta, value_col, "")
                    table.blockSignals(True)
                    try:
                        table.item(r_eta, value_col).setText(val)
                    finally:
                        table.blockSignals(False)
            except Exception as e:
                print(f"[联动失败] μ→η: {e}")

        # ==== 拉杆型式：根据换热管外径自动带入（对比“库中外径数值”，变了才覆盖；允许用户改） ====
        try:
            # 缓存：上次使用过的外径数值
            if not hasattr(table, "_tierod_od_last"):
                table._tierod_od_last = None

            r_tierod = find_row_by_param_name(table, "拉杆型式", param_col)
            if r_tierod is not None and getattr(viewer_instance, "product_id", None):
                # 直接从库里拿当前外径（不依赖本表是否触发了 itemChanged）
                od_txt = query_extra_param_value(viewer_instance.product_id, "换热管外径")

                import re
                s_num = "".join(re.findall(r"[-\d.]+", str(od_txt or "").strip()))
                od_val = float(s_num) if s_num else None

                # 只有当“库中外径数值”与缓存不同，才覆盖拉杆型式
                if od_val is not None and od_val != table._tierod_od_last:
                    target = "焊接拉杆" if od_val < 19.0 else "螺纹拉杆"

                    if table.item(r_tierod, value_col) is None:
                        it = QTableWidgetItem("")
                        it.setTextAlignment(Qt.AlignCenter)
                        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                        table.setItem(r_tierod, value_col, it)

                    table.blockSignals(True)
                    try:
                        table.item(r_tierod, value_col).setText(target)
                    finally:
                        table.blockSignals(False)

                    # 根据拉杆型式更新定距管元件的定义状态
                    try:
                        if target == "焊接拉杆":
                            # 焊接拉杆不需要定距管，将相关元件设为未定义
                            update_spacer_tube_status_to_undefined(viewer_instance.product_id)
                        elif target == "螺纹拉杆":
                            # 螺纹拉杆需要定距管，将相关元件恢复为已定义
                            restore_spacer_tube_status_to_defined(viewer_instance.product_id)
                    except Exception as e:
                        print(f"[定距管状态更新失败] {e}")

                    table._tierod_od_last = od_val  # 更新缓存
        except Exception as e:
            print(f"[拉杆型式自动带入] 失败：{e}")

        # ==== 换热管 / U形换热管：级别或外径变化 -> 查库回填/清空 ====
        try:
            ele_name = _current_element_name()
            if ele_name in {"换热管", "U形换热管"} and pname in {"管束级别", "换热管外径"}:
                # 读取当前“管束级别”“换热管外径”的值
                r_lvl = find_row_by_param_name(table, "管束级别", param_col)
                r_od = find_row_by_param_name(table, "换热管外径", param_col)
                if r_lvl is not None and r_od is not None:
                    it_lvl = table.item(r_lvl, value_col)
                    it_od = table.item(r_od, value_col)
                    lvl = (it_lvl.text() if it_lvl else "").strip()
                    od_txt = (it_od.text() if it_od else "").strip()
                    if lvl and od_txt:
                        try:
                            od_val = float(od_txt)
                        except:
                            od_val = None

                        if od_val is not None:
                            spec = query_tube_specs_by_level_and_od(lvl, od_val)

                            # 目标行
                            r_tol_od = find_row_by_param_name(table, "换热管外径允许偏差", param_col)
                            r_hole_d = find_row_by_param_name(table, "管孔直径", param_col)
                            r_tol_h = find_row_by_param_name(table, "管孔直径允许偏差", param_col)

                            def _ensure_cell(rr):
                                if rr is None: return
                                if not table.item(rr, value_col):
                                    ensure_editable_item(rr, value_col, "")

                            def _write_or_clear(rr, value: str):
                                if rr is None: return
                                _ensure_cell(rr)
                                table.item(rr, value_col).setText(value if value else "")

                            # —— 回填（命中写值；未命中清空）——
                            with FreezeUI(table):
                                _write_or_clear(r_tol_od, spec.get("换热管外径允许偏差", ""))
                                _write_or_clear(r_hole_d, spec.get("管孔直径") or "")
                                _write_or_clear(r_tol_h, spec.get("管孔直径允许偏差", ""))

                            # —— 同步写库（同样命中写值；未命中写空串）——
                            try:
                                product_id = viewer_instance.product_id
                                element_id = viewer_instance.clicked_element_data.get("元件ID", "")
                                update_element_para_data(product_id, element_id, "换热管外径允许偏差",
                                                         spec.get("换热管外径允许偏差", ""))
                                update_element_para_data(product_id, element_id, "管孔直径", spec.get("管孔直径") or "")
                                update_element_para_data(product_id, element_id, "管孔直径允许偏差",
                                                         spec.get("管孔直径允许偏差", ""))
                            except Exception as ee:
                                print(f"[写库失败-换热管联动] {ee}")

        except Exception as e:
            print(f"[换热管联动] 计算失败：{e}")

        # ==== 垫片：驱动变更 → 清锁 + 强制覆盖；未变更 → 保护手动值 ====
        try:
            ele_name = _current_element_name()
            if ("垫片" in (ele_name or "")) and (pname in {"垫片标准", "垫片类型", "垫片型式"}):
                if getattr(table, "_loading", False):
                    return

                # —— 读三要素 —— #
                def _val(param):
                    rr = find_row_by_param_name(table, param, param_col)
                    it0 = table.item(rr, value_col) if rr is not None else None
                    return (it0.text() if it0 else "").strip()

                gasket_name     = _val("垫片名称") or ele_name
                gasket_standard = _val("垫片标准")
                gasket_type     = _val("垫片型式") or _val("垫片类型")
                cur_sig         = f"{gasket_name}|{gasket_standard}|{gasket_type}"

                driver_changed = (table._gasket_last_sig != cur_sig)

                # —— 查尺寸与材料 —— #
                spec  = resolve_gasket_dimensions(
                    product_id=viewer_instance.product_id,
                    gasket_name=gasket_name,
                    gasket_standard=gasket_standard,
                    gasket_type=gasket_type
                )

                # —— 2) 查材料/y/m（按类型+标准） ——
                props = query_gasket_material_options_by_type_std(gasket_type, gasket_standard)

                # 结果示例：{"垫片材料": "...", "垫片比压力y": "3.0", "垫片系数m": "1.0"} 或 {}

                # —— 工具：找行 / 置可编辑 / 写值 ——
                def _find_any(names):
                    for nm in names:
                        rr = find_row_by_param_name(table, nm, param_col)
                        if rr is not None:
                            return rr
                    return None

                row_D2n = _find_any(["垫片名义外径D2n", "垫片外径D", "外径D", "垫片外径"])
                row_D1n = _find_any(["垫片名义内径D1n", "垫片内径d", "内径d", "垫片内径"])
                row_d1 = _find_any(["环内径d1", "环内径", "d1"])

                row_mat = _find_any(["垫片材料"])
                row_y = _find_any(["垫片比压力y", "垫片比压y", "比压力y"])
                row_m = _find_any(["垫片系数m", "垫片系数M", "系数m"])

                def _ensure_editable(rr):
                    if rr is None: return
                    itx = table.item(rr, value_col)
                    if itx is None:
                        itx = QTableWidgetItem("")
                        table.setItem(rr, value_col, itx)
                    itx.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    itx.setTextAlignment(Qt.AlignCenter)

                def _pname_of_row(rr):
                    itp = table.item(rr, param_col)
                    return (itp.text().strip() if itp else "")

                def _clear_gasket_locks_for(params):
                    for nm in params:
                        table._gasket_user_lock.pop(nm, None)

                def _set_by_spec(rr, v, force=False):
                    if rr is None:
                        return
                    # 行级锁：仅在非强制 且 锁签名==当前签名 时拦截
                    tgt_name = _pname_of_row(rr)
                    if (not force):
                        locked_sig = table._gasket_user_lock.get(tgt_name)
                        if locked_sig and locked_sig == cur_sig:
                            return

                    _ensure_editable(rr)
                    itx      = table.item(rr, value_col)
                    cur_txt  = (itx.text().strip() if itx else "")
                    prev_sig = (itx.data(ROLE_SIG) if itx else None)
                    src_tag  = (itx.data(ROLE_SRC) if itx else None)

                    # ========== 【修改标记1】智能垫片驱动变化检测 ==========
                    # 检查是否是垫片类型或材料标准变化导致的强制更新
                    gasket_driver_changed = False
                    # 始终检查垫片驱动变化，不依赖于force参数
                    try:
                        # 获取当前垫片类型和材料标准
                        current_gasket_type = _val("垫片型式") or _val("垫片类型")
                        current_gasket_standard = _val("垫片标准")

                        # 检查垫片类型是否变化
                        gasket_type_changed = False
                        if current_gasket_type:
                            last_type = getattr(table, '_last_gasket_type', None)
                            if last_type and last_type != current_gasket_type:
                                gasket_type_changed = True
                                print(f"[DBG] 垫片联动: 垫片类型已变化: {last_type} → {current_gasket_type}")
                                # 设置全局变化状态
                                table._gasket_type_changing = True
                                # 主动触发垫片标准的更新
                                _trigger_gasket_standard_update_on_type_change(table)

                            table._last_gasket_type = current_gasket_type

                        # 检查是否处于垫片类型变化状态
                        if getattr(table, '_gasket_type_changing', False):
                            gasket_type_changed = True

                        # 检查材料标准是否变化
                        gasket_standard_changed = False
                        if current_gasket_standard:
                            last_standard = getattr(table, '_last_gasket_standard', None)
                            if last_standard and last_standard != current_gasket_standard:
                                gasket_standard_changed = True
                                print(f"[DBG] 垫片联动: 垫片标准已变化: {last_standard} → {current_gasket_standard}")
                                # 设置全局变化状态
                                table._gasket_standard_changing = True
                            table._last_gasket_standard = current_gasket_standard

                        # 检查是否处于垫片标准变化状态
                        if getattr(table, '_gasket_standard_changing', False):
                            gasket_standard_changed = True

                        # 如果垫片类型或材料标准发生变化，则认为是驱动变化
                        gasket_driver_changed = gasket_type_changed or gasket_standard_changed
                        print(f"[DBG] 垫片联动: 垫片驱动变化={gasket_driver_changed} (类型变化={gasket_type_changed}, 标准变化={gasket_standard_changed})")

                    except Exception as e:
                        print(f"[DBG] 垫片联动: 检测垫片驱动变化失败: {e}")
                        gasket_driver_changed = False

                    # ========== 【修改标记2】用户手动修改检查逻辑 ==========
                    # 如果当前值不是弱值且不是自动值，说明用户手动修改过
                    user_manually_modified = (cur_txt not in WEAK_VALS) and (src_tag != AUTO_TAG) and (cur_txt != "")

                    # ★★★ 关键判断：只有在垫片类型或材料标准变化时才覆盖用户修改 ★★★
                    if user_manually_modified and not gasket_driver_changed:
                        print(f"[DBG] 垫片联动: 参数{tgt_name}已被用户手动修改为{cur_txt}，且垫片驱动未变化，跳过覆盖")
                        return

                    # ========== 【修改标记3】垫片驱动变化时的强制覆盖逻辑 ==========
                    # 如果垫片类型或材料标准变化，即使参数被手动修改过，也要强制更新
                    if gasket_driver_changed:
                        print(f"[DBG] 垫片联动: 垫片驱动已变化，强制覆盖参数{tgt_name}为{v}")

                        # 特殊处理垫片材料：垫片类型变化时必须清空用户锁
                        if tgt_name == "垫片材料" and getattr(table, '_gasket_type_changing', False):
                            print(f"[DBG] 垫片联动: 垫片类型变化，清空垫片材料用户锁")
                            table._gasket_user_lock.pop(tgt_name, None)

                        # 执行强制覆盖
                        itx.setText("" if v is None else str(v))
                        itx.setData(ROLE_SRC, AUTO_TAG)
                        itx.setData(ROLE_SIG, cur_sig)
                        table._gasket_user_lock.pop(tgt_name, None)
                        print(f"[DBG] 垫片联动: 强制覆盖参数{tgt_name}为{v}")

                        # 如果这是最后一个垫片参数，清除变化状态
                        if tgt_name in ["垫片名义内径D1n", "垫片名义外径D2n"]:
                            # 检查所有垫片参数是否都已处理完成
                            gasket_params = ["垫片名义内径D1n", "垫片名义外径D2n", "环内径d1"]
                            processed_count = getattr(table, '_gasket_processed_count', 0) + 1
                            table._gasket_processed_count = processed_count

                            if processed_count >= len(gasket_params):
                                # 清除变化状态
                                table._gasket_type_changing = False
                                table._gasket_standard_changing = False
                                table._gasket_processed_count = 0
                                print(f"[DBG] 垫片联动: 所有垫片参数处理完成，清除变化状态")

                        return

                    # 强制 或 签名变更 → 覆盖并清锁
                    if force or (prev_sig != cur_sig):
                        itx.setText("" if v is None else str(v))
                        itx.setData(ROLE_SRC, AUTO_TAG)
                        itx.setData(ROLE_SIG, cur_sig)
                        table._gasket_user_lock.pop(tgt_name, None)
                        print(f"[DBG] 垫片联动: 强制覆盖参数{tgt_name}为{v}")
                        return

                    # 签名未变：弱值/自动 才覆盖
                    if (cur_txt in WEAK_VALS) or (src_tag == AUTO_TAG):
                        itx.setText("" if v is None else str(v))
                        itx.setData(ROLE_SRC, AUTO_TAG)
                        itx.setData(ROLE_SIG, cur_sig)

                # —— 写回 —— #
                if getattr(table, "_gasket_ui_guard", False):
                    return
                table._gasket_ui_guard = True
                table.blockSignals(True)
                try:
                    with FreezeUI(table):
                        if driver_changed:
                            _clear_gasket_locks_for(DIM_PARAMS)

                        if not spec.get("nonstd", True):
                            _set_by_spec(row_D2n, spec.get("外直径D"), force=driver_changed)
                            _set_by_spec(row_D1n, spec.get("内直径d"), force=driver_changed)
                            _set_by_spec(row_d1,  spec.get("环内径d1"), force=driver_changed)
                        else:
                            for rr in (row_D2n, row_D1n, row_d1):
                                _set_by_spec(rr, None, force=driver_changed)  # “程序推荐”

                        # 2.2 材料 / y / m 写回（按类型+标准）
                        if props:
                            # === 仅改“垫片材料”的下拉代理 + 变化时重置值 ===
                            mats = (props.get("垫片材料候选") or [])
                            if row_mat is not None:
                                _ensure_editable(row_mat)

                                # 安装下拉代理
                                table.setItemDelegateForRow(row_mat, ComboDelegate(mats, table))
                                txt_now = table.item(row_mat, value_col).text().strip() if table.item(row_mat, value_col) else ""
                                if driver_changed and (not txt_now) and len(mats) == 1:
                                    _set_by_spec(row_mat, mats[0], force=True)
                            _set_by_spec(row_y, props.get("垫片比压力y"), force=driver_changed)
                            _set_by_spec(row_m, props.get("垫片系数m"),   force=driver_changed)
                        else:
                            for rr in (row_mat, row_y, row_m):
                                _set_by_spec(rr, None, force=driver_changed)

                finally:
                    table.blockSignals(False)
                    table._gasket_ui_guard = False

                # 更新“上次签名”
                table._gasket_last_sig = cur_sig

                # 友好提示
                tip = getattr(viewer_instance, "line_tip", None)
                if tip:
                    tip.setStyleSheet("color:orange;" if spec.get("nonstd", True) else "color:;")
                    tip.setText("垫片尺寸将由程序推荐，用户可手动更改。" if spec.get("nonstd", True) else "")


        except Exception as e:
            print(f"[垫片联动] 计算失败：{e}")


        # ==== 显隐规则：每次值变化后再评估 ====
        try:
            ele_name = _current_element_name()
            if ele_name:
                effects = evaluate_visibility_rules_from_db(
                    ele_name, table=table, param_col=param_col, value_col=value_col, viewer_instance=viewer_instance
                )
                with FreezeUI(table):
                    for tgt_param, act in effects.items():
                        rr = find_row_by_param_name(table, tgt_param, param_col)
                        if rr is not None:
                            table.setRowHidden(rr, act == "HIDE")
        except Exception as e:
            print(f"[显隐规则-变更后评估失败] {e}")

    # 防重复绑定
    old_handler = getattr(table, "_covering_item_changed_handler", None)
    if old_handler is not None:
        try:
            table.itemChanged.disconnect(old_handler)
        except Exception:
            pass
    table.itemChanged.connect(_on_item_changed)
    table._covering_item_changed_handler = _on_item_changed

    # 5) 单击进入编辑
    def _edit_on_click(r, c):
        idx = table.model().index(r, c)
        it = table.item(r, c)
        if idx.isValid() and it and (it.flags() & Qt.ItemIsEditable):
            table.setCurrentIndex(idx); table.edit(idx)
    try:
        table.cellClicked.disconnect()
    except Exception:
        pass
    table.cellClicked.connect(_edit_on_click)

    # —— 首次渲染后，主动按库中外径带入一次 ——
    def _bootstrap_tierod_by_db():
        try:
            r_tierod = find_row_by_param_name(table, "拉杆型式", param_col)
            if r_tierod is None or not getattr(viewer_instance, "product_id", None):
                return
            od_txt = query_extra_param_value(viewer_instance.product_id, "换热管外径")
            import re
            s_num = "".join(re.findall(r"[-\d.]+", str(od_txt or "").strip()))
            od_val = float(s_num) if s_num else None
            if od_val is None:
                return
            target = "焊接拉杆" if od_val < 19.0 else "螺纹拉杆"
            if table.item(r_tierod, value_col) is None:
                it = QTableWidgetItem("")
                it.setTextAlignment(Qt.AlignCenter)
                it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                table.setItem(r_tierod, value_col, it)
            table.blockSignals(True)
            try:
                table.item(r_tierod, value_col).setText(target)
            finally:
                table.blockSignals(False)
            table._tierod_od_last = od_val  # 初始化缓存
        except Exception as e:
            print(f"[拉杆型式引导带入] 失败：{e}")

    QTimer.singleShot(0, _bootstrap_tierod_by_db)






from PyQt5.QtCore import Qt

def apply_linked_param_combobox(table, param_col, value_col, mapping):
    from PyQt5.QtWidgets import QTableWidgetItem, QAbstractItemView

    # ---- 小工具 ----
    def _ensure_editable_item(tbl, r, c):
        it = tbl.item(r, c)
        if it is None:
            it = QTableWidgetItem("")
            tbl.setItem(r, c, it)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        it.setTextAlignment(Qt.AlignCenter)
        return it

    def _get(r):
        it = table.item(r, value_col)
        return (it.text().strip() if it else "")

    def _set(r, txt):
        _ensure_editable_item(table, r, value_col)
        table.item(r, value_col).setText("" if txt is None else str(txt))

    # —— 名称同义词（统一以“垫片类型”为规范名）——
    _CANON = {
        "垫片型式": "垫片类型",
        "垫片类型": "垫片类型",
        "垫片结构形式代号": "垫片结构型式代号",
        "垫片结构式代号": "垫片结构型式代号",
        "垫片结构型式": "垫片结构型式代号",
        "垫片结构型式代号": "垫片结构型式代号",
        "垫片标准": "垫片标准",
    }
    _REV = {}
    for k, v in _CANON.items():
        _REV.setdefault(v, set()).add(k)

    def _canon(name: str) -> str:
        n = (name or "").strip()
        return _CANON.get(n, n)

    # —— 字段名 -> 行号（含别名注册）——
    name_to_row = {}
    def _register_row(label: str, row: int):
        raw = (label or "").strip()
        canon = _canon(raw)
        name_to_row[raw] = row
        name_to_row.setdefault(canon, row)
        for alias in _REV.get(canon, []):
            name_to_row.setdefault(alias, row)

    for r in range(table.rowCount()):
        it = table.item(r, param_col)
        if it and (it.text() or "").strip():
            _register_row(it.text(), r)

    def _row_of(field_name: str) -> int:
        if field_name in name_to_row:
            return name_to_row[field_name]
        cn = _canon(field_name)
        if cn in name_to_row:
            return name_to_row[cn]
        for k, r in name_to_row.items():
            if _canon(k) == cn:
                return r
        return -1

    # —— 收集单主映射 ——
    master_fields = [k for k in (mapping or {}).keys() if k != "_compound_rules"]
    dependent_fields_all = {}
    for mf in master_fields:
        deps = set()
        for _, submap in (mapping.get(mf, {}) or {}).items():
            deps.update((submap or {}).keys())
        dependent_fields_all[mf] = deps

    # —— 可编辑 ——
    for fname in set(master_fields) | set().union(*dependent_fields_all.values()):
        r = _row_of(fname)
        if r >= 0:
            if table.cellWidget(r, value_col):
                table.setCellWidget(r, value_col, None)
            _ensure_editable_item(table, r, value_col)

    table.setEditTriggers(QAbstractItemView.SelectedClicked)

    # —— 复合规则 ——
    rules = (mapping or {}).get("_compound_rules") or []
    compound_master_set = {_canon(n) for rule in rules for (n, _v) in (rule.get("masters") or [])}

    def _apply_compound_rules():
        if not rules:
            return
        for rule in rules:
            dep = _canon(rule.get("dependent", ""))
            r_dep = _row_of(dep)
            if r_dep < 0:
                continue
            masters_can = [(_canon(n), v) for (n, v) in (rule.get("masters") or [])]
            matched = all((_get(_row_of(n)) == v) for (n, v) in masters_can)
            if matched:
                # 去空/去重/保序
                seen, opts = set(), []
                for o in (rule.get("options") or []):
                    s = (o or "").strip()
                    if s and s not in seen:
                        seen.add(s); opts.append(s)
                table.setItemDelegateForRow(
                    r_dep, MaterialInstantDelegate(opts, table, field_name=dep, on_pick=None)
                )
                _set(r_dep, opts[0] if opts else "")

    # —— 安装被联动字段 ——
    def _install_dependent_delegate(sub_field, options, *, force_default=False, triggerable=False, preserve_current=True):
        r = _row_of(sub_field)
        if r < 0:
            return
        seen, opts = set(), []
        for o in (options or []):
            s = (o or "").strip()
            if s and s not in seen:
                seen.add(s); opts.append(s)

        def _cb(_field_name, new_text, _row, _col):
            _apply_compound_rules()

        need_cb = (_canon(sub_field) in compound_master_set)
        table.setItemDelegateForRow(
            r,
            MaterialInstantDelegate(opts, table, field_name=sub_field,
                                    on_pick=_cb if (need_cb or triggerable) else None)
        )

        # 处理值设置逻辑
        if force_default and not preserve_current:
            # 强制设置默认值
            _set(r, opts[0] if opts else "")
        elif preserve_current and not force_default:
            # 保持当前值，仅在当前值在选项中时才保持
            current_val = _get(r)  # 获取当前值
            if current_val in opts:
                _set(r, current_val)  # 保持当前值
            elif opts:
                _set(r, opts[0] if opts else "")  # 设置为第一个选项
        elif force_default and preserve_current:
            # 既有强制又有保持，优先强制设置默认值
            _set(r, opts[0] if opts else "")
        else:
            # 不设置值，保持原有状态
            pass

    # —— 安装主字段 ——
    def _install_master_delegate(master_field):
        r_master = _row_of(master_field)
        if r_master < 0:
            return

        saved = _get(r_master)
        base_opts = list((mapping.get(master_field) or {}).keys())
        if saved and (saved not in base_opts):
            base_opts = base_opts + [saved]

        def on_master_pick(_field_name, new_text, _row, _col):
            if not (new_text or "").strip():
                return
            submap = (mapping.get(master_field, {}) or {}).get(new_text, {}) or {}
            is_gasket_master = (_canon(master_field) == "垫片类型")
            master_type_changed = (saved != new_text)  # 检查垫片类型是否真的变化了

            # 垫片类型的特殊处理：检查全局变化状态
            if is_gasket_master:
                global_type_changed = getattr(table, '_gasket_type_changing', False)
                # 如果有全局变化状态，或者是文本变化，都认为类型变化了
                actual_type_changed = master_type_changed or global_type_changed
                master_type_changed = actual_type_changed
                print(f"[DBG] 垫片标准联动: 垫片类型'{master_field}'从'{saved}'变更为'{new_text}', 文本变化={saved != new_text}, 全局变化={global_type_changed}, 实际变化={actual_type_changed}")

            for sub_field in dependent_fields_all.get(master_field, []):
                opts = submap.get(sub_field, [])

                if is_gasket_master and _canon(sub_field) == "垫片标准":
                    # 垫片标准的特殊处理逻辑
                    r_standard = _row_of(sub_field)  # 找到垫片标准行

                    if master_type_changed:
                        # 垫片类型发生变化：先清空，再使用默认值（第一个选项）
                        _set(r_standard, "")  # 先清空当前值
                        _install_dependent_delegate(sub_field, opts, force_default=True, preserve_current=False)
                        print(f"[DBG] 垫片联动: 垫片类型变化，垫片标准已清空并设置为默认值: {opts[0] if opts else '无选项'}")
                    else:
                        # 垫片类型没有变化：使用保存的垫片标准值，绝对不碰默认值
                        _install_dependent_delegate(sub_field, opts, force_default=False, preserve_current=True)
                else:
                    # 其他依赖字段的常规处理
                    _install_dependent_delegate(sub_field, opts, force_default=False)

            _apply_compound_rules()
            table.viewport().update()

        table.setItemDelegateForRow(
            r_master,
            MaterialInstantDelegate(base_opts, table, field_name=master_field, on_pick=on_master_pick)
        )
        if saved:
            on_master_pick(master_field, saved, r_master, value_col)

    for mf in master_fields:
        _install_master_delegate(mf)

    _apply_compound_rules()














def apply_gk_paramname_combobox(table, param_col, value_col, component_info=None, viewer_instance=None):
    field_widgets = {}
    positive_float_params = {"焊缝金属截面积", "管程接管腐蚀裕量", "壳程接管腐蚀裕量", "覆层厚度"}
    toggle_cover_dependent_fields = [
        "覆层材料类型", "覆层材料牌号", "覆层材料级别",
        "覆层材料标准", "覆层成型工艺", "覆层使用状态", "覆层厚度"
    ]

    for row in range(table.rowCount()):
        try:
            param_item = table.item(row, param_col)
            param_name = param_item.text().strip() if param_item else ""

            value_item = table.item(row, value_col)
            current_value = value_item.text().strip() if value_item else ""

            # 处理是否添加覆层
            if param_name == "是否添加覆层":
                combo = QComboBox()
                combo.addItems(["是", "否"])
                combo.setEditable(True)
                combo.setCurrentText("是" if current_value == "是" else "否")
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox { border: none; background-color: transparent; font-size: 9pt; font-family: "Microsoft YaHei"; padding-left: 2px; }
                """)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)

                # ✅ 直接把当前 component_info 存入 combo 属性
                combo.component_info = component_info
                combo.viewer_instance = viewer_instance

                # ✅ 定义信号槽时，取 combo 内部绑定的 component_info
                def on_cover_changed(value, combo_ref=combo):
                    ci = getattr(combo_ref, "component_info", None)
                    viewer = getattr(combo_ref, "viewer_instance", None)
                    has_covering = (value.strip() == "是")

                    for r in range(table.rowCount()):
                        pitem = table.item(r, param_col)
                        if not pitem:
                            continue
                        pname = pitem.text().strip()
                        if pname in toggle_cover_dependent_fields:
                            table.setRowHidden(r, not has_covering)

                            # ✅ 仅在隐藏行时清空控件内的值，保留控件
                            if not has_covering:
                                widget = table.cellWidget(r, value_col)
                                if isinstance(widget, QLineEdit):
                                    widget.clear()
                                elif isinstance(widget, QComboBox):
                                    widget.setCurrentIndex(0)  # 置为空白项（第一项）
                                    widget.setCurrentText("")  # 保险起见再清空显示文本

                    # 刷新图片逻辑
                    if ci and viewer:
                        template_name = ci.get("模板名称")
                        template_id = query_template_id(template_name) if template_name else ci.get("模板ID")
                        element_id = ci.get("管口零件ID")
                        if template_id and element_id:
                            image_path = query_guankou_image_from_database(template_id, element_id, has_covering)
                            if image_path:
                                viewer.display_image(image_path)

                # 初始化 & 绑定信号
                on_cover_changed(combo.currentText())
                combo.currentTextChanged.connect(on_cover_changed)

                continue

            # 处理覆层材料类型及其联动
            if param_name == "覆层材料类型":
                options = get_options_for_param(param_name) or []
                combo = QComboBox()
                combo.addItem("")
                combo.addItems(options)
                combo.setEditable(True)
                combo.setCurrentText(current_value)
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox { border: none; background-color: transparent; font-size: 9pt; font-family: "Microsoft YaHei"; padding-left: 2px; }
                """)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)
                field_widgets["覆层材料类型"] = combo

                def on_material_type_changed(index, c=combo):
                    value = c.currentText().strip()
                    cover_value = ""
                    for rr in range(table.rowCount()):
                        item = table.item(rr, param_col)
                        if item and item.text().strip() == "是否添加覆层":
                            widget = table.cellWidget(rr, value_col)
                            if isinstance(widget, QComboBox):
                                cover_value = widget.currentText().strip()
                            break

                    # 控制“覆层材料级别”和“覆层使用状态”的显示
                    for r in range(table.rowCount()):
                        pitem = table.item(r, param_col)
                        if not pitem:
                            continue
                        pname = pitem.text().strip()
                        if pname == "覆层材料级别":
                            table.setRowHidden(r, not (cover_value == "是" and value == "钢板"))
                        if pname == "覆层使用状态":
                            table.setRowHidden(r, not (cover_value == "是" and value == "钢板"))

                    # ✅ 更新覆层成型工艺的下拉内容
                    if "覆层成型工艺" in field_widgets and cover_value == "是":
                        combo_widget = field_widgets["覆层成型工艺"]
                        combo_widget.blockSignals(True)
                        combo_widget.clear()
                        combo_widget.addItem("")
                        if value == "钢板":
                            combo_widget.addItems(["轧制复合", "爆炸焊接"])
                            combo_widget.setCurrentText("爆炸焊接")
                        elif value == "焊材":
                            combo_widget.addItem("堆焊")
                            combo_widget.setCurrentText("堆焊")
                        else:
                            combo_widget.setCurrentText("")
                        combo_widget.blockSignals(False)

                combo.currentIndexChanged.connect(on_material_type_changed)
                QTimer.singleShot(0, lambda: on_material_type_changed(combo.currentIndex()))
                continue

            # 处理覆层成型工艺
            if param_name == "覆层成型工艺":
                combo = QComboBox()
                combo.setEditable(True)
                combo.setInsertPolicy(QComboBox.NoInsert)
                combo.addItem("")  # 添加空项，避免空下拉无法点击

                # ✅ 根据 current_value 判断初始化选项
                if current_value == "爆炸焊接":
                    combo.addItems(["轧制复合", "爆炸焊接"])
                elif current_value == "堆焊":
                    combo.addItem("堆焊")

                # ✅ 设置当前值（确保显示）
                combo.setCurrentText(current_value)

                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox {
                        border: none;
                        background-color: transparent;
                        font-size: 9pt;
                        font-family: "Microsoft YaHei";
                        padding-left: 2px;
                    }
                """)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)
                field_widgets["覆层成型工艺"] = combo
                continue

            # 处理一般正浮点数
            if param_name in positive_float_params:
                line_edit = QLineEdit()
                line_edit.setText(current_value)
                line_edit.setAlignment(Qt.AlignCenter)
                line_edit.setStyleSheet("""
                    QLineEdit { border: none; font-size: 9pt; font-family: "Microsoft YaHei"; }
                """)

                def validate(le=line_edit, pname=param_name, r=row, tip=viewer_instance.line_tip):
                    try:
                        val = float(le.text().strip())
                        if val < 0 or (pname == "焊缝金属截面积" and val == 0):
                            raise ValueError
                        tip.setText("")  # 输入合法时清空提示
                    except:
                        tip.setText(f"第 {r + 1} 行参数“{pname}”输入值不合法")
                        tip.setStyleSheet("color: red;")
                        le.setText("")

                line_edit.editingFinished.connect(validate)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, line_edit)
                continue

            # 其他通用下拉
            options = get_options_for_param(param_name)
            if options:
                combo = QComboBox()
                combo.addItem("")
                combo.addItems(options)
                combo.setEditable(True)
                combo.setCurrentText(current_value)
                combo.lineEdit().setAlignment(Qt.AlignCenter)
                combo.setStyleSheet("""
                    QComboBox { border: none; background-color: transparent; font-size: 9pt; font-family: "Microsoft YaHei"; padding-left: 2px; }
                """)
                table.setItem(row, value_col, None)
                table.setCellWidget(row, value_col, combo)

        except Exception as e:
            print(f"[接管参数处理失败] 第{row}行 参数名: {param_name}，错误: {e}")



def sync_component_params_to_buguan(table_widget, product_id):
    """
    将元件参数定义表中的部分参数同步到布管参数表
    """

    #元件参数-->布管参数
    MAPPING_DICT = {
        "换热管外径": "换热管外径 do",
        "防冲板形式": "防冲板形式",
        "防冲板厚度": "防冲板厚度",
        "防冲板折边角度": "防冲板折边角度",
        "滑道定位": "滑道定位",
        "滑道高度": "滑道高度",
        "滑道厚度": "滑道厚度",
        "滑道与竖直中心线夹角": "滑道与竖直中心线夹角",
        "中间挡板厚度":"中间挡板厚度",
        "中间挡板宽度":"中间挡板宽度",
        "旁路挡板厚度": "旁路挡板厚度",
        "旁路挡板宽度": "旁路挡板宽度",
    }
    try:
        conn = get_connection("localhost", 3306, "root", "123456", "产品设计活动库")
        with conn.cursor() as cursor:
            for row in range(table_widget.rowCount()):
                name_item = table_widget.item(row, 0)  # 假设第0列是 参数名称
                value_item = table_widget.item(row, 1) # 假设第1列是 参数值

                if not name_item or not value_item:
                    continue

                param_name = name_item.text().strip()
                param_value = value_item.text().strip()

                if param_name in MAPPING_DICT:
                    mapped_name = MAPPING_DICT[param_name]

                    cursor.execute("""
                        UPDATE 产品设计活动表_布管参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 参数名=%s
                    """, (param_value, product_id, mapped_name))

        conn.commit()
        print("[布管参数同步] 成功")
    except Exception as e:
        print(f"[布管参数同步] 失败: {e}")
    finally:
        conn.close()


def query_template_element_merged_para_data(template_id, element_id):
    """从材料库查询元件附加参数合并表模板数据"""
    print(f"[调试] 查询参数: template_id={template_id}, element_id={element_id}")
    
    connection = get_connection(**db_config_2)
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                元件ID,
                参数名称,
                参数值,
                参数单位,
                Tab分类,
                模板ID
            FROM 元件附加参数合并表
            WHERE 模板ID = %s AND 元件ID = %s
            ORDER BY Tab分类, 参数名称
            """
            cursor.execute(sql, (template_id, element_id))
            result = cursor.fetchall()
            print(f"[调试] 查询结果: {len(result)} 条数据")
            
            # 打印原始数据以调试
            for i, row in enumerate(result):
                print(f"[调试] 原始数据 {i+1}: {row}")
                print(f"[调试] 原始数据字段: 元件ID={row.get('元件ID')}, 参数名称={row.get('参数名称')}, 参数值={row.get('参数值')}, 参数单位={row.get('参数单位')}")
            
            # 转换数据结构 - 直接使用字段名
            converted_result = []
            for row in result:
                # 直接使用字段名进行映射
                converted_row = {
                    '元件ID': row['元件ID'],
                    '参数名称': row['参数名称'],
                    '参数值': row['参数值'],
                    '参数单位': row['参数单位'] or '',
                    'Tab分类': row['Tab分类'] or 'PNO.1',
                    '模板ID': row['模板ID']
                }
                converted_result.append(converted_row)
                print(f"[调试] 转换后数据: {converted_row}")
                print(f"[调试] 转换后字段: 元件ID={converted_row['元件ID']}, 参数名称={converted_row['参数名称']}, 参数值={converted_row['参数值']}")
                
                # 验证数据是否正确
                if converted_row['参数名称'] == converted_row['参数值']:
                    print(f"[警告] 参数名称和参数值相同，可能数据有问题！")
                if not converted_row['参数名称'] and converted_row['参数值']:
                    print(f"[警告] 参数名称为空但参数值有值，可能字段映射错误！")
            
            return converted_result
    finally:
        connection.close()


def insert_or_update_element_merged_para_data(product_id, element_id, merged_para_info, template_name):
    """将元件附加参数合并表数据插入到产品活动库"""
    if not merged_para_info:
        print(f"[元件附加参数合并表] 元件 {element_id} 没有附加参数数据，跳过插入")
        return
        
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            # 先删除该元件的现有数据
            cursor.execute("""
                DELETE FROM 产品设计活动表_元件附加参数合并表 
                WHERE 产品ID = %s AND 元件ID = %s
            """, (product_id, element_id))
            
            # 按Tab分类分组数据，为每个Tab生成唯一的Tab_ID
            tab_groups = {}
            for item in merged_para_info:
                tab_name = item.get('Tab分类', 'PNO.1')
                if tab_name not in tab_groups:
                    tab_groups[tab_name] = []
                tab_groups[tab_name].append(item)
            
            # 为每个Tab生成Tab_ID并插入数据
            insert_count = 0
            for tab_name, tab_items in tab_groups.items():
                # 为当前Tab生成唯一的Tab_ID
                tab_id = generate_unique_tab_id()
                print(f"[元件附加参数合并表] Tab {tab_name} 生成Tab_ID: {tab_id}")
                
                for item in tab_items:
                    param_name = item.get('参数名称', '')
                    param_value = item.get('参数值', '')
                    
                    print(f"[调试] 准备插入数据: {item}")
                    print(f"[调试] 插入字段: 参数名称='{param_name}', 参数值='{param_value}', Tab_ID='{tab_id}'")
                    
                    # 验证数据是否正确
                    if not param_name and param_value:
                        print(f"[错误] 参数名称为空但参数值有值: '{param_value}'")
                    if param_name and not param_value:
                        print(f"[错误] 参数名称有值但参数值为空: '{param_name}'")
                    if param_name == param_value:
                        print(f"[错误] 参数名称和参数值相同: '{param_name}'")
                    
                    cursor.execute("""
                        INSERT INTO 产品设计活动表_元件附加参数合并表 
                        (产品ID, 元件ID, 参数名称, 参数值, 参数单位, Tab分类, Tab_ID, 模板名称, 模板ID)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        product_id,
                        element_id,
                        param_name,
                        param_value,
                        item.get('参数单位', ''),
                        tab_name,
                        tab_id,
                        template_name,
                        item.get('模板ID')
                    ))
                    insert_count += 1
                
            connection.commit()
            print(f"[元件附加参数合并表] 成功插入 {insert_count} 条 {element_id} 的附加参数数据")
            
    except Exception as e:
        print(f"[元件附加参数合并表] 插入失败: {e}")
        connection.rollback()
    finally:
        connection.close()


def get_template_merged_para_element_ids(template_id):
    """获取模板中所有有附加参数合并表的元件ID列表"""
    connection = get_connection(**db_config_2)
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT DISTINCT 元件ID 
            FROM 元件附加参数合并表 
            WHERE 模板ID = %s
            """
            cursor.execute(sql, (template_id,))
            result = cursor.fetchall()
            element_ids = [row['元件ID'] for row in result]
            print(f"[调试] 找到元件ID列表: {element_ids}")
            return element_ids
    finally:
        connection.close()


def batch_insert_element_merged_para_data(product_id, template_id, template_name):
    """批量处理模板中所有有附加参数合并表的元件"""
    print(f"[调试] 开始批量处理: product_id={product_id}, template_id={template_id}")
    
    # 获取所有需要处理的元件ID
    element_ids = get_template_merged_para_element_ids(template_id)
    
    if not element_ids:
        print(f"[批量处理] 模板 {template_id} 没有找到需要处理的元件")
        return
        
    print(f"[批量处理] 开始处理 {len(element_ids)} 个元件的附加参数合并表数据: {element_ids}")
    
    for element_id in element_ids:
        try:
            print(f"[调试] 处理元件: {element_id}")
            # 查询该元件的附加参数合并表数据
            merged_para_info = query_template_element_merged_para_data(template_id, element_id)
            print(f"[调试] 查询到 {len(merged_para_info)} 条数据")
            
            # 插入到产品活动库
            insert_or_update_element_merged_para_data(product_id, element_id, merged_para_info, template_name)
            
        except Exception as e:
            print(f"[批量处理] 处理元件 {element_id} 失败: {e}")
            continue
    
    print(f"[批量处理] 完成所有元件的附加参数合并表数据处理")


def load_fixed_saddle_data_by_tab(product_id, element_id, tab_name):
    """从产品活动库加载指定Tab页的固定鞍座数据"""
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                参数名称,
                参数值,
                参数单位,
                Tab分类,
                Tab_ID,
                模板名称,
                模板ID
            FROM 产品设计活动表_元件附加参数合并表
            WHERE 产品ID = %s AND 元件ID = %s AND Tab分类 = %s
            ORDER BY Tab_ID, 参数名称
            """
            cursor.execute(sql, (product_id, element_id, tab_name))
            result = cursor.fetchall()
            print(f"[固定鞍座] Tab页 {tab_name} 加载数据: {len(result)} 条")
            return result
    finally:
        connection.close()


def load_fixed_saddle_data_by_product(product_id, element_id):
    """从产品活动库加载固定鞍座附加参数数据"""
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT 
                参数名称,
                参数值,
                参数单位,
                Tab分类
            FROM 产品设计活动表_元件附加参数合并表
            WHERE 产品ID = %s AND 元件ID = %s
            ORDER BY Tab分类, 参数名称
            """
            cursor.execute(sql, (product_id, element_id))
            result = cursor.fetchall()
            print(f"[固定鞍座] 加载数据: {len(result)} 条")
            return result
    finally:
        connection.close()


def sync_fixed_saddle_param_across_tabs(viewer_instance, product_id, tab_name):
    """同步固定鞍座关键参数到所有Tab页"""
    # 需要同步的参数列表
    sync_params = ["支座型式", "支座标准", "支座型号", "鞍座高度"]
    
    try:
        element_id = 29  # 固定鞍座的元件ID
        
        print(f"[固定鞍座参数同步] 开始同步参数: product={product_id}, tab={tab_name}")
        
        # 从当前Tab页获取关键参数的值
        current_tab_data = load_fixed_saddle_data_by_tab(product_id, element_id, tab_name)
        sync_values = {}
        
        for item in current_tab_data:
            param_name = item.get('参数名称', '')
            if param_name in sync_params:
                sync_values[param_name] = item.get('参数值', '')
        
        print(f"[固定鞍座参数同步] 当前Tab页关键参数值: {sync_values}")
        
        # 检查是否支座型式发生了改变
        old_support_type = None
        new_support_type = sync_values.get('支座型式', '')
        
        # 更新数据库中所有Tab页的这些参数
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                # 获取旧的支座型式值进行比较
                cursor.execute("""
                    SELECT 参数值 FROM 产品设计活动表_元件附加参数合并表 
                    WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '支座型式' 
                    AND Tab分类 != %s LIMIT 1
                """, (product_id, element_id, tab_name))
                result = cursor.fetchone()
                if result:
                    old_support_type = result.get('参数值', '')
                
                # 更新数据库中所有Tab页的这些参数
                for param_name, param_value in sync_values.items():
                    cursor.execute("""
                        UPDATE 产品设计活动表_元件附加参数合并表 
                        SET 参数值 = %s
                        WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = %s
                    """, (param_value, product_id, element_id, param_name))
                    
                    updated_count = cursor.rowcount
                    print(f"[固定鞍座参数同步] {param_name}={param_value} 更新了 {updated_count} 条记录")
                
                # 如果支座型式发生了改变，需要验证和清空无效的元件名称选择
                if old_support_type and old_support_type != new_support_type:
                    print(f"[固定鞍座参数同步] 支座型式改变: {old_support_type} -> {new_support_type}")
                    validate_and_clear_invalid_component_names(connection, product_id, element_id, new_support_type)
                
                connection.commit()
                print(f"[固定鞍座参数同步] 数据库更新完成")
                
        finally:
            connection.close()
        
        # 刷新所有Tab页的UI显示
        if hasattr(viewer_instance, 'dynamic_fixed_saddle_tabs'):
            for tab_name, table in viewer_instance.dynamic_fixed_saddle_tabs.items():
                try:
                    # 重新加载该Tab页的数据并刷新UI
                    tab_data = load_fixed_saddle_data_by_tab(product_id, element_id, tab_name)
                    render_fixed_saddle_table_data(table, tab_data)
                    
                    # 在应用下拉框之前，确保元件名称单元格显示正确的值
                    for row in range(table.rowCount()):
                        pitem = table.item(row, 0)
                        if pitem and pitem.text().strip() == "元件名称":
                            # 从数据库数据中获取正确的元件名称值
                            for item in tab_data:
                                if item.get('参数名称') == '元件名称':
                                    param_value = item.get('参数值', '')
                                    if param_value and str(param_value).startswith("[") and str(param_value).endswith("]"):
                                        try:
                                            import json
                                            parsed_options = json.loads(str(param_value))
                                            if parsed_options:
                                                display_value = "、".join(parsed_options)
                                                table.item(row, 1).setText(display_value)
                                                print(f"[固定鞍座参数同步] 设置元件名称显示值: {param_value} -> {display_value}")
                                            else:
                                                table.item(row, 1).setText("")
                                                print(f"[固定鞍座参数同步] 清空元件名称显示值")
                                        except json.JSONDecodeError:
                                            table.item(row, 1).setText(str(param_value))
                                    else:
                                        table.item(row, 1).setText(str(param_value))
                                    break
                            break
                    
                    apply_fixed_saddle_paramname_combobox(table, 0, 1, viewer_instance, tab_data)
                    print(f"[固定鞍座参数同步] Tab {tab_name} UI刷新完成")
                except Exception as e:
                    print(f"[固定鞍座参数同步] Tab {tab_name} UI刷新失败: {e}")
        
        print(f"[固定鞍座参数同步] 同步完成: product={product_id}")
        
    except Exception as e:
        print(f"[固定鞍座参数同步] 同步失败: {e}")
        import traceback
        traceback.print_exc()


def validate_and_clear_invalid_component_names(connection, product_id, element_id, new_support_type):
    """验证和清空无效的元件名称选择"""
    try:
        from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_2
        from modules.cailiaodingyi.db_cnt import get_connection as get_connection_2
        
        print(f"[元件名称验证] 开始验证支座型式: {new_support_type}")
        
        # 获取新支座型式下的有效元件名称候选值
        conn2 = get_connection_2(**db_config_2)
        try:
            with conn2.cursor() as cur:
                sql = """
                    SELECT 联动选项 
                    FROM 法兰参数联动表 
                    WHERE 主参数名称 = %s AND 主参数值 = %s AND 被联动参数名称 = %s
                """
                cur.execute(sql, ("支座型式", new_support_type, "元件名称"))
                result = cur.fetchone()
                
                valid_component_names = []
                if result and result["联动选项"]:
                    raw_text = result["联动选项"].strip()
                    try:
                        import json
                        valid_component_names = json.loads(raw_text)
                        print(f"[元件名称验证] 新支座型式有效候选值: {valid_component_names}")
                    except json.JSONDecodeError:
                        valid_component_names = [x.strip() for x in raw_text.split(",") if x.strip()]
                        print(f"[元件名称验证] 新支座型式有效候选值(逗号分割): {valid_component_names}")
        finally:
            conn2.close()
        
        # 查询所有Tab页的元件名称选择
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT Tab分类, 参数值
                FROM 产品设计活动表_元件附加参数合并表
                WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '元件名称'
                AND 参数值 != '' AND 参数值 != '[]'
            """, (product_id, element_id))
            results = cursor.fetchall()
            
            for row in results:
                tab_name = row.get('Tab分类', '')
                param_value = row.get('参数值', '')
                
                if not param_value:
                    continue
                
                # 解析当前选择的元件名称
                current_selected = []
                try:
                    import json
                    current_selected = json.loads(param_value)
                except json.JSONDecodeError:
                    current_selected = [x.strip() for x in param_value.split('、') if x.strip()]
                
                # 检查哪些选择是无效的
                valid_selected = [name for name in current_selected if name in valid_component_names]
                invalid_selected = [name for name in current_selected if name not in valid_component_names]
                
                print(f"[元件名称验证] Tab {tab_name} 当前选择: {current_selected}")
                print(f"[元件名称验证] Tab {tab_name} 新候选值: {valid_component_names}")
                print(f"[元件名称验证] Tab {tab_name} 有效选择: {valid_selected}")
                print(f"[元件名称验证] Tab {tab_name} 无效选择: {invalid_selected}")
                
                # 只有当有无效选择时才更新数据库
                if invalid_selected:
                    # 更新数据库，只保留用户实际选择的有效项
                    if valid_selected:
                        new_value = json.dumps(valid_selected, ensure_ascii=False)
                    else:
                        new_value = '[]'
                    
                    cursor.execute("""
                        UPDATE 产品设计活动表_元件附加参数合并表 
                        SET 参数值 = %s
                        WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '元件名称' AND Tab分类 = %s
                    """, (new_value, product_id, element_id, tab_name))
                    
                    print(f"[元件名称验证] Tab {tab_name} 已更新为: {new_value}")
                else:
                    print(f"[元件名称验证] Tab {tab_name} 所有选择都有效，无需更新")
        
        print(f"[元件名称验证] 验证完成")
        
    except Exception as e:
        print(f"[元件名称验证] 验证失败: {e}")
        import traceback
        traceback.print_exc()


def on_clear_fixed_saddle_param_update(viewer_instance):
    """
    安全清空固定鞍座参数表格，并同步数据库
    """
    from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem
    
    # 1) 询问确认 —— 使用标准信息样式的确认框
    table = getattr(viewer_instance, "tabWidget_2", None)
    if table is None:
        return

    box = QMessageBox(QMessageBox.Information, "清空确认",
                      "清空后不可撤销，是否继续？",
                      QMessageBox.NoButton, table)
    btn_ok = box.addButton("确认", QMessageBox.YesRole)
    btn_cancel = box.addButton("取消", QMessageBox.NoRole)
    box.setDefaultButton(btn_cancel)  # 默认光标在"取消"，更安全
    box.exec_()
    if box.clickedButton() is not btn_ok:
        print("[固定鞍座清空] 用户取消操作")
        return

    # 2) 当前 Tab / 表
    tw = getattr(viewer_instance, "tabWidget_2", None)
    if tw is None or tw.currentIndex() < 0:
        print("[固定鞍座清空] 无法定位当前固定鞍座Tab")
        return
    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()
    
    # 获取当前Tab页的参数表
    current_page = tw.widget(cur_idx)
    table_param = current_page.property('param_table') if current_page else None
    
    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return

    # 3) UI 清空（不销毁委托/控件，只清文本）
    preserved_params = set()  # 固定鞍座没有需要保留的参数
    table_param.blockSignals(True)
    try:
        for r in range(table_param.rowCount()):
            it0 = table_param.item(r, 0)
            label_ui = it0.text().strip() if it0 else ""
            if not label_ui:
                continue

            # 单值行：清空参数值
            v = "" if label_ui not in preserved_params else "否"
            it = table_param.item(r, 1)
            if it:
                it.setText(v)
            else:
                table_param.setItem(r, 1, QTableWidgetItem(v))
    finally:
        table_param.blockSignals(False)

    # 4) DB 批量清空
    try:
        clear_fixed_saddle_params_for_tab(
            viewer_instance, table_param,
            viewer_instance.product_id, tab_name,
            preserved_params=preserved_params
        )
    except Exception as e:
        print("[固定鞍座数据库错误] 清空固定鞍座参数失败：", e)

    print(f"[固定鞍座清空] Tab {tab_name} 清空完成")


def clear_fixed_saddle_params_for_tab(viewer_instance, table, product_id, tab_name, preserved_params=None):
    """清空固定鞍座Tab页的参数数据（更新参数值为空，不删除记录）"""
    if preserved_params is None:
        preserved_params = set()
    
    try:
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                # 更新指定Tab页的所有参数值为空字符串（保留记录结构）
                cursor.execute("""
                    UPDATE 产品设计活动表_元件附加参数合并表
                    SET 参数值 = ''
                    WHERE 产品ID = %s AND Tab分类 = %s
                """, (product_id, tab_name))
                
                updated_count = cursor.rowcount
                connection.commit()
                print(f"[固定鞍座清空] 数据库清空完成: {updated_count} 条记录（参数值已清空）")
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"[固定鞍座清空] 数据库清空失败: {e}")
        raise


def update_fixed_saddle_param_in_db(product_id, element_id, param_name, param_value, tab_name):
    """更新固定鞍座单个参数到数据库"""
    try:
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                # 先查询是否存在该记录
                cursor.execute("""
                    SELECT 参数值, Tab_ID FROM 产品设计活动表_元件附加参数合并表
                    WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = %s AND Tab分类 = %s
                """, (product_id, element_id, param_name, tab_name))
                
                existing_record = cursor.fetchone()
                print(f"[固定鞍座参数更新] 查询现有记录: {param_name} -> {existing_record}")
                
                if existing_record:
                    # 更新现有记录
                    cursor.execute("""
                        UPDATE 产品设计活动表_元件附加参数合并表
                        SET 参数值 = %s
                        WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = %s AND Tab分类 = %s
                    """, (param_value, product_id, element_id, param_name, tab_name))
                    
                    updated_count = cursor.rowcount
                    connection.commit()
                    print(f"[固定鞍座参数更新] {param_name}={param_value} 更新了 {updated_count} 条记录")
                else:
                    print(f"[固定鞍座参数更新] 未找到现有记录，跳过更新: {param_name}")
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"[固定鞍座参数更新] 失败: {e}")
        raise


def update_fixed_saddle_tab_data_from_table(table_param, product_id, element_id, tab_name):
    """更新固定鞍座Tab页的所有参数到数据库"""
    # 需要更新的所有参数
    update_params = [
        "支座型式", "支座标准", "支座型号", "鞍座高度", "腐蚀裕量",
        "元件名称", "材料类型", "材料牌号", "材料标准", "供货状态"
    ]
    
    try:
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                for param_name in update_params:
                    # 在表格中查找对应的参数行
                    param_value = ""
                    param_unit = ""
                    
                    for r in range(table_param.rowCount()):
                        it0 = table_param.item(r, 0)
                        if it0 and it0.text().strip() == param_name:
                            # 获取参数值
                            it1 = table_param.item(r, 1)
                            if it1:
                                param_value = it1.text().strip()
                            
                            # 获取参数单位
                            it2 = table_param.item(r, 2)
                            if it2:
                                param_unit = it2.text().strip()
                            break
                    
                    # 对元件名称进行特殊处理：确保保持JSON格式
                    if param_name == "元件名称":
                        if not param_value or param_value.strip() == "":
                            # 如果表格中的值是空的，保持数据库中的空JSON数组格式
                            param_value = "[]"
                        elif not param_value.startswith("[") or not param_value.endswith("]"):
                            # 如果不是JSON格式，尝试转换为JSON格式
                            try:
                                import json
                                # 如果是用"、"分隔的字符串，转换为JSON数组
                                if "、" in param_value:
                                    options = [x.strip() for x in param_value.split("、") if x.strip()]
                                    param_value = json.dumps(options, ensure_ascii=False)
                                    print(f"[固定鞍座Tab更新] 元件名称格式转换: {param_value} -> {param_value}")
                                else:
                                    # 其他情况，保持原值
                                    pass
                            except Exception as e:
                                # 转换失败，保持原值
                                print(f"[固定鞍座Tab更新] 元件名称格式转换失败: {e}")
                                pass
                    
                    # 更新数据库中的参数值
                    cursor.execute("""
                        UPDATE 产品设计活动表_元件附加参数合并表
                        SET 参数值 = %s, 参数单位 = %s
                        WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = %s AND Tab分类 = %s
                    """, (param_value, param_unit, product_id, element_id, param_name, tab_name))
                    
                    updated_count = cursor.rowcount
                    print(f"[固定鞍座Tab更新] {param_name}={param_value} 更新了 {updated_count} 条记录")
                
                connection.commit()
                print(f"[固定鞍座Tab更新] Tab {tab_name} 所有参数更新完成")
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"[固定鞍座Tab更新] 失败: {e}")
        raise


def extract_fixed_saddle_data_from_table(table_param, product_id, tab_name):
    """从固定鞍座表格中提取数据"""
    data = []
    
    # 定义参数顺序
    display_params = [
        "支座型式", "支座标准", "支座型号", "鞍座高度", "腐蚀裕量",
        "元件名称", "材料类型", "材料牌号", "材料标准", "供货状态"
    ]
    
    for param_name in display_params:
        # 在表格中查找对应的参数行
        param_value = ""
        param_unit = ""
        
        for r in range(table_param.rowCount()):
            it0 = table_param.item(r, 0)
            if it0 and it0.text().strip() == param_name:
                # 获取参数值
                it1 = table_param.item(r, 1)
                if it1:
                    param_value = it1.text().strip()
                
                # 获取参数单位
                it2 = table_param.item(r, 2)
                if it2:
                    param_unit = it2.text().strip()
                break
        
        # 构建数据项
        data_item = {
            "产品ID": product_id,
            "元件ID": 29,
            "参数名称": param_name,
            "参数值": param_value,
            "参数单位": param_unit,
            "Tab分类": tab_name,
            "模板名称": "",
            "模板ID": 0,
            "Tab_ID": generate_unique_tab_id()
        }
        data.append(data_item)
    
    print(f"[固定鞍座] 从表格提取数据: {len(data)} 条")
    return data


def on_confirm_fixed_saddle_param(viewer_instance):
    """固定鞍座确定按钮处理"""
    print("点击了固定鞍座确定按钮")
    
    # 获取当前Tab页
    tw = getattr(viewer_instance, "tabWidget_2", None)
    if tw is None:
        print("[固定鞍座确定] 未找到tabWidget_2")
        return
    
    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()
    
    # 获取当前Tab页的表格
    table_param = None
    if hasattr(viewer_instance, "dynamic_fixed_saddle_tabs"):
        table_param = viewer_instance.dynamic_fixed_saddle_tabs.get(tab_name)
    
    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return
    
    product_id = getattr(viewer_instance, "product_id", None)
    if not product_id:
        QMessageBox.warning(viewer_instance, "错误", "未找到产品ID")
        return
    
    try:
        # 1) 先保存当前Tab页的所有参数到数据库
        element_id = 29  # 固定鞍座的元件ID
        update_fixed_saddle_tab_data_from_table(table_param, product_id, element_id, tab_name)
        print(f"[固定鞍座确定] 已保存 {tab_name} 的所有参数到数据库")
        
        # 2) 强制提交数据库事务
        if hasattr(viewer_instance, "force_commit"):
            viewer_instance.force_commit()
            print("[固定鞍座确定] 已执行 force_commit()")
        
        # 3) 同步关键参数到其他Tab页
        try:
            print(f"[固定鞍座确定] 开始同步关键参数到其他Tab页: product={product_id}, tab={tab_name}")
            sync_fixed_saddle_param_across_tabs(viewer_instance, product_id, tab_name)
            print("[固定鞍座确定] 关键参数同步完成")
        except Exception as e:
            print(f"[固定鞍座确定] 关键参数同步失败：{e}")
        
        # 4) 刷新当前Tab页的UI（显示最新的数据库数据）
        try:
            data = load_fixed_saddle_data_by_tab(product_id, element_id, tab_name)
            
            # 重新渲染当前Tab页
            render_fixed_saddle_table_data(table_param, data)
            apply_fixed_saddle_paramname_combobox(table_param, 0, 1, viewer_instance, data)
            
            print(f"[固定鞍座确定] 已刷新 {tab_name} 的UI，数据条数={len(data)}")
        except Exception as e:
            print(f"[固定鞍座确定] UI刷新失败：{e}")
        
        # 5) 显示成功提示
        QMessageBox.information(viewer_instance, "提示", f"{tab_name} 的参数已保存")
        
    except Exception as e:
        print(f"[固定鞍座确定] 保存失败：{e}")
        QMessageBox.warning(viewer_instance, "错误", f"保存失败：{e}")


def delete_fixed_saddle_data_from_db(product_id, tab_name):
    """从数据库删除指定Tab页的固定鞍座数据"""
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            # 删除指定Tab分类的数据
            cursor.execute("""
                DELETE FROM 产品设计活动表_元件附加参数合并表
                WHERE 产品ID = %s AND Tab分类 = %s
            """, (product_id, tab_name))
            
            deleted_count = cursor.rowcount
            connection.commit()
            print(f"[固定鞍座] 删除Tab页 {tab_name} 数据: {deleted_count} 条")
            
    except Exception as e:
        print(f"[固定鞍座] 删除Tab页数据失败: {e}")
        connection.rollback()
    finally:
        connection.close()


def _on_fixed_saddle_tab_right_menu(viewer_instance, pos):
    """固定鞍座Tab页右键菜单处理"""
    from PyQt5.QtWidgets import QMenu, QMessageBox
    from PyQt5.QtCore import Qt
    
    tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
    if not tab_widget:
        return
    
    bar = tab_widget.tabBar()
    index = bar.tabAt(pos)
    if index < 0:
        return

    text = tab_widget.tabText(index).strip()
    if text in {"+", "＋"}:
        return

    total = tab_widget.count()
    has_plus = total > 0 and tab_widget.tabText(total - 1).strip() in {"+", "＋"}
    real_count = total - (1 if has_plus else 0)

    menu = QMenu(tab_widget)
    act_delete = menu.addAction("删除此分类")
    act = menu.exec_(bar.mapToGlobal(pos))
    
    if act is act_delete:
        _remove_fixed_saddle_tab(viewer_instance, index)


def _remove_fixed_saddle_tab(viewer_instance, index):
    """删除固定鞍座Tab页"""
    from PyQt5.QtWidgets import QMessageBox
    
    tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
    if not tab_widget:
        return
    
    # 防止删除 "+"
    tab_text = tab_widget.tabText(index).strip()
    if tab_text in {"+", "＋"}:
        return

    # 至少保留一个（排除"+"）
    total = tab_widget.count()
    has_plus = total > 0 and tab_widget.tabText(total - 1).strip() in {"+", "＋"}
    real_count = total - (1 if has_plus else 0)
    if real_count <= 1:
        QMessageBox.information(tab_widget, "提示", "至少保留一个固定鞍座分类，不能删除最后一个 tab")
        return

    tab_name = tab_widget.tabText(index)
    print(f"[固定鞍座] 正在删除 tab: {tab_name}")

    # 删库
    product_id = getattr(viewer_instance, "product_id", None)
    if product_id:
        delete_fixed_saddle_data_from_db(product_id, tab_name)
    else:
        print("[固定鞍座] 当前 product_id 不存在，无法删除数据库记录")

    # 从映射字典中移除
    if hasattr(viewer_instance, 'dynamic_fixed_saddle_tabs'):
        viewer_instance.dynamic_fixed_saddle_tabs.pop(tab_name, None)

    # UI 移除
    tab_widget.removeTab(index)

    # 选中一个合理的 tab
    cnt = tab_widget.count()
    if cnt:
        sel = min(index, cnt - 1)
        if tab_widget.tabText(sel).strip() in {"+", "＋"} and sel > 0:
            sel -= 1
        tab_widget.setCurrentIndex(sel)

    # 让 PlusTabManager 重新判断"+"用页签还是右上角按钮
    if hasattr(viewer_instance, "fixed_saddle_plus_mgr") and viewer_instance.fixed_saddle_plus_mgr:
        viewer_instance.fixed_saddle_plus_mgr.refresh_after_model_change()


def _on_fixed_saddle_tab_changed(viewer_instance, index: int):
    """固定鞍座Tab页切换时的数据加载逻辑"""
    tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
    if not tab_widget or index < 0 or index >= tab_widget.count():
        return

    tab_name = tab_widget.tabText(index).strip()
    if tab_name in {"+", "＋"}:
        # 点击 + 标签，跳回上一页
        tab_widget.setCurrentIndex(max(0, index - 1))
        return

    print(f"[固定鞍座] Tab页切换: {tab_name}")
    
    # 获取当前Tab页对应的表格
    page = tab_widget.widget(index)
    table = page.property('param_table') if page else None
    
    if table is None:
        print(f"[固定鞍座] 未找到 {tab_name} 的参数表，跳过刷新")
        return
    
    # 刷新当前Tab页的数据
    try:
        patch_fixed_saddle_params_for_current_tab(table, tab_name, viewer_instance)
    except Exception as e:
        print(f"[固定鞍座] Tab页数据刷新失败: {e}")


def generate_unique_fixed_saddle_label(viewer_instance):
    """生成唯一的固定鞍座Tab页标签（PNO.1, PNO.2, PNO.3...）"""
    tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
    if not tab_widget:
        return "PNO.1"
    
    # 获取当前所有Tab页的标签
    existing_labels = set()
    for i in range(tab_widget.count()):
        text = tab_widget.tabText(i).strip()
        if text not in {"+", "＋"}:
            existing_labels.add(text)
    
    # 查找最大的PNO.x编号
    max_idx = 0
    for label in existing_labels:
        if label.startswith("PNO."):
            try:
                idx = int(label.split(".")[1])
                max_idx = max(max_idx, idx)
            except (ValueError, IndexError):
                continue
    
    # 返回下一个编号
    next_idx = max_idx + 1
    return f"PNO.{next_idx}"


def generate_unique_tab_id():
    """生成唯一的Tab_ID"""
    import time
    import random
    return f"TAB_{int(time.time() * 1000)}_{random.randint(1000, 9999)}"


def copy_fixed_saddle_data_for_new_tab(source_data, new_tab_name, new_tab_id):
    """复制源Tab页数据到新Tab页，清空指定字段"""
    copied_data = []
    
    # 需要复制的字段（保持原值）
    copy_fields = {'支座型式', '支座标准', '支座型号', '鞍座高度', '腐蚀裕量'}
    
    # 需要清空的字段
    clear_fields = {'元件名称', '材料类型', '材料牌号', '材料标准', '供货状态'}
    
    for item in source_data:
        param_name = item.get('参数名称', '')
        param_value = item.get('参数值', '')
        param_unit = item.get('参数单位', '')
        template_name = item.get('模板名称', '')
        template_id = item.get('模板ID', '')
        
        # 创建新的数据项
        new_item = {
            '参数名称': param_name,
            '参数值': param_value if param_name in copy_fields else '',
            '参数单位': param_unit,
            'Tab分类': new_tab_name,
            'Tab_ID': new_tab_id,
            '模板名称': template_name,
            '模板ID': template_id
        }
        
        # 特殊处理：元件名称需要清空为空的JSON数组
        if param_name == '元件名称':
            new_item['参数值'] = '[]'
        
        # 调试信息：特别关注腐蚀裕量和模板信息
        if param_name == '腐蚀裕量':
            print(f"[固定鞍座] 复制腐蚀裕量: 原值={param_value}, 是否复制={'是' if param_name in copy_fields else '否'}, 新值={new_item['参数值']}")
        
        # 调试信息：显示模板信息
        if param_name == '支座型式':  # 用第一个参数来显示模板信息
            print(f"[固定鞍座] 源数据模板信息: 模板名称='{template_name}', 模板ID='{template_id}'")
        
        copied_data.append(new_item)
        print(f"[固定鞍座] 复制参数: {param_name} = {new_item['参数值']}")
    
    return copied_data


def save_fixed_saddle_data_for_tab(product_id, element_id, tab_name, tab_id, data):
    """保存新Tab页的数据到数据库"""
    print(f"[固定鞍座] 开始保存数据: product_id={product_id}, element_id={element_id}, tab_name={tab_name}")
    print(f"[固定鞍座] 数据条数: {len(data)}")
    
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            # 插入新Tab页的数据
            for i, item in enumerate(data):
                print(f"[固定鞍座] 保存第{i+1}条数据: {item['参数名称']} = {item['参数值']}")
                # 处理模板ID，确保是整数
                template_id = item.get('模板ID', 0)
                if template_id == '' or template_id is None:
                    template_id = 0
                else:
                    try:
                        template_id = int(template_id)
                    except (ValueError, TypeError):
                        template_id = 0
                
                cursor.execute("""
                    INSERT INTO 产品设计活动表_元件附加参数合并表 
                    (产品ID, 元件ID, 参数名称, 参数值, 参数单位, Tab分类, Tab_ID, 模板名称, 模板ID)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    product_id,
                    element_id,
                    item['参数名称'],
                    item['参数值'],
                    item['参数单位'],
                    item['Tab分类'],
                    item['Tab_ID'],
                    item.get('模板名称', ''),  # 使用复制的模板名称
                    template_id               # 确保是整数的模板ID
                ))
            
            connection.commit()
            print(f"[固定鞍座] 新Tab页 {tab_name} 数据保存完成: {len(data)} 条")
            
    except Exception as e:
        print(f"[固定鞍座] 保存新Tab页数据失败: {e}")
        import traceback
        traceback.print_exc()
        connection.rollback()
    finally:
        connection.close()


def create_fixed_saddle_tab_ui(viewer_instance, tab_name, data):
    """创建新Tab页的UI"""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QAbstractItemView, QHeaderView
    from PyQt5.QtCore import Qt
    
    tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
    if not tab_widget:
        return
    
    # 创建新的Tab页
    tab_page = QWidget()
    tab_widget.addTab(tab_page, tab_name)
    
    # 创建表格
    table = QTableWidget()
    table.setColumnCount(3)
    table.setHorizontalHeaderLabels(['参数名称', '参数值', '参数单位'])
    table.setAlternatingRowColors(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setEditTriggers(QAbstractItemView.SelectedClicked)
    table.verticalHeader().setVisible(False)
    
    # 设置列宽和表头样式
    header = table.horizontalHeader()
    for i in range(table.columnCount()):
        header.setSectionResizeMode(i, QHeaderView.Stretch)
    
    # 设置表头样式
    table.setStyleSheet("""
        QHeaderView::section {
            background-color: #F2F2F2;
            color: black;
            font-weight: bold;
            text-align: center;
            padding: 5px;
            border: 1px solid #CCCCCC;
            border-right: 1px solid #CCCCCC;
            border-bottom: 1px solid #CCCCCC;
        }
        QHeaderView::section:first {
            border-left: 1px solid #CCCCCC;
        }
    """)
    table.horizontalHeader().setFixedHeight(35)
    
    # 创建布局
    layout = QVBoxLayout(tab_page)
    layout.addWidget(table)
    
    # 设置表格属性到页面
    tab_page.setProperty('param_table', table)
    
    # 添加到映射字典
    if not hasattr(viewer_instance, 'dynamic_fixed_saddle_tabs'):
        viewer_instance.dynamic_fixed_saddle_tabs = {}
    viewer_instance.dynamic_fixed_saddle_tabs[tab_name] = table
    
    # 设置表格属性，用于选项过滤
    table._viewer_instance = viewer_instance
    table._current_tab_name = tab_name
    
    # 渲染数据
    render_fixed_saddle_table_data(table, data)
    apply_fixed_saddle_paramname_combobox(table, 0, 1, viewer_instance, data)
    
    # 切换到新Tab页
    tab_widget.setCurrentIndex(tab_widget.count() - 1)
    
    print(f"[固定鞍座] 新Tab页UI创建完成: {tab_name}")


def _add_single_fixed_saddle_tab_copy_only(viewer_instance, source_tab_index, source_tab_name):
    """新增固定鞍座Tab页（模仿管口的_add_single_table_tab_copy_only）"""
    try:
        print(f"[固定鞍座] 开始新增Tab页，源Tab: {source_tab_name}")
        
        tab_widget = getattr(viewer_instance, 'tabWidget_2', None)
        if not tab_widget:
            print("[固定鞍座] 未找到tabWidget_2")
            return
        
        # 生成新的Tab标签和ID
        new_tab_name = generate_unique_fixed_saddle_label(viewer_instance)
        new_tab_id = generate_unique_tab_id()
        
        print(f"[固定鞍座] 新Tab标签: {new_tab_name}, Tab_ID: {new_tab_id}")
        
        # 获取源Tab页的数据
        product_id = getattr(viewer_instance, 'product_id', None)
        element_id = getattr(viewer_instance, 'clicked_element_data', {}).get('元件ID', '')
        
        if not product_id or not element_id:
            print("[固定鞍座] 缺少product_id或element_id")
            return
        
        # 加载源Tab页的数据
        print(f"[固定鞍座] 尝试加载源Tab页数据: {source_tab_name}")
        source_data = load_fixed_saddle_data_by_tab(product_id, element_id, source_tab_name)
        if not source_data:
            print(f"[固定鞍座] 源Tab页 {source_tab_name} 没有数据")
            return
        
        print(f"[固定鞍座] 源Tab页数据加载成功: {len(source_data)} 条")
        for item in source_data:
            if item.get('参数名称') == '腐蚀裕量':
                print(f"[固定鞍座] 源Tab页腐蚀裕量: {item.get('参数值')}")
                break
        
        # 复制数据并清空指定字段
        copied_data = copy_fixed_saddle_data_for_new_tab(source_data, new_tab_name, new_tab_id)
        print(f"[固定鞍座] 复制数据完成: {len(copied_data)} 条")
        
        # 保存新Tab页的数据到数据库
        print(f"[固定鞍座] 开始保存数据到数据库: {new_tab_name}")
        save_fixed_saddle_data_for_tab(product_id, element_id, new_tab_name, new_tab_id, copied_data)
        print(f"[固定鞍座] 数据库保存完成")
        
        # 创建新的Tab页UI
        create_fixed_saddle_tab_ui(viewer_instance, new_tab_name, copied_data)
        
        print(f"[固定鞍座] 新增Tab页完成: {new_tab_name}")
        
    except Exception as e:
        print(f"[固定鞍座] 新增Tab页失败: {e}")
        import traceback
        traceback.print_exc()


def patch_fixed_saddle_params_for_current_tab(table, tab_name, viewer_instance):
    """刷新当前Tab页的数据（模仿管口的patch_codes_for_current_tab）"""
    try:
        # 从数据库加载当前Tab页的数据
        product_id = getattr(viewer_instance, 'product_id', None)
        element_id = 29  # 固定鞍座的元件ID
        
        if not product_id:
            print("[固定鞍座] 缺少product_id，跳过数据刷新")
            return
            
        # 加载数据
        data = load_fixed_saddle_data_by_tab(product_id, element_id, tab_name)
        if not data:
            print(f"[固定鞍座] Tab页 {tab_name} 没有数据")
            return
            
        # 重新渲染表格
        render_fixed_saddle_table_data(table, data)
        apply_fixed_saddle_paramname_combobox(table, 0, 1, viewer_instance, data)
        
        print(f"[固定鞍座] Tab页 {tab_name} 数据刷新完成")
        
    except Exception as e:
        print(f"[固定鞍座] Tab页数据刷新失败: {e}")


def render_fixed_saddle_data_to_ui(viewer_instance, saddle_data):
    """将固定鞍座数据渲染到UI（完全模仿apply_paramname_combobox的逻辑）"""
    if not saddle_data:
        print("[固定鞍座] 没有数据需要渲染")
        return
        
    print(f"[固定鞍座] 开始渲染数据: {len(saddle_data)} 条")
    
    # 根据Tab分类分组数据
    tab_data = {}
    for item in saddle_data:
        tab_name = item.get('Tab分类', 'PNO.1')
        if tab_name not in tab_data:
            tab_data[tab_name] = []
        tab_data[tab_name].append(item)
    
    print(f"[固定鞍座] Tab分组: {list(tab_data.keys())}")
    
    # 获取固定鞍座的TabWidget
    try:
        tab_widget = viewer_instance.tabWidget_2  # 固定鞍座的TabWidget
        if not tab_widget:
            print("[固定鞍座] 未找到TabWidget_2")
            return
            
        # 清空现有Tab页
        while tab_widget.count() > 0:
            tab_widget.removeTab(0)
            
        # 为每个Tab分类创建Tab页
        for tab_name, data in tab_data.items():
            print(f"[固定鞍座] 创建Tab页: {tab_name}, 数据条数: {len(data)}")
            
            # 创建新的Tab页
            tab_page = QWidget()
            tab_widget.addTab(tab_page, tab_name)
            
            # 初始化基础数据结构
            if not hasattr(viewer_instance, 'dynamic_fixed_saddle_tabs'):
                viewer_instance.dynamic_fixed_saddle_tabs = {}
            
            # 创建表格 - 完全模仿普通元件的表格结构
            table = QTableWidget()
            table.setColumnCount(3)  # 参数名称 | 参数值 | 参数单位
            table.setHorizontalHeaderLabels(['参数名称', '参数值', '参数单位'])
            
            # 设置表格属性 - 完全模仿普通元件的样式
            table.setAlternatingRowColors(False)  # 不设置交替行颜色
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setEditTriggers(QAbstractItemView.SelectedClicked)
            
            # 隐藏行序号 - 完全模仿普通元件
            table.verticalHeader().setVisible(False)
            
            # 设置列宽和表头样式 - 完全模仿普通元件
            from PyQt5.QtWidgets import QHeaderView
            header = table.horizontalHeader()
            for i in range(table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            
            # 设置表头样式 - 完全模仿普通元件的CustomHeaderView
            table.setStyleSheet("""
                QHeaderView::section {
                    background-color: #F2F2F2;
                    color: black;
                    font-weight: bold;
                    text-align: center;
                    padding: 5px;
                    border: 1px solid #CCCCCC;
                    border-right: 1px solid #CCCCCC;
                    border-bottom: 1px solid #CCCCCC;
                }
                QHeaderView::section:first {
                    border-left: 1px solid #CCCCCC;
                }
            """)
            
            # 设置表头高度 - 完全模仿普通元件
            table.horizontalHeader().setFixedHeight(35)
            
            # 创建布局
            layout = QVBoxLayout(tab_page)
            layout.addWidget(table)
            
            # 设置表格属性到页面
            tab_page.setProperty('param_table', table)
            
            # 添加到映射字典
            viewer_instance.dynamic_fixed_saddle_tabs[tab_name] = table
            
            # 设置表格属性，用于选项过滤
            table._viewer_instance = viewer_instance
            table._current_tab_name = tab_name
            
            # 先填充数据到表格，然后使用apply_paramname_combobox的逻辑渲染
            render_fixed_saddle_table_data(table, data)
            apply_fixed_saddle_paramname_combobox(table, 0, 1, viewer_instance, data)
            
        # 连接Tab页切换信号
        try:
            tab_widget.currentChanged.connect(lambda index: _on_fixed_saddle_tab_changed(viewer_instance, index))
            print("[固定鞍座] Tab页切换信号连接完成")
        except Exception as e:
            print(f"[固定鞍座] Tab页切换信号连接失败: {e}")
            
        # 连接右键菜单信号
        try:
            from PyQt5.QtCore import Qt
            tab_widget.tabBar().setContextMenuPolicy(Qt.CustomContextMenu)
            tab_widget.tabBar().customContextMenuRequested.connect(lambda pos: _on_fixed_saddle_tab_right_menu(viewer_instance, pos))
            print("[固定鞍座] 右键菜单信号连接完成")
        except Exception as e:
            print(f"[固定鞍座] 右键菜单信号连接失败: {e}")
            
        # 初始化PlusTabManager（在创建完所有Tab页后）
        try:
            from modules.cailiaodingyi.controllers.add_tab import PlusTabManager
            from PyQt5.QtCore import QTimer
            
            # 如果PlusTabManager已存在，先清理
            if hasattr(viewer_instance, 'fixed_saddle_plus_mgr'):
                try:
                    # 断开信号连接
                    viewer_instance.fixed_saddle_plus_mgr.tw.tabBar().tabBarClicked.disconnect()
                    viewer_instance.fixed_saddle_plus_mgr.tw.removeEventFilter(viewer_instance.fixed_saddle_plus_mgr)
                    viewer_instance.fixed_saddle_plus_mgr.tw.tabBar().removeEventFilter(viewer_instance.fixed_saddle_plus_mgr)
                except:
                    pass
                del viewer_instance.fixed_saddle_plus_mgr
            
            # 将_add_single_fixed_saddle_tab_copy_only方法绑定到viewer_instance
            if not hasattr(viewer_instance, '_add_single_fixed_saddle_tab_copy_only'):
                def wrapper_add_fixed_saddle_tab(source_tab_index, source_tab_name):
                    return _add_single_fixed_saddle_tab_copy_only(viewer_instance, source_tab_index, source_tab_name)
                viewer_instance._add_single_fixed_saddle_tab_copy_only = wrapper_add_fixed_saddle_tab
            
            # 创建新的PlusTabManager
            viewer_instance.fixed_saddle_plus_mgr = PlusTabManager(
                tab_widget, 
                viewer_instance._add_single_fixed_saddle_tab_copy_only
            )
            print("[固定鞍座] PlusTabManager 初始化完成")
            
            # 延迟刷新PlusTabManager状态，确保UI完全渲染后显示"+"按钮
            def delayed_refresh():
                try:
                    if hasattr(viewer_instance, 'fixed_saddle_plus_mgr'):
                        mgr = viewer_instance.fixed_saddle_plus_mgr
                        print(f"[固定鞍座] PlusTabManager 状态: _ready={mgr._ready}, _plus_as_tab={mgr._plus_as_tab}")
                        print(f"[固定鞍座] TabWidget 可见性: {tab_widget.isVisible()}, TabBar可见性: {tab_widget.tabBar().isVisible()}")
                        print(f"[固定鞍座] TabBar宽度: {tab_widget.tabBar().width()}")
                        print(f"[固定鞍座] 当前Tab数量: {tab_widget.count()}")
                        
                        mgr.refresh_after_model_change()
                        mgr.update_mode()  # 强制更新模式
                        
                        print(f"[固定鞍座] 刷新后状态: _ready={mgr._ready}, _plus_as_tab={mgr._plus_as_tab}")
                        print(f"[固定鞍座] 角落按钮可见性: {mgr._btn.isVisible()}")
                        print(f"[固定鞍座] 页签中是否有'+': {any(tab_widget.tabText(i) == '+' for i in range(tab_widget.count()))}")
                        print("[固定鞍座] PlusTabManager 延迟刷新完成")
                except Exception as e:
                    print(f"[固定鞍座] PlusTabManager 延迟刷新失败: {e}")
                    import traceback
                    traceback.print_exc()
            
            QTimer.singleShot(100, delayed_refresh)  # 100ms后刷新
            
        except Exception as e:
            print(f"[固定鞍座] PlusTabManager 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            
    except Exception as e:
        print(f"[固定鞍座] UI渲染失败: {e}")


def render_fixed_saddle_table_data(table, data):
    """将固定鞍座数据填充到表格中（完全模仿render_additional_info_table的逻辑）"""
    from PyQt5.QtWidgets import QTableWidgetItem
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QHeaderView
    
    if not data:
        print("[固定鞍座] 没有数据需要填充")
        return
    
    print(f"[固定鞍座] 开始填充数据到表格: {len(data)} 条")
    
    # 根据参数名称分组数据
    param_groups = {}
    for item in data:
        param_name = item.get('参数名称', '')
        if param_name not in param_groups:
            param_groups[param_name] = item
    
    # 定义需要显示的参数顺序（按照你的要求）
    display_params = [
        '支座型式',
        '支座标准', 
        '支座型号',
        '鞍座高度',
        '腐蚀裕量',
        '元件名称',
        '材料类型',
        '材料牌号',
        '材料标准',
        '供货状态'
    ]
    
    # 完全模仿render_additional_info_table的逻辑
    with FreezeUI(table):   # 🚩 批量操作前冻结
        table.setRowCount(0)
        table.clearContents()
        headers = ["参数名称", "参数值", "参数单位"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setRowCount(len(display_params))
        
        # 按照指定顺序渲染数据
        for row_idx, param_name in enumerate(display_params):
            # 获取该参数的数据
            if param_name in param_groups:
                row_data = param_groups[param_name]
            else:
                row_data = {'参数名称': param_name, '参数值': '', '参数单位': ''}
            
            # 渲染三列数据
            for col_idx, header_name in enumerate(headers):
                # 获取原始值
                raw_value = row_data.get(header_name, "")
                
                # 初始化显示值
                display_value = raw_value
                
                # 对元件名称进行特殊处理：解析JSON数组并显示所有选中的选项
                if param_name == "元件名称" and header_name == "参数值":
                    # 如果是JSON格式，解析并显示所有选中的选项
                    if raw_value and str(raw_value).startswith("[") and str(raw_value).endswith("]"):
                        try:
                            import json
                            parsed_options = json.loads(str(raw_value))
                            if parsed_options and len(parsed_options) > 0:
                                # 显示所有选中的选项，用"、"分隔（CheckComboDelegate的默认分隔符）
                                display_value = "、".join(parsed_options)
                                print(f"[固定鞍座] 初始渲染解析元件名称: {raw_value} -> {display_value}")
                            else:
                                # 如果是空数组[]，UI显示为空字符串
                                display_value = ""
                                print(f"[固定鞍座] 初始渲染解析元件名称: {raw_value} -> (空)")
                        except json.JSONDecodeError:
                            display_value = raw_value
                    elif raw_value == "" or raw_value is None:
                        # 如果是空字符串或None，显示为空字符串（但保持数据库中的空字符串状态）
                        display_value = ""
                        print(f"[固定鞍座] 初始渲染元件名称为空: {raw_value} -> (空)")
                    else:
                        # 其他情况，保持原始值
                        display_value = raw_value
                
                item = QTableWidgetItem(str(display_value))
                item.setTextAlignment(Qt.AlignCenter)
                # ✅ 设置只读（不可编辑）列：参数名称 和 参数单位
                if col_idx in [0, 2]:  # 参数名称列 和 参数单位列
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                table.setItem(row_idx, col_idx, item)
    
    print(f"[固定鞍座] 数据填充完成，表格行数: {table.rowCount()}")


def render_fixed_saddle_table_with_combobox(table, data, viewer_instance):
    """使用apply_paramname_combobox的逻辑渲染固定鞍座表格"""
    try:
        # 根据参数名称分组数据
        param_groups = {}
        for item in data:
            param_name = item.get('参数名称', '')
            if param_name not in param_groups:
                param_groups[param_name] = item
        
        # 定义需要显示的参数顺序
        display_params = [
            '支座型式',
            '支座标准', 
            '支座型号',
            '鞍座高度',
            '腐蚀裕量',
            '元件名称',
            '材料类型',
            '材料牌号',
            '材料标准',
            '供货状态'
        ]
        
        # 设置行数（每个参数一行）
        table.setRowCount(len(display_params))
        
        # 渲染数据（竖着显示）
        for row, param_name in enumerate(display_params):
            # 第一列：参数名称
            name_item = QTableWidgetItem(param_name)
            name_item.setTextAlignment(Qt.AlignCenter)
            name_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # 只读
            table.setItem(row, 0, name_item)
            
            # 第二列：参数值
            if param_name in param_groups:
                item = param_groups[param_name]
                param_value = item.get('参数值', '')
                param_unit = item.get('参数单位', '')
                
                # 创建单元格
                cell_item = QTableWidgetItem(str(param_value))
                cell_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, cell_item)
            else:
                # 如果没有数据，创建空单元格
                cell_item = QTableWidgetItem("")
                cell_item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, 1, cell_item)
        
        # 调整列宽
        table.resizeColumnsToContents()
        
        # 使用apply_paramname_combobox的逻辑设置编辑器
        apply_fixed_saddle_paramname_combobox(table, 0, 1, viewer_instance)
        
    except Exception as e:
        print(f"[固定鞍座] 表格数据渲染失败: {e}")


def apply_fixed_saddle_paramname_combobox(table: QTableWidget, param_col: int, value_col: int, viewer_instance, data=None):
    """完全模仿apply_paramname_combobox的逻辑来处理固定鞍座参数"""
    # ===== 必要导入 =====
    from PyQt5.QtCore import Qt, QEvent, QTimer
    from PyQt5.QtWidgets import (
        QStyledItemDelegate, QLineEdit, QTableWidgetItem, QAbstractItemView, QComboBox
    )

    # ===== 常量集合 =====
    MATERIAL_FIELDS = {
        "材料类型", "材料牌号", "材料标准", "供货状态"
    }
    READONLY_PARAMS = {"零件名称"}  # 移除元件名称，让它可编辑
    NUMERIC_PARAMS = {"鞍座高度", "腐蚀裕量"}
    DROPDOWN_PARAMS = {"支座型式", "支座标准", "支座型号", "元件名称"}  # 添加元件名称
    
    # 简化的小工具 - 完全模仿apply_paramname_combobox
    def ensure_editable_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt); table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        return it
    def ensure_readonly_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt); table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        return it

    # 从数据库获取参数选项
    def get_options_from_database(param_name):
        """从数据库获取参数的可选值"""
        try:
            # 如果是元件名称，从当前表格数据中解析
            if param_name == "元件名称":
                # 查找元件名称行
                for row in range(table.rowCount()):
                    pitem = table.item(row, param_col)
                    if pitem and pitem.text().strip() == "元件名称":
                        vitem = table.item(row, value_col)
                        if vitem:
                            raw_text = vitem.text().strip()
                            if raw_text:
                                try:
                                    import json
                                    # 解析JSON数组
                                    options = json.loads(raw_text)
                                    print(f"[固定鞍座] 从表格数据解析元件名称: {raw_text} -> {options}")
                                    return options
                                except json.JSONDecodeError:
                                    # 如果不是JSON，按逗号分割
                                    options = [x.strip() for x in raw_text.split(",") if x.strip()]
                                    print(f"[固定鞍座] 从表格数据按逗号分割元件名称: {raw_text} -> {options}")
                                    return options
                return []
            
            from modules.cailiaodingyi.funcs.funcs_pdf_change import get_dependency_mapping_from_db
            
            # 从数据库获取联动规则
            mapping = get_dependency_mapping_from_db()
            
            # 根据参数名获取选项
            if param_name == "支座型式":
                # 从法兰参数联动表获取支座型式的选项
                from modules.cailiaodingyi.db_cnt import get_connection
                from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_2
                
                conn = get_connection(**db_config_2)
                try:
                    with conn.cursor() as cur:
                        sql = "SELECT DISTINCT 主参数值 FROM 法兰参数联动表 WHERE 主参数名称 = %s"
                        cur.execute(sql, (param_name,))
                        results = cur.fetchall()
                        options = [row["主参数值"] for row in results if row["主参数值"]]
                        return options
                finally:
                    conn.close()
            else:
                # 其他参数暂时返回空列表，由联动逻辑处理
                return []
                
        except Exception as e:
            print(f"[获取{param_name}选项] 失败: {e}")
            return []

    # ---------- 数值代理 ----------
    class NumericDelegate(QStyledItemDelegate):
        def __init__(self, rule: str, pname_for_tip: str, minmax=None, allowed_texts=None):
            super().__init__(table)
            self.rule = rule
            self.pname = pname_for_tip
            self.minmax = minmax or (None, None, True, True)
            self.allowed_texts = set(allowed_texts or [])

        def createEditor(self, parent, option, index):
            le = QLineEdit(parent)
            le.setAlignment(Qt.AlignCenter)
            le.setAutoFillBackground(True)
            le.setStyleSheet("""
                QLineEdit{
                    border:none;
                    background:palette(base);
                    font-size:9pt;
                    font-family:"Microsoft YaHei";
                    padding-left:2px;
                }
            """)
            le.editingFinished.connect(lambda: self.commitData.emit(le))
            le.returnPressed.connect(lambda: (self.commitData.emit(le), self.closeEditor.emit(le, QStyledItemDelegate.NoHint)))
            le.installEventFilter(self)
            return le

        def eventFilter(self, editor, ev):
            if isinstance(editor, QLineEdit) and ev.type() == QEvent.FocusOut:
                try:
                    self.commitData.emit(editor)
                except Exception:
                    pass
            return super().eventFilter(editor, ev)

        def setEditorData(self, editor, index):
            editor.setText(index.data() or "")
            editor.selectAll()

        def updateEditorGeometry(self, editor, option, index):
            editor.setGeometry(option.rect)

        def setModelData(self, editor, model, index):
            tip = getattr(viewer_instance, "line_tip", None)
            txt = (editor.text() or "").strip()

            def show_tip(msg: str):
                if not tip:
                    return
                tip.setStyleSheet("color:red;")
                tip.setText(msg)
                QTimer.singleShot(0, lambda: (tip.setStyleSheet("color:red;"), tip.setText(msg)))
                QTimer.singleShot(50, lambda: (tip.setStyleSheet("color:red;"), tip.setText(msg)))

            def clear_tip():
                if tip:
                    tip.setText("")

            if txt == "":
                model.setData(index, "")
                clear_tip()
                return

            # 放行允许字面值
            if txt in self.allowed_texts:
                clear_tip()
                model.setData(index, txt)
                return

            try:
                val = float(txt)
                ok = True
                limit_msg = "有效数值"

                if self.rule == "gt0":
                    ok = (val > 0)
                    limit_msg = "大于 0"
                elif self.rule == "ge0":
                    ok = (val >= 0)
                    limit_msg = "大于等于 0"
                elif self.rule == "range":
                    lo, hi, lo_inc, hi_inc = self.minmax
                    parts = []
                    if lo is not None:
                        ok = ok and (val >= lo if lo_inc else val > lo)
                        parts.append(("≥" if lo_inc else ">") + str(lo))
                    if hi is not None:
                        ok = ok and (val <= hi if hi_inc else val < hi)
                        parts.append(("≤" if hi_inc else "<") + str(hi))
                    limit_msg = " 且 ".join(parts) if parts else "有效范围"

                if not ok:
                    extra = f"，或输入：{'、'.join(sorted(self.allowed_texts))}" if self.allowed_texts else ""
                    show_tip(f"第 {index.row() + 1} 行参数'{self.pname}'的值应为{limit_msg}的数字{extra}！")
                    model.setData(index, "")
                    return

                clear_tip()
                model.setData(index, txt)
            except Exception:
                extra = f"，或输入：{'、'.join(sorted(self.allowed_texts))}" if self.allowed_texts else ""
                show_tip(f"第 {index.row() + 1} 行参数'{self.pname}'的值应为数字{extra}！")
                model.setData(index, "")

    # ---------- 下拉框代理 ----------
    class ComboDelegate(QStyledItemDelegate):
        def __init__(self, options, parent_table):
            super().__init__(parent_table)
            self.options = options

        def createEditor(self, parent, option, index):
            combo = QComboBox(parent)
            combo.addItems(self.options)
            combo.setEditable(False)
            combo.currentTextChanged.connect(lambda: self.commitData.emit(combo))
            return combo

        def setEditorData(self, editor, index):
            text = index.data() or ""
            if text in self.options:
                editor.setCurrentText(text)
            else:
                editor.setCurrentIndex(0)

        def setModelData(self, editor, model, index):
            model.setData(index, editor.currentText())

        def updateEditorGeometry(self, editor, option, index):
            editor.setGeometry(option.rect)

    # 1) 单击进入编辑
    table.setEditTriggers(QAbstractItemView.SelectedClicked)

    # 2) 清理 value 列 cellWidget
    for r in range(table.rowCount()):
        if table.cellWidget(r, value_col):
            table.setCellWidget(r, value_col, None)

    # 3) 初次渲染：用总闸防误触发 - 完全模仿apply_paramname_combobox
    table._loading = True
    table.blockSignals(True)
    try:
        for row in range(table.rowCount()):
            pitem = table.item(row, param_col)
            pname = pitem.text().strip() if pitem else ""

            # 只读参数
            if pname in READONLY_PARAMS:
                table.setItemDelegateForRow(row, None)
                if table.cellWidget(row, value_col): 
                    table.setCellWidget(row, value_col, None)
                cur = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                ensure_readonly_item(row, value_col, cur)
                continue

            # 材料字段 - 暂时设为可编辑，后续会安装材料联动
            if pname in MATERIAL_FIELDS:
                cur_text = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                ensure_editable_item(row, value_col, cur_text)
                continue

            # 数值字段
            if pname in NUMERIC_PARAMS:
                vitem = table.item(row, value_col)
                cur_text = vitem.text().strip() if vitem else ""
                ensure_editable_item(row, value_col, cur_text)
                if pname == "鞍座高度":
                    table.setItemDelegateForRow(row, NumericDelegate("gt0", pname))
                elif pname == "腐蚀裕量":
                    table.setItemDelegateForRow(row, NumericDelegate("ge0", pname))
                continue

            # 下拉框字段 - 从数据库读取选项
            if pname in DROPDOWN_PARAMS:
                # 从数据库获取选项
                options = get_options_from_database(pname)
                
                # 如果从数据库获取不到选项，使用默认选项
                if not options:
                    if pname == "支座型式":
                        options = ["鞍式支座", "耳式支座"]
                    elif pname == "支座标准":
                        options = ["NB/T 47065.1", "NB/T 47065.2"]
                    elif pname == "支座型号":
                        options = ["A", "BI", "BII", "BIII", "BIV", "BV"]
                    elif pname == "元件名称":
                        options = ["底板", "腹板", "筋板", "垫板", "盖板"]
                
                if options:
                    # 对于元件名称，需要特殊处理显示值
                    if pname == "元件名称":
                        # 从原始数据中获取JSON值，而不是从表格中读取
                        raw_value = ""
                        for item in data:
                            if item.get('参数名称') == '元件名称':
                                raw_value = item.get('参数值', '')
                                break
                        
                        display_value = ""
                        
                        # 如果原始值是JSON格式，解析并显示所有选中的选项
                        if raw_value and str(raw_value).startswith("[") and str(raw_value).endswith("]"):
                            try:
                                import json
                                parsed_options = json.loads(str(raw_value))
                                if parsed_options:
                                    # 显示所有选中的选项，用"、"分隔（CheckComboDelegate的默认分隔符）
                                    display_value = "、".join(parsed_options)
                                    print(f"[固定鞍座] 元件名称显示值: {raw_value} -> {display_value}")
                            except json.JSONDecodeError:
                                display_value = raw_value
                        else:
                            # 如果原始值不是JSON格式，使用表格中的当前值
                            current_value = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                            display_value = current_value
                        
                        # 设置显示值
                        ensure_editable_item(row, value_col, display_value)
                        
                        # 使用复选下拉框（真正的多选）
                        from modules.cailiaodingyi.controllers.checkcombo import CheckComboDelegate
                        table.setItemDelegateForRow(row, CheckComboDelegate(options, table))
                    else:
                        # 其他参数使用普通下拉框
                        cur_text = table.item(row, value_col).text().strip() if table.item(row, value_col) else ""
                        ensure_editable_item(row, value_col, cur_text)
                        table.setItemDelegateForRow(row, ComboDelegate(options, table))
                continue


    finally:
        table.blockSignals(False)
        table._loading = False

    # 4) 根据当前数据值设置初始联动状态
    try:
        # 获取当前支座型式的值
        current_support_type = None
        for row in range(table.rowCount()):
            pitem = table.item(row, param_col)
            if pitem and pitem.text().strip() == "支座型式":
                vitem = table.item(row, value_col)
                if vitem:
                    current_support_type = vitem.text().strip()
                break
        
        # 如果支座型式有值，设置相应的联动（不自动更新值，只更新选项）
        if current_support_type:
            print(f"[固定鞍座] 初始联动: 支座型式={current_support_type}")
            # 保存初始值用于后续比较
            setattr(table, "_old_支座型式", current_support_type)
            
            # 更新支座标准选项（不自动更新值）
            update_support_standard_options(table, current_support_type, param_col, value_col, auto_update=False)
            # 更新元件名称选项（不自动更新值）
            update_component_name_options(table, current_support_type, param_col, value_col, auto_update=False)
            
            # 获取当前支座标准的值，设置支座型号联动
            current_support_standard = None
            for row in range(table.rowCount()):
                pitem = table.item(row, param_col)
                if pitem and pitem.text().strip() == "支座标准":
                    vitem = table.item(row, value_col)
                    if vitem:
                        current_support_standard = vitem.text().strip()
                    break
            
            if current_support_standard:
                print(f"[固定鞍座] 初始联动: 支座标准={current_support_standard}")
                # 保存初始值用于后续比较
                setattr(table, "_old_支座标准", current_support_standard)
                
                # 更新支座型号选项（不自动更新值）
                update_support_model_options(table, current_support_standard, param_col, value_col, auto_update=False)
    except Exception as e:
        print(f"[固定鞍座] 初始联动设置失败: {e}")

    # 5) 安装材料四字段联动逻辑 - 完全模仿apply_paramname_combobox
    install_material_delegate_linkage(table, param_col, value_col, viewer_instance)

    # 5) 事件处理 - 完全模仿apply_paramname_combobox
    def _on_item_changed(item: QTableWidgetItem):
        # 总闸
        if getattr(table, "_loading", False):
            return
        if item.column() != value_col:
            return

        r = item.row()
        pitem = table.item(r, param_col)
        if not pitem:
            return

        pname = pitem.text().strip()
        val = (item.text() or "").strip()

        # 支座型式联动逻辑 - 只在值真正改变时触发
        if pname == "支座型式":
            try:
                # 检查值是否真的改变了
                old_value = getattr(table, f"_old_{pname}", "")
                if old_value != val:
                    print(f"[固定鞍座] 支座型式值改变: {old_value} -> {val}")
                    # 更新支座标准选项（自动更新值）
                    update_support_standard_options(table, val, param_col, value_col, auto_update=True)
                    # 更新元件名称选项（自动更新值）
                    update_component_name_options(table, val, param_col, value_col, auto_update=True)
                    # 保存当前值
                    setattr(table, f"_old_{pname}", val)
                else:
                    print(f"[固定鞍座] 支座型式值未改变: {val}")
            except Exception as e:
                print(f"[支座型式联动] 失败: {e}")

        # 支座标准联动逻辑 - 只在值真正改变时触发
        elif pname == "支座标准":
            try:
                # 检查值是否真的改变了
                old_value = getattr(table, f"_old_{pname}", "")
                if old_value != val:
                    print(f"[固定鞍座] 支座标准值改变: {old_value} -> {val}")
                    # 更新支座型号选项（自动更新值）
                    update_support_model_options(table, val, param_col, value_col, auto_update=True)
                    # 保存当前值
                    setattr(table, f"_old_{pname}", val)
                else:
                    print(f"[固定鞍座] 支座标准值未改变: {val}")
            except Exception as e:
                print(f"[支座标准联动] 失败: {e}")

        # 参数修改时只更新UI，不保存到数据库
        # 真正的保存和同步逻辑在确定按钮中处理
        print(f"[固定鞍座-参数修改] {pname}={val} (仅UI更新，未保存到数据库)")

    # 6) 单击进入编辑
    def _edit_on_click(r, c):
        idx = table.model().index(r, c)
        it = table.item(r, c)
        if idx.isValid() and it and (it.flags() & Qt.ItemIsEditable):
            table.setCurrentIndex(idx)
            table.edit(idx)

    # 绑定事件
    try:
        table.itemChanged.disconnect()
    except Exception:
        pass
    table.itemChanged.connect(_on_item_changed)

    try:
        table.cellClicked.disconnect()
    except Exception:
        pass
    table.cellClicked.connect(_edit_on_click)


def update_support_standard_options(table, support_type, param_col, value_col, auto_update=True):
    """根据支座型式更新支座标准选项 - 从数据库读取联动规则"""
    try:
        from modules.cailiaodingyi.db_cnt import get_connection
        from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_2
        
        # 直接从数据库查询联动规则
        conn = get_connection(**db_config_2)
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT 联动选项 
                    FROM 法兰参数联动表 
                    WHERE 主参数名称 = %s AND 主参数值 = %s AND 被联动参数名称 = %s
                """
                cur.execute(sql, ("支座型式", support_type, "支座标准"))
                result = cur.fetchone()
                
                # 查找支座标准行
                for row in range(table.rowCount()):
                    pitem = table.item(row, param_col)
                    if pitem and pitem.text().strip() == "支座标准":
                        # 从数据库获取选项
                        options = []
                        if result and result["联动选项"]:
                            # 直接使用原始值，不进行分割
                            standard_value = result["联动选项"].strip()
                            options = [standard_value]
                        
                        # 更新下拉框选项
                        if options:
                            from modules.cailiaodingyi.controllers.combo import ComboDelegate
                            table.setItemDelegateForRow(row, ComboDelegate(options, table))
                            
                            # 只有在用户手动修改时才自动更新值
                            if auto_update:
                                if len(options) == 1:
                                    # 有唯一值就直接填入唯一值
                                    table.item(row, value_col).setText(options[0])
                                    print(f"[固定鞍座] 自动更新支座标准为: {options[0]}")
                                elif len(options) > 1:
                                    # 有多个值就填入第一个
                                    table.item(row, value_col).setText(options[0])
                                    print(f"[固定鞍座] 自动更新支座标准为第一个选项: {options[0]}")
                                else:
                                    # 没有选项就清空
                                    table.item(row, value_col).setText("")
                                    print(f"[固定鞍座] 清空支座标准")
                        break
        finally:
            conn.close()
    except Exception as e:
        print(f"[更新支座标准选项] 失败: {e}")


def update_support_model_options(table, support_standard, param_col, value_col, auto_update=True):
    """根据支座标准更新支座型号选项 - 从数据库读取联动规则"""
    try:
        from modules.cailiaodingyi.db_cnt import get_connection
        from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_2
        
        # 直接从数据库查询联动规则
        conn = get_connection(**db_config_2)
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT 联动选项 
                    FROM 法兰参数联动表 
                    WHERE 主参数名称 = %s AND 主参数值 = %s AND 被联动参数名称 = %s
                """
                cur.execute(sql, ("支座标准", support_standard, "支座型号"))
                result = cur.fetchone()
                
                # 查找支座型号行
                for row in range(table.rowCount()):
                    pitem = table.item(row, param_col)
                    if pitem and pitem.text().strip() == "支座型号":
                        # 从数据库获取选项
                        options = []
                        if result and result["联动选项"]:
                            # 解析JSON数组
                            try:
                                import json
                                options = json.loads(result["联动选项"])
                            except:
                                # 如果不是JSON，按逗号分割
                                options = [x.strip() for x in result["联动选项"].split(",") if x.strip()]
                        
                        # 更新下拉框选项
                        if options:
                            from modules.cailiaodingyi.controllers.combo import ComboDelegate
                            table.setItemDelegateForRow(row, ComboDelegate(options, table))
                            
                            # 只有在用户手动修改时才自动更新值
                            if auto_update:
                                if len(options) > 0:
                                    table.item(row, value_col).setText(options[0])
                                    print(f"[固定鞍座] 自动更新支座型号为第一个选项: {options[0]}")
                        else:
                            # 只有在用户手动修改时才清空
                            if auto_update:
                                table.item(row, value_col).setText("")
                                print(f"[固定鞍座] 清空支座型号")
                        break
        finally:
            conn.close()
    except Exception as e:
        print(f"[更新支座型号选项] 失败: {e}")


def update_component_name_options(table, support_type, param_col, value_col, auto_update=True):
    """根据支座型式更新元件名称选项 - 从数据库读取联动规则并过滤已选择的选项"""
    try:
        from modules.cailiaodingyi.db_cnt import get_connection
        from modules.cailiaodingyi.funcs.funcs_pdf_change import db_config_2
        from PyQt5.QtWidgets import QLineEdit
        from PyQt5.QtCore import Qt
        
        # 直接从数据库查询联动规则
        conn = get_connection(**db_config_2)
        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT 联动选项 
                    FROM 法兰参数联动表 
                    WHERE 主参数名称 = %s AND 主参数值 = %s AND 被联动参数名称 = %s
                """
                cur.execute(sql, ("支座型式", support_type, "元件名称"))
                result = cur.fetchone()
                
                # 查找元件名称行
                for row in range(table.rowCount()):
                    pitem = table.item(row, param_col)
                    if pitem and pitem.text().strip() == "元件名称":
                        # 从数据库获取选项并解析JSON数组
                        all_options = []
                        if result and result["联动选项"]:
                            raw_text = result["联动选项"].strip()
                            try:
                                import json
                                # 解析JSON数组
                                all_options = json.loads(raw_text)
                                print(f"[固定鞍座] 联动解析元件名称JSON: {raw_text} -> {all_options}")
                            except json.JSONDecodeError:
                                # 如果不是JSON，按逗号分割
                                all_options = [x.strip() for x in raw_text.split(",") if x.strip()]
                                print(f"[固定鞍座] 联动按逗号分割元件名称: {raw_text} -> {all_options}")
                        
                        # 获取其他Tab页已选择的元件名称
                        selected_in_other_tabs = get_selected_component_names_for_fixed_saddle(table, support_type)
                        print(f"[固定鞍座] 其他Tab页已选择的元件名称: {selected_in_other_tabs}")
                        
                        # 过滤掉已选择的选项
                        available_options = [opt for opt in all_options if opt not in selected_in_other_tabs]
                        print(f"[固定鞍座] 当前Tab页可选的元件名称: {available_options}")
                        
                        # 根据可用选项数量决定使用下拉框还是文本框
                        if available_options:
                            # 有可选选项，使用复选下拉框
                            from modules.cailiaodingyi.controllers.checkcombo import CheckComboDelegate
                            table.setItemDelegateForRow(row, CheckComboDelegate(available_options, table))
                            
                            # 不要自动更新值，保持当前数据库中的值
                            # 让UI从数据库重新加载数据时显示正确的值
                            print(f"[固定鞍座] 设置元件名称下拉框，可用选项: {available_options}")
                        else:
                            # 没有可选选项，使用文本框
                            print(f"[固定鞍座] 没有可选元件名称，切换到文本框")
                            table.setItemDelegateForRow(row, None)  # 移除下拉框代理
                            
                            # 只有在用户手动修改时才清空
                            if auto_update:
                                table.item(row, value_col).setText("")
                                print(f"[固定鞍座] 清空元件名称")
                        break
        finally:
            conn.close()
    except Exception as e:
        print(f"[更新元件名称选项] 失败: {e}")


def get_selected_component_names_for_fixed_saddle(table, support_type):
    """获取其他Tab页已选择的元件名称"""
    try:
        # 获取viewer_instance
        viewer_instance = getattr(table, '_viewer_instance', None)
        if not viewer_instance:
            print("[固定鞍座] 未找到viewer_instance，无法获取其他Tab页数据")
            return []
        
        # 获取当前Tab页名称
        current_tab_name = getattr(table, '_current_tab_name', None)
        if not current_tab_name:
            print("[固定鞍座] 未找到当前Tab页名称")
            return []
        
        # 从数据库查询其他Tab页已选择的元件名称
        product_id = getattr(viewer_instance, 'product_id', None)
        element_id = getattr(viewer_instance, 'clicked_element_data', {}).get('元件ID', '')
        
        if not product_id or not element_id:
            print("[固定鞍座] 缺少product_id或element_id")
            return []
        
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                sql = """
                SELECT 参数值
                FROM 产品设计活动表_元件附加参数合并表
                WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '元件名称' 
                AND Tab分类 != %s AND 参数值 != '' AND 参数值 != '[]'
                """
                cursor.execute(sql, (product_id, element_id, current_tab_name))
                results = cursor.fetchall()
                
                selected_names = []
                for row in results:
                    param_value = row.get('参数值', '')
                    if param_value:
                        try:
                            import json
                            # 解析JSON数组
                            names = json.loads(param_value)
                            if isinstance(names, list):
                                selected_names.extend(names)
                        except json.JSONDecodeError:
                            # 如果不是JSON，按"、"分割
                            names = [x.strip() for x in param_value.split('、') if x.strip()]
                            selected_names.extend(names)
                
                # 去重
                selected_names = list(set(selected_names))
                print(f"[固定鞍座] 其他Tab页已选择的元件名称: {selected_names}")
                return selected_names
                
        finally:
            connection.close()
            
    except Exception as e:
        print(f"[固定鞍座] 获取其他Tab页已选择元件名称失败: {e}")
        return []


def get_component_name_options_from_db(table, param_col, value_col):
    """从数据库获取元件名称选项"""
    try:
        # 查找元件名称行
        for row in range(table.rowCount()):
            pitem = table.item(row, param_col)
            if pitem and pitem.text().strip() == "元件名称":
                # 从数据库获取JSON数组并解析
                # 这里暂时返回硬编码的选项，后续可以从数据库获取
                options = ["底板", "腹板", "筋板", "垫板", "盖板"]
                return options
        return []
    except Exception as e:
        print(f"[获取元件名称选项] 失败: {e}")
        return []
        
        # 创建多选控件
        widget = create_multi_select_component_name_widget(options, current_value, viewer_instance)
        
        if widget:
            # 设置到表格
            table.setItem(row, col, None)
            table.setCellWidget(row, col, widget)
        
    except Exception as e:
        print(f"[固定鞍座] 多选元件名称控件设置失败: {e}")


def setup_component_name_combobox(table, row, col, current_value, viewer_instance):
    """设置元件名称下拉框（可复选）"""
    try:
        from PyQt5.QtWidgets import QComboBox, QCheckBox
        from PyQt5.QtCore import Qt
        
        # 获取支座型式
        support_type = get_support_type_from_data(viewer_instance)
        
        # 根据支座型式获取可选的元件名称
        options = get_component_name_options(support_type)
        
        # 创建下拉框
        combo = QComboBox()
        combo.setEditable(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo.setStyleSheet("""
            QComboBox {
                border: none;
                background-color: transparent;
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding-left: 2px;
            }
        """)
        
        # 添加选项
        combo.addItems(options)
        
        # 设置当前值
        if current_value:
            # 解析JSON数组格式的值
            try:
                import json
                selected_values = json.loads(current_value) if current_value.startswith('[') else [current_value]
                combo.setCurrentText(', '.join(selected_values))
            except:
                combo.setCurrentText(current_value)
        
        # 设置到表格
        table.setItem(row, col, None)
        table.setCellWidget(row, col, combo)
        
        # 绑定变化事件
        combo.currentTextChanged.connect(lambda: on_component_name_changed(table, row, col, combo, viewer_instance))
        
    except Exception as e:
        print(f"[固定鞍座] 元件名称下拉框设置失败: {e}")


def create_multi_select_component_name_widget(options, current_value, viewer_instance):
    """创建多选元件名称控件"""
    try:
        from PyQt5.QtWidgets import QWidget, QVBoxLayout, QCheckBox, QPushButton, QLabel
        from PyQt5.QtCore import Qt
        
        # 解析当前选中的值
        selected_values = []
        if current_value:
            try:
                import json
                selected_values = json.loads(current_value) if current_value.startswith('[') else [current_value]
            except:
                selected_values = [current_value] if current_value else []
        
        # 创建主容器
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(2, 2, 2, 2)
        
        # 创建标签显示当前选择
        label = QLabel(', '.join(selected_values) if selected_values else '请选择元件名称')
        label.setStyleSheet("""
            QLabel {
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding: 2px;
                border: 1px solid #ccc;
                background-color: white;
            }
        """)
        layout.addWidget(label)
        
        # 创建选择按钮
        select_btn = QPushButton("选择元件名称")
        select_btn.setStyleSheet("""
            QPushButton {
                font-size: 8pt;
                font-family: "Microsoft YaHei";
                padding: 2px;
                border: 1px solid #ccc;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        layout.addWidget(select_btn)
        
        # 绑定按钮点击事件
        select_btn.clicked.connect(lambda: show_component_name_dialog(widget, options, selected_values, label, viewer_instance))
        
        return widget
        
    except Exception as e:
        print(f"[固定鞍座] 多选元件名称控件创建失败: {e}")
        return None


def show_component_name_dialog(parent_widget, options, current_selected, label, viewer_instance):
    """显示元件名称选择对话框"""
    try:
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QCheckBox, QPushButton, QLabel
        from PyQt5.QtCore import Qt
        
        # 创建对话框
        dialog = QDialog(parent_widget)
        dialog.setWindowTitle("选择元件名称")
        dialog.setModal(True)
        dialog.resize(300, 200)
        
        layout = QVBoxLayout(dialog)
        
        # 添加说明标签
        info_label = QLabel("请选择需要的元件名称（可多选）：")
        info_label.setStyleSheet("font-size: 9pt; font-family: 'Microsoft YaHei'; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # 创建复选框
        checkboxes = {}
        for option in options:
            cb = QCheckBox(option)
            cb.setChecked(option in current_selected)
            cb.setStyleSheet("font-size: 9pt; font-family: 'Microsoft YaHei'; margin: 2px;")
            checkboxes[option] = cb
            layout.addWidget(cb)
        
        # 创建按钮
        btn_layout = QHBoxLayout()
        
        ok_btn = QPushButton("确定")
        ok_btn.setStyleSheet("""
            QPushButton {
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding: 5px 15px;
                border: 1px solid #ccc;
                background-color: #0078d4;
                color: white;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.setStyleSheet("""
            QPushButton {
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding: 5px 15px;
                border: 1px solid #ccc;
                background-color: #f0f0f0;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)
        
        # 绑定事件
        def on_ok():
            selected = [option for option, cb in checkboxes.items() if cb.isChecked()]
            if selected:
                label.setText(', '.join(selected))
                # 保存到数据库
                save_component_name_selection(selected, viewer_instance)
            else:
                label.setText('请选择元件名称')
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)
        
        # 显示对话框
        dialog.exec_()
        
    except Exception as e:
        print(f"[固定鞍座] 元件名称选择对话框显示失败: {e}")


def save_component_name_selection(selected_values, viewer_instance):
    """保存元件名称选择到数据库"""
    try:
        import json
        
        # 将选择的值转换为JSON格式
        json_value = json.dumps(selected_values, ensure_ascii=False)
        
        # 更新数据库
        product_id = viewer_instance.product_id
        element_id = getattr(viewer_instance, 'clicked_element_data', {}).get('元件ID', '')
        
        if product_id and element_id:
            update_element_para_data(product_id, element_id, '元件名称', json_value)
            print(f"[固定鞍座] 元件名称选择已保存: {json_value}")
        
    except Exception as e:
        print(f"[固定鞍座] 元件名称选择保存失败: {e}")


def setup_material_combobox(table, row, col, param_name, current_value, viewer_instance):
    """设置材料字段下拉框（联动）"""
    try:
        from PyQt5.QtWidgets import QComboBox
        from PyQt5.QtCore import Qt
        
        # 获取选项
        options = get_material_options(param_name, viewer_instance)
        
        # 创建下拉框
        combo = QComboBox()
        combo.setEditable(True)
        combo.lineEdit().setAlignment(Qt.AlignCenter)
        combo.setStyleSheet("""
            QComboBox {
                border: none;
                background-color: transparent;
                font-size: 9pt;
                font-family: "Microsoft YaHei";
                padding-left: 2px;
            }
        """)
        
        # 添加选项
        combo.addItems(options)
        
        # 设置当前值
        combo.setCurrentText(current_value)
        
        # 设置到表格
        table.setItem(row, col, None)
        table.setCellWidget(row, col, combo)
        
        # 绑定变化事件
        combo.currentTextChanged.connect(lambda: on_material_field_changed(table, row, col, param_name, combo, viewer_instance))
        
    except Exception as e:
        print(f"[固定鞍座] 材料字段下拉框设置失败: {e}")


def get_support_type_from_data(viewer_instance):
    """从数据中获取支座型式"""
    try:
        # 从固定鞍座数据中查找支座型式
        saddle_data = getattr(viewer_instance, 'fixed_saddle_data', [])
        for item in saddle_data:
            if item.get('参数名称') == '支座型式':
                return item.get('参数值', '')
        return '鞍式支座'  # 默认值
    except:
        return '鞍式支座'


def get_component_name_options(support_type):
    """根据支座型式获取元件名称选项"""
    options_map = {
        '鞍式支座': ['底板', '腹板', '筋板', '垫板'],
        '耳式支座': ['底板', '筋板', '垫板', '盖板']
    }
    return options_map.get(support_type, ['底板', '腹板', '筋板', '垫板'])


def get_material_options(param_name, viewer_instance):
    """获取材料字段选项"""
    try:
        # 这里可以调用现有的材料选项获取函数
        from modules.cailiaodingyi.controllers.datamanager import get_filtered_material_options
        return get_filtered_material_options(param_name, viewer_instance.product_id)
    except:
        return []


def on_component_name_changed(table, row, col, combo, viewer_instance):
    """元件名称变化事件处理"""
    try:
        new_value = combo.currentText()
        print(f"[固定鞍座] 元件名称变化: {new_value}")
        
        # 这里可以添加保存到数据库的逻辑
        # 也可以添加联动逻辑，比如根据选择的元件名称更新其他字段
        
    except Exception as e:
        print(f"[固定鞍座] 元件名称变化处理失败: {e}")


def on_material_field_changed(table, row, col, param_name, combo, viewer_instance):
    """材料字段变化事件处理"""
    try:
        new_value = combo.currentText()
        print(f"[固定鞍座] {param_name}变化: {new_value}")
        
        # 保存到数据库
        product_id = viewer_instance.product_id
        element_id = getattr(viewer_instance, 'clicked_element_data', {}).get('元件ID', '')
        
        if product_id and element_id:
            update_element_para_data(product_id, element_id, param_name, new_value)
            print(f"[固定鞍座] {param_name}已保存到数据库: {new_value}")
        
        # 材料联动逻辑
        if param_name == '材料类型':
            # 材料类型变化时，更新其他材料字段的选项
            update_material_dependent_fields(table, row, new_value, viewer_instance)
        
    except Exception as e:
        print(f"[固定鞍座] 材料字段变化处理失败: {e}")


def update_material_dependent_fields(table, row, material_type, viewer_instance):
    """更新材料依赖字段"""
    try:
        # 定义材料字段及其行位置
        material_fields = {
            '材料牌号': 6,  # 第7行（索引6）
            '材料标准': 7,  # 第8行（索引7）
            '供货状态': 8   # 第9行（索引8）
        }
        
        # 根据材料类型更新选项
        for field_name, field_row in material_fields.items():
            # 获取新的选项
            new_options = get_material_options(field_name, viewer_instance)
            
            # 更新下拉框选项（值在第二列，索引1）
            combo = table.cellWidget(field_row, 1)
            if combo and hasattr(combo, 'clear'):
                combo.clear()
                combo.addItems(new_options)
                
                # 如果当前值不在新选项中，清空
                current_text = combo.currentText()
                if current_text and current_text not in new_options:
                    combo.setCurrentIndex(0)
        
    except Exception as e:
        print(f"[固定鞍座] 材料依赖字段更新失败: {e}")


def handle_fixed_saddle_table_click(viewer_instance, row, col):
    """处理固定鞍座表格点击事件"""
    print(f"[固定鞍座] 表格点击: 行{row}, 列{col}")
    
    # 获取当前点击行的数据
    clicked_saddle_data = getattr(viewer_instance, 'fixed_saddle_data', [])
    if row < len(clicked_saddle_data):
        clicked_item = clicked_saddle_data[row]
        print(f"[固定鞍座] 点击的数据: {clicked_item}")
        viewer_instance.clicked_fixed_saddle_data = clicked_item






