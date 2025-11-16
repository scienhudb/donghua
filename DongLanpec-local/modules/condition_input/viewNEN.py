import sys

from PyQt5 import uic
from PyQt5.QtGui import QPixmap, QPainter, QFont
from PyQt5.QtWidgets import QWidget, QMessageBox, QFileDialog, QApplication, QToolTip
from PyQt5.QtCore import QTimer, Qt
import os

from PyQt5.QtCore import QEvent
from PyQt5.QtWidgets import QTableWidgetItem
from modules.condition_input.funcs.multi_conditions_dialog import MultiConditionsDialog
from PyQt5.QtWidgets import QMessageBox, QPushButton

# 导入功能函数
from modules.condition_input.funcs.funcs_product_info import check_pdt_define, check_has_any_product
from modules.condition_input.funcs.ctrl_helper import enable_full_undo
from modules.condition_input.funcs.funcs_cdt_input import load_design_data_if_exists, render_grouped_table, \
    render_coating_table, set_multilevel_headers, apply_table_style, highlight_missing_required_rows, \
    validate_required_fields, import_all_reference_data, save_local_condition_file, save_all_tables, \
    trigger_all_cross_table_relations, apply_design_data_dropdowns, apply_general_data_dropdowns, \
    apply_trail_data_dropdowns, TrailTableComboDelegate, highlight_entire_row, shrink_index_column, shrink_unit_column,\
    get_ref_data_excel_path, fetch_all_mode_orders, capture_default_order, apply_mode_param_order
from modules.chanpinguanli.chanpinguanli_main import product_manager
from modules.condition_input.funcs.design_data_delegate import DesignDataDelegate  # 根据实际路径调整
from modules.yudingyi.luoshuan import update_user_config_for_2_6_1
from modules.chanpinguanli.project_confirm_btn import show_confirm_dialog
product_id = None


def on_product_id_changed(new_id):
    print(f"Received new PRODUCT_ID: {new_id}")
    global product_id
    product_id = new_id


# 测试用产品 ID（真实情况中由外部输入）
product_manager.product_id_changed.connect(on_product_id_changed)


#0903会议纪要 添加一个通用的检查函数，用于所有非项目管理界面
def check_project_and_product():
    """检查项目和产品状态的通用函数（修复变量引用问题）"""
    # 关键修改：直接通过bianl模块访问current_project_id
    from modules.chanpinguanli import bianl
    # 打印调试信息，确认获取的项目ID
    print(f"检查函数中获取的项目ID: {repr(bianl.current_project_id)}")
    # 检查项目ID是否有效
    if not bianl.current_project_id or str(bianl.current_project_id).strip() == "":
        return False, "请先创建项目和产品！"
    # 检查当前项目下是否有产品
    if not check_has_any_product(bianl.current_project_id):
        return False, "请先创建至少一个产品！"
    return True, ""

class DesignConditionInputViewer(QWidget):
    def __init__(self, line_tip=None):
        super().__init__()

        # ▼▼▼【核心修改 1】在最开始初始化状态变量 ▼▼▼
        self._is_modified = False     # 关键！追踪界面数据是否被修改
        self._is_loading_data = True  # 关键！开始初始化，标记为“正在加载”
        self.original_window_title = ""  # UI加载后赋值


        # 0903会议纪要 首先进行项目和产品检查
        print("准备检查项目和产品状态...")
        can_open, msg = check_project_and_product()
        if not can_open:
            QMessageBox.information(self, "提示", msg)
            self.deleteLater()  # 不打开界面
            return  # 立即返回

        current_dir = os.path.dirname(os.path.abspath(__file__))
        ui_path = os.path.join(current_dir, "viewer.ui")
        uic.loadUi(ui_path, self)
        # ▼▼▼【修改点 1.2】UI加载后获取标题 ▼▼▼
        self.original_window_title = self.windowTitle()

        self.product_id = product_id
        self.line_tip = line_tip

        screen_geometry = QApplication.desktop().screenGeometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()
        target_width = int(screen_width * 0.7)
        target_height = int(screen_height * 0.7)
        self.resize(target_width, target_height)
        self.move((screen_width - target_width) // 2, (screen_height - target_height) // 2)

        QToolTip.setFont(QFont("Microsoft YaHei", 12))

        # 1014lxy
        # ========== 新增：初始化提示定时器 ==========
        self.tip_timer = QTimer(self)  # 创建定时器实例
        self.tip_timer.setSingleShot(True)  # 仅触发一次（避免重复清空）
        self.tip_timer.timeout.connect(self.clear_line_tip)  # 超时后调用清空方法
        # self.product_id = product_id
        self._is_valid_product = True
        self._early_tip_msg = ""

        # self._is_modified = False
        self._validation_triggered = False  # <---lxy101 新增：验证触发标志，默认为 False

        if not self.product_id:
            self._is_valid_product = False
            self._early_tip_msg = "请先至项目管理处选择产品！"
        elif not check_pdt_define(self.product_id):
            self._is_valid_product = False
            self._early_tip_msg = "请先至项目管理处对当前产品进行定义！"

        # 统一处理提示
        if not self._is_valid_product:
            if self.line_tip:
                self.line_tip.setText(self._early_tip_msg)
                self.line_tip.setToolTip(self._early_tip_msg)
            self.setDisabled(True)  # 禁用界面交互
            self._original_pixmap = None
            return  # 如果你仍想中断后续数据加载逻辑，可以留这个 return，但控件已完整初始化

        self._is_loading_data = True

        # === 模式下拉初始化 === 新增
        try:
            self._mode_orders = fetch_all_mode_orders()  # {模式名: [id...]}
        except Exception:
            self._mode_orders = {}

        self._default_mode_name = "设计模式"
        combo = getattr(self, "combo_mode", None)  # 直接取 UI 里的 combo_mode

        if combo is None:
            print("[ERR][init] 在 UI 里没有找到 combo_mode，请确认 .ui 文件里对象名是否为 'combo_mode'")
        else:
            combo.blockSignals(True)
            combo.clear()
            if self._default_mode_name not in self._mode_orders:
                combo.addItem(self._default_mode_name)
            else:
                other_modes = [m for m in self._mode_orders if m != self._default_mode_name]
                combo.addItems([self._default_mode_name] + other_modes)
                print(f"[DBG][init] 填充模式列表: {[combo.itemText(i) for i in range(combo.count())]}")
            combo.blockSignals(False)
            # 禁用鼠标滚轮切换模式，避免误操作
            try:
                combo.installEventFilter(self)
            except Exception as _:
                pass

            # 确保 on_mode_changed 已定义
            if hasattr(self, "on_mode_changed") and callable(self.on_mode_changed):
                combo.currentTextChanged.connect(self.on_mode_changed)
                combo.currentTextChanged.connect(lambda: setattr(self, "_is_modified", True))
            else:
                print("[ERR][init] 没有定义 on_mode_changed 方法，无法连接信号")

        self.btn_inputrefdata.clicked.connect(self.on_input_ref_data_clicked)
        self.btn_confirm.clicked.connect(lambda: self.check_and_save_data(force=True))
        self.btn_output.clicked.connect(self.export_condition_file)
        self.import_condition_data(self.product_id)

        tables = [
            self.tableWidget_design_data,
            self.tableWidget_general_data,
            self.tableWidget_product_std,
            self.tableWidget_trail_data,
            self.tableWidget_coating_data
        ]
        for table in tables:
            font_metrics = table.fontMetrics()
            header_height = font_metrics.height() + 12
            table.horizontalHeader().setFixedHeight(header_height)

        for table in tables:
            apply_table_style(table)

        if self._is_valid_product:
            # 新增
            for table1 in [
                self.tableWidget_design_data,
                self.tableWidget_general_data,
                self.tableWidget_product_std
            ]:
                shrink_index_column(table1, width=100)

            # 新增
            for table2 in [
                self.tableWidget_design_data,
                self.tableWidget_general_data
            ]:
                shrink_unit_column(table2, width=200)

        for table in tables:
            table.itemSelectionChanged.connect(lambda t=table: highlight_entire_row(t))
        design_config = apply_design_data_dropdowns(product_id=self.product_id)
        general_config = apply_general_data_dropdowns()
        trail_config = apply_trail_data_dropdowns()
        enable_full_undo(self.tableWidget_product_std, self, mode="product")
        enable_full_undo(self.tableWidget_design_data, self, mode="design", dropdown_config=design_config)
        enable_full_undo(self.tableWidget_general_data, self, mode="general", dropdown_config=general_config)
        enable_full_undo(self.tableWidget_coating_data, self, mode="coating")
        trail_delegate = TrailTableComboDelegate(config=trail_config, parent=self.tableWidget_trail_data)
        for col in [2, 4, 5, 7]:
            self.tableWidget_trail_data.setItemDelegateForColumn(col, trail_delegate)

        from modules.condition_input.funcs.ctrl_helper import DropDownClickOnlyFilter
        filter = DropDownClickOnlyFilter(self.tableWidget_trail_data, trail_delegate)
        self.tableWidget_trail_data.viewport().installEventFilter(filter)

        enable_full_undo(self.tableWidget_trail_data, self, mode="trail")
        self.tableWidget_trail_data.viewer = self
        self.tableWidget_trail_data.undo_stack = self.undo_stack

        # ===lxy101 核心修改点 1: 连接信号与槽函数 ===

        # 为所有表格的撤销/重做操作添加 _is_modified 标记 1014
        for table in tables:
            if hasattr(table, "undo_stack"):
                table.undo_stack.indexChanged.connect(self.mark_as_modified)
                # table.undo_stack.indexChanged.connect(lambda: setattr(self, "_is_modified", True))
        combo = getattr(self, "combo_mode", None)
        if combo:
             combo.currentTextChanged.connect(lambda: self.mark_as_modified())

        # 只对“设计数据”表开启单击打开多工况窗口
        self.tableWidget_design_data.viewport().installEventFilter(self)
        self._is_loading_data = False
        # 应用自定义代理显示多工况标识
        if hasattr(self, 'tableWidget_design_data') and self.tableWidget_design_data is not None:
            self.design_delegate = DesignDataDelegate()
            self.tableWidget_design_data.setItemDelegateForColumn(1, self.design_delegate)
            self.tableWidget_design_data.viewer = self
        # 所有数据加载和UI设置完成后，更新状态标志
        self._is_loading_data = False
        tables = [
            self.tableWidget_design_data,
            self.tableWidget_general_data,
            self.tableWidget_product_std,
            self.tableWidget_trail_data,
            self.tableWidget_coating_data
        ]

        # 用一个循环为所有表格连接 itemChanged 信号
        for table in tables:
            # itemChanged 是当一个单元格(item)的数据发生变化时发出的信号
            table.itemChanged.connect(self.mark_as_modified)
            # 1015 为需要实时校验的表格，额外连接到 handle_cell_input ▼▼▼
            if table in [self.tableWidget_design_data, self.tableWidget_general_data]:
                table.itemChanged.connect(self.handle_cell_input)

    # 1014lxy
    def mark_as_modified(self, item=None): # item参数设为可选
        """当任何数据被用户改变时，将界面标记为已修改"""
        # 正在加载数据时，任何信号都忽略
        if self._is_loading_data:
            return

        # 如果已经标记过了，就不用重复操作了
        if self._is_modified:
            return

        self._is_modified = True
        # 在窗口标题上加一个星号，给用户直观提示
        self.setWindowTitle(f"{self.original_window_title}*")
        print("条件输入界面已被修改，标记完成。")

    # 修改后 (弹窗提示)
    def can_be_closed(self):
        """
        供主窗口调用的关闭检查接口。
        - 如果没有修改，直接返回 True。
        - 如果有修改，弹窗询问用户操作（保存/不保存/取消）。
        返回: bool -> 是否可以安全关闭
        """
        # 1. 如果没有被修改过，直接告诉主窗口“可以关闭”
        if not self._is_modified:
            return True

        # 2. 如果有修改，弹出提示框询问用户
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setWindowTitle("确认关闭")
        msg_box.setText(f"文档 '{self.original_window_title}' 有未保存的更改。")
        msg_box.setInformativeText("有修改项未被保存，是否在关闭前保存更改？")

        # 添加三个标准按钮
        save_button = msg_box.addButton("是", QMessageBox.AcceptRole)
        discard_button = msg_box.addButton("否", QMessageBox.DestructiveRole)
        cancel_button = msg_box.addButton("取消", QMessageBox.RejectRole)

        msg_box.setDefaultButton(save_button)  # 默认选中“保存”

        msg_box.exec_()

        clicked_button = msg_box.clickedButton()

        # 3. 根据用户的选择执行相应操作
        if clicked_button == save_button:
            # 用户选择“保存”
            print("用户选择保存。")
            try:
                # 执行核心保存操作
                if not save_local_condition_file(self.product_id, self):
                    raise IOError("保存本地条件文件失败。")
                save_all_tables(self, self.product_id)

                # 保存成功后，重置状态并允许关闭
                self._is_modified = False
                self.setWindowTitle(self.original_window_title)
                print("保存成功！现在可以关闭。")
                if hasattr(self, 'line_tip') and self.line_tip:
                    self.line_tip.setText("关闭前保存成功！")
                    self.line_tip.setStyleSheet("color: black;")  # 确保设置黑色
                    self.line_tip.setToolTip("关闭前保存成功！")
                    if hasattr(self, 'tip_timer'):
                        self.tip_timer.start(5000)
                return True  # 返回 True，主窗口继续关闭

            except Exception as e:
                # 如果保存失败，弹窗提示并阻止关闭
                print(f"保存失败，无法关闭: {e}")
                QMessageBox.critical(self, "保存失败", f"保存数据时发生错误，关闭操作已取消。\n\n错误信息: {e}")
                return False  # 返回 False，主窗口中断关闭

        elif clicked_button == discard_button:
            # 用户选择“不保存”
            print("用户选择不保存，直接关闭。")
            # 直接允许关闭
            return True  # 返回 True，主窗口继续关闭

        elif clicked_button == cancel_button:
            # 用户选择“取消”
            print("用户取消了关闭操作。")
            # 阻止关闭
            return False  # 返回 False，主窗口中断关闭

        # 以防万一用户直接关闭了提示框，也当作取消
        return False
    # def can_be_closed(self): 无弹窗提示直接关闭版
    #     """
    #     供主窗口调用的关闭检查接口。
    #     - 如果没有修改，直接返回 True。
    #     - 如果有修改，自动执行静默保存 (不弹窗询问必填项)。
    #     - 保存成功，返回 True。
    #     - 保存失败，弹窗提示并返回 False。
    #     返回: bool -> 是否可以安全关闭
    #     """
    #     # 如果没有被修改过，直接告诉主窗口“可以关闭”
    #     if not self._is_modified:
    #         print("条件输入界面无修改，可直接关闭。")
    #         return True
    #
    #     print("检测到未保存的修改，正在自动静默保存...")
    #
    #     try:
    #         # 执行核心保存操作，不进行UI交互（如弹窗询问）
    #         if not save_local_condition_file(self.product_id, self):
    #             raise IOError("保存本地条件文件失败。")
    #         save_all_tables(self, self.product_id)
    #
    #         # 保存成功后，重置状态
    #         self._is_modified = False
    #         self.setWindowTitle(self.original_window_title)
    #
    #         print("自动保存成功！可以关闭。")
    #         if hasattr(self, 'line_tip') and self.line_tip:
    #             self.line_tip.setText("关闭前自动保存成功！")
    #             if hasattr(self, 'tip_timer'):
    #                 self.tip_timer.start(5000)
    #
    #         return True  # 返回成功，主窗口可以继续关闭操作
    #
    #     except Exception as e:
    #         print(f"自动保存失败，无法关闭: {e}")
    #         QMessageBox.critical(self, "保存失败", f"自动保存数据时发生错误，关闭操作已取消。\n\n错误信息: {e}")
    #         return False  # 返回失败，主窗口将中断关闭操作
# lxy1014
    def clear_line_tip(self):
        """5秒后自动清空line_tip的文本和样式（避免残留）"""
        # 先判断line_tip是否存在，防止空指针错误
        if hasattr(self, "line_tip") and self.line_tip:
            self.line_tip.setText("")  # 清空提示文本
            self.line_tip.setStyleSheet("")  # 恢复默认样式（若之前设置过颜色）
            self.line_tip.setToolTip("")  # 清空 tooltip（可选）

    def import_condition_data(self, product_id):
        if not product_id:
            return

        # 调用函数获取产品形式，如果找不到或出错，则默认为 'all'
        from main import get_product_form_from_db
        product_form = get_product_form_from_db(product_id) or "all"
        print(f"当前产品ID: {product_id}, 获取到的产品型式: {product_form}")

        result = load_design_data_if_exists(product_id, product_form)

        if not result or not result.get("import_status"):
            QMessageBox.information(self, "提示", "未找到设计数据，表格将保持为空。")
            return

        self.design_data_source = result["data_source_status"]
        print(f"数据来源：{self.design_data_source}")

        # ❗️没有导入数据，提示后返回（错误/空数据情况需要用户知道）
        if not result.get("import_status", False):
            QMessageBox.information(self, "提示", "未在产品设计活动库中找到该产品的设计数据。")
            return

        # ✅ 成功导入时不弹窗，用 print 或 QLabel 替代
        data = result["数据"]
        print("✅ 成功导入产品设计活动数据")  # 或界面提示也可

        self.fill_table_widget(
            self.tableWidget_product_std,
            data["产品标准"]["headers"],
            data["产品标准"]["rows"],
            index_header=data["产品标准"].get("prepend_index_header")
        )
        self.fill_table_widget(
            self.tableWidget_design_data,
            data["设计数据"]["headers"],
            data["设计数据"]["rows"],
            index_header=data["设计数据"].get("prepend_index_header")
        )
        self.fill_table_widget(
            self.tableWidget_general_data,
            data["通用数据"]["headers"],
            data["通用数据"]["rows"],
            index_header=data["通用数据"].get("prepend_index_header")
        )

        # === 记录默认顺序（用于保存/导出固定顺序写出）===
        #capture_default_order(self.tableWidget_product_std)
        capture_default_order(self.tableWidget_design_data)
        #capture_default_order(self.tableWidget_general_data)

        set_multilevel_headers(
            self.tableWidget_trail_data,
            top_headers=["接头种类", "检测方法", "壳程", "管程"],
            sub_headers=["", "", "技术等级", "检测比例%", "合格级别", "技术等级", "检测比例%", "合格级别"],
            span_map=[(0, 1), (1, 1), (2, 3), (5, 3)]
        )
        self.render_grouped_table(
            self.tableWidget_trail_data,
            data["检测数据"]["格式化"],
            [
                "接头种类", "检测方法",
                "壳程_技术等级", "壳程_检测比例", "壳程_合格级别",
                "管程_技术等级", "管程_检测比例", "管程_合格级别"
            ],
            group_key_column=0
        )
        # 导入涂漆数据，执行标准/规范从产品标准中取值
        # 在导入涂漆数据之前加入以下代码
        product_std_rows = data["产品标准"]["rows"]
        coating_std_value = ""
        for row in product_std_rows:
            if row.get("规范/标准名称", "").strip() == "涂漆标准":
                coating_std_value = row.get("规范/标准代号", "").strip()
                break
        render_coating_table(self.tableWidget_coating_data, data["涂漆数据"]["格式化"], coating_std_value)
        if hasattr(self, 'undo_stack'):
            self.undo_stack.clear()
        # 专门用于触发“绝热层类型”的联动
        trigger_all_cross_table_relations(self)
        # 新增：数据导入后清除高亮lxy101
        self.clear_all_highlights()

    def fill_table_widget(self, table_widget, headers, rows, index_header=None):
        """
        填充 QTableWidget 的通用方法
        """
        # === 新增：仅在设计数据表中过滤掉 [工况] 参数 ===
        if table_widget.objectName() == "tableWidget_design_data":
            before = len(rows)
            rows = [row for row in rows if "[工况" not in str(row.get("参数名称", ""))]
            after = len(rows)
            print(f"[过滤] 设计数据表: 原始 {before} 行, 过滤后 {after} 行")

            # ✅ 新增：重新分配连续的序号
            if index_header and rows:
                for idx, row in enumerate(rows):
                    row[index_header] = idx + 1  # 重新分配从1开始的连续序号
                print(f"[序号重分配] 设计数据表: 已重新分配 {len(rows)} 个连续序号")

        # === 下面保持你原来的逻辑不变 ===
        clean_headers = headers.copy()
        if index_header in clean_headers:
            clean_headers.remove(index_header)

        extra_col = 1 if index_header else 0
        table_widget.clear()
        table_widget.setColumnCount(len(clean_headers) + extra_col)
        table_widget.setRowCount(len(rows))

        header_labels = [index_header] + clean_headers if index_header else clean_headers

        for col_index, header_text in enumerate(header_labels):
            display_text = "序号" if index_header and col_index == 0 else header_text
            item = QTableWidgetItem(display_text)
            item.setData(Qt.UserRole, header_text)  # ✅ 存储真实字段名
            item.setTextAlignment(Qt.AlignCenter)
            font = item.font()
            font.setBold(True)
            item.setFont(font)
            item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            table_widget.setHorizontalHeaderItem(col_index, item)

        table_widget.verticalHeader().setVisible(False)

        for row_idx, row in enumerate(rows):
            if index_header:
                index_value = row.get(index_header, "")
                index_item = QTableWidgetItem(str(index_value))
                index_item.setTextAlignment(Qt.AlignCenter)
                index_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                table_widget.setItem(row_idx, 0, index_item)

            for col_idx, key in enumerate(clean_headers):
                value = str(row.get(key, ""))
                item = QTableWidgetItem(value)

                is_name_column = col_idx == 0
                is_code_column = key == "规范/标准代号"
                is_unit_column = key == "参数单位"  # 修改
                if is_name_column:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                elif is_unit_column:  # 修改
                    item.setTextAlignment(Qt.AlignCenter)  # ✅ 居中
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # ✅ 不可编辑
                else:
                    if is_code_column:
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                    else:
                        item.setTextAlignment(Qt.AlignCenter)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEditable | Qt.ItemIsEnabled)

                table_widget.setItem(row_idx, col_idx + extra_col, item)

        # ✅ 仅对涂漆表设置 logical_headers，避免误操作其他表
        if table_widget.objectName() == "tableWidget_coating_data":
            table_widget.logical_headers = [
                "执行标准/规范", "用途", "油漆类别", "颜色", "干膜厚度（μm）", "涂漆面积", "备注"
            ]

        table_widget.resizeColumnsToContents()

    def on_input_ref_data_clicked(self):
        if not getattr(self, "_is_valid_product", True):
            self.line_tip.setText("当前未选择产品，无法导入参考数据")
            self.line_tip.setStyleSheet("color: black;")
            self.line_tip.setToolTip("当前未选择产品，无法导入参考数据")
            return
        try:
            # 弹出文件选择框
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "选择条件输入数据表",
                "",
                "Excel 文件 (*.xlsx);;所有文件 (*)"
            )
            if not file_path:
                return  # 用户取消选择，直接返回

            # 执行导入操作
            import_all_reference_data(file_path, self)
            QMessageBox.information(self, "成功", "成功导入参考数据！")

            # 关键：导入后标记为未保存 1014
            self._is_modified = True  # <--- 新增这一行

        except Exception as e:
            QMessageBox.critical(self, "导入失败", str(e))

    def render_grouped_table(self, table_widget, grouped_data, headers, group_key_column=0):
        render_grouped_table(table_widget, grouped_data, headers, group_key_column)

    # 保存及检查必填项 lxy1012
    # def check_and_save_data1(self, force=False, skip_confirm=False):
    #     """
    #     保存及检查必填项
    #     :param force: 是否强制保存（确认按钮时 True，切换/关闭时 False）
    #     :return: 检查结果 + 缺失字段（元组）
    #     """
    #     print(f"[调试] check_and_save_data：force={force}, _is_modified={self._is_modified}")  # 新增日志
    #     if not getattr(self, "_is_valid_product", True):
    #         return (True, [])  # 空界面不用保存，返回成功和空列表
    #
    #     try:
    #         # 新增：优先判断是否有未保存的修改
    #         if self._is_modified and not force:
    #             # 有未保存修改，且不是强制保存场景 → 阻止关闭
    #             return (False, [])
    #         # 检查必填项
    #         has_missing_dsg, missing_dsg = validate_required_fields(
    #             self.tableWidget_design_data, mode="设计数据"
    #         )
    #         has_missing_common, missing_common = validate_required_fields(
    #             self.tableWidget_general_data, mode="通用数据"
    #         )
    #
    #         missing_fields = [name for _, name in (missing_dsg + missing_common)]
    #
    #         # 1. 切换/关闭场景（force=False）：只检查不提示，返回检查结果和缺失字段
    #         if not force:
    #             # 高亮未填项
    #             if has_missing_dsg or has_missing_common:
    #                 self._validation_triggered = True
    #                 highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
    #                 highlight_missing_required_rows(self.tableWidget_general_data, missing_common)
    #                 return (False, missing_fields)  # 检查失败，返回缺失字段
    #             return (True, [])  # 检查通过
    #
    #         # 2. 主动保存场景（force=True）：有未填项时才弹提示
    #         if has_missing_dsg or has_missing_common:
    #             self._validation_triggered = True
    #             highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
    #             highlight_missing_required_rows(self.tableWidget_general_data, missing_common)
    #         self.tip_timer.stop()
    #         self.tip_timer.start(5000)
    #         self._is_modified = False
    #         return (True, [])
    #
    #     except Exception as e:
    #         QMessageBox.critical(self, "保存失败1", f"保存数据出错：\n{str(e)}")
    #         return (False, [])

    def only_check_validate_data(self, force=False):
        """
        仅用于检查必填项，并返回检查结果与未填写的必填项，不执行保存操作。
        返回：一个元组，(检查结果, 未填写的必填项列表)
        """
        if not getattr(self, "_is_valid_product", True):
            return True  # 如果产品有效则直接返回 True

        try:
            # 检查必填项
            has_missing_dsg, missing_dsg = validate_required_fields(
                self.tableWidget_design_data, mode="设计数据"
            )
            has_missing_common, missing_common = validate_required_fields(
                self.tableWidget_general_data, mode="通用数据"
            )

            missing_fields = [name for _, name in (missing_dsg + missing_common)]

            # 如果有缺失的必填项，进行高亮
            if has_missing_dsg or has_missing_common:
                self._validation_triggered = True  # 保留实时高亮逻辑
                highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
                highlight_missing_required_rows(self.tableWidget_general_data, missing_common)

                # 返回 False，表示有未填写的必填项
                return False,missing_fields

            # 如果没有缺失项，则返回 True
            return True,[]

        except Exception as e:
            print(f"检查数据出错：{str(e)}")
            return False,[]

    # 这个方法现在只由他将输入界面的“确认”按钮调用 (force=True)
    def check_and_save_data(self, force=False, skip_confirm=False):
        """
        【保留功能】仅用于用户点击“确认”按钮时，检查必填项并保存。
        """
        if not getattr(self, "_is_valid_product", True):
            return (True, [])

        try:
            # 检查必填项
            has_missing_dsg, missing_dsg = validate_required_fields(
                self.tableWidget_design_data, mode="设计数据"
            )
            has_missing_common, missing_common = validate_required_fields(
                self.tableWidget_general_data, mode="通用数据"
            )

            missing_fields = [name for _, name in (missing_dsg + missing_common)]

            if has_missing_dsg or has_missing_common:
                self._validation_triggered = True  # 保留您的实时高亮逻辑
                highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
                highlight_missing_required_rows(self.tableWidget_general_data, missing_common)

                # 保留您的弹窗询问逻辑
                if skip_confirm==False:
                    msg = ("以下必填项：\n" + "、".join(missing_fields) + "\n对应参数值不能为空。\n是否确认继续保存？")
                    if not show_confirm_dialog(self, "提示", msg):
                        return (False, missing_fields)

            # 执行保存操作
            if not save_local_condition_file(self.product_id, self):
                return (False, missing_fields)
            save_all_tables(self, self.product_id)
            update_user_config_for_2_6_1(product_id, json_path="modules/yudingyi/dn_pressure_table.json")


            # 保存成功后清理状态
            self._validation_triggered = False
            self.clear_all_highlights()
            self.line_tip.setText("保存成功！")
            self.line_tip.setToolTip("保存成功！")
            self.line_tip.setStyleSheet("color: black;")

            self.tip_timer.stop()
            self.tip_timer.start(5000)

            # 关键：保存成功后，重置修改状态
            self._is_modified = False
            self.setWindowTitle(self.original_window_title)  # 恢复窗口标题

            return (True, [])

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存数据出错：\n{str(e)}")
            return (False, [])

    def check_and_save_datagb(self, force=False, skip_confirm=False):
        """
        【调试专用版本】
        用于用户点击关闭界面时，检查必填项并保存。
        增加了详细的日志和对可疑函数的隔离。
        """
        print("\n--- [BUG HUNT] '条件输入'的 check_and_save_datagb 开始执行 ---")

        if not getattr(self, "_is_valid_product", True):
            print("[BUG HUNT] 1. _is_valid_product 为 False，提前退出。")
            return (True, [])

        try:
            # --- 调试步骤 1: 暂时绕过最可疑的函数 ---
            # 我们先假设没有缺失项，直接跳过 validate_required_fields 和 highlight_missing_required_rows
            # 如果这样就不再闪退，就证明 bug 就在这两个函数之一。
            print("[BUG HUNT] 2. 准备调用 validate_required_fields...")

            # ▼▼▼ 崩溃最可能发生在这里 ▼▼▼
            has_missing_dsg, missing_dsg = validate_required_fields(
                self.tableWidget_design_data, mode="设计数据"
            )
            print("[BUG HUNT] 3. '设计数据' 验证函数成功返回。")

            has_missing_common, missing_common = validate_required_fields(
                self.tableWidget_general_data, mode="通用数据"
            )
            print("[BUG HUNT] 4. '通用数据' 验证函数成功返回。")
            # ▲▲▲ 如果日志能打印到这里，说明上面两行没问题 ▲▲▲

            missing_fields = [name for _, name in (missing_dsg + missing_common)]

            if has_missing_dsg or has_missing_common:
                print("[BUG HUNT] 5. 发现缺失项，进入高亮和弹窗逻辑。")
                self._validation_triggered = True

                print("[BUG HUNT] 5.1. 准备调用 highlight_missing_required_rows...")
                highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
                highlight_missing_required_rows(self.tableWidget_general_data, missing_common)
                print("[BUG HUNT] 5.2. 高亮函数成功返回。")

                if not skip_confirm:
                    msg = ("以下必填项：\n" + "、".join(missing_fields) + "\n对应参数值不能为空。\n是否确认继续关闭？")
                    if show_confirm_dialog(self, "提示", msg):
                        print("[BUG HUNT] 6. 用户选择'是'，执行保存。")
                        if not save_local_condition_file(self.product_id, self):
                            return (False, missing_fields)
                        save_all_tables(self, self.product_id)
                        update_user_config_for_2_6_1(product_id, json_path="modules/yudingyi/dn_pressure_table.json")

                        # ... 省略UI更新代码 ...
                        self._is_modified = False
                        return (True, [])
                    else:
                        print("[BUG HUNT] 7. 用户选择'否'，阻止关闭。")
                        return (False, missing_fields)

            # 如果没有缺失项，代码会执行到这里
            print("[BUG HUNT] 8. 没有发现缺失项，方法正常结束。")
            # 添加一个明确的返回，避免隐式返回 None
            return (True, [])

        except Exception as e:
            print(f"[BUG HUNT] 捕获到 Python 异常: {e}")
            QMessageBox.critical(self, "保存失败", f"保存数据出错：\n{str(e)}")
            return (False, [])

    # 关闭条件输入界面用
    # def check_and_save_datagb(self, force=False, skip_confirm=False):
    #     """
    #     用于用户点击关闭界面时，检查必填项并保存。
    #     """
    #     if not getattr(self, "_is_valid_product", True):
    #         return (True, [])
    #
    #     try:
    #         # 检查必填项
    #         has_missing_dsg, missing_dsg = validate_required_fields(
    #             self.tableWidget_design_data, mode="设计数据"
    #         )
    #         has_missing_common, missing_common = validate_required_fields(
    #             self.tableWidget_general_data, mode="通用数据"
    #         )
    #
    #         missing_fields = [name for _, name in (missing_dsg + missing_common)]
    #
    #         if has_missing_dsg or has_missing_common:
    #             self._validation_triggered = True  # 保留您的实时高亮逻辑
    #             highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
    #             highlight_missing_required_rows(self.tableWidget_general_data, missing_common)
    #
    #             # 保留您的弹窗询问逻辑
    #             if skip_confirm==False:
    #                 msg = ("以下必填项：\n" + "、".join(missing_fields) + "\n对应参数值不能为空。\n是否继续关闭？")
    #                 reply = QMessageBox.question(self, "提示", msg, QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
    #                 # if reply == QMessageBox.No:
    #                 #     return (False, missing_fields)
    #                 if reply == QMessageBox.Yes:
    #                     # 执行保存操作
    #                     if not save_local_condition_file(self.product_id, self):
    #                         return (False, missing_fields)
    #                     save_all_tables(self, self.product_id)
    #
    #                     # 保存成功后清理状态
    #                     self._validation_triggered = False
    #                     self.clear_all_highlights()
    #                     self.line_tip.setText("保存成功！")
    #                     self.line_tip.setToolTip("保存成功！")
    #                     self.line_tip.setStyleSheet("color: black;")
    #
    #                     self.tip_timer.stop()
    #                     self.tip_timer.start(5000)
    #
    #                     # 关键：保存成功后，重置修改状态
    #                     self._is_modified = False
    #                     self.setWindowTitle(self.original_window_title)  # 恢复窗口标题
    #                     return (True, [])
    #                 else:
    #                     return (False, missing_fields)
    #
    #     except Exception as e:
    #         QMessageBox.critical(self, "保存失败", f"保存数据出错：\n{str(e)}")
    #         return (False, [])

    def check_and_save_dataqh(self, force=False, skip_confirm=False):
        """
        用于用户从条件输入界面切换至其他界面时，检查必填项并保存。
        """
        if not getattr(self, "_is_valid_product", True):
            return (True, [])

        try:
            # 检查必填项
            has_missing_dsg, missing_dsg = validate_required_fields(
                self.tableWidget_design_data, mode="设计数据"
            )
            has_missing_common, missing_common = validate_required_fields(
                self.tableWidget_general_data, mode="通用数据"
            )

            missing_fields = [name for _, name in (missing_dsg + missing_common)]

            if has_missing_dsg or has_missing_common:
                self._validation_triggered = True  # 保留您的实时高亮逻辑
                highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
                highlight_missing_required_rows(self.tableWidget_general_data, missing_common)

                # 保留您的弹窗询问逻辑
                if skip_confirm==False:
                    msg = ("以下必填项：\n" + "、".join(missing_fields) + "\n对应参数值不能为空。\n是否确认继续切换界面？")
                    if not show_confirm_dialog(self, "提示", msg):
                        return (False, missing_fields)

            # 执行保存操作
            if not save_local_condition_file(self.product_id, self):
                return (False, missing_fields)
            save_all_tables(self, self.product_id)
            update_user_config_for_2_6_1(product_id, json_path="modules/yudingyi/dn_pressure_table.json")


            # 保存成功后清理状态
            self._validation_triggered = False
            self.clear_all_highlights()
            self.line_tip.setText("保存成功！")
            self.line_tip.setToolTip("保存成功！")
            self.line_tip.setStyleSheet("color: black;")

            self.tip_timer.stop()
            self.tip_timer.start(5000)

            # 关键：保存成功后，重置修改状态
            self._is_modified = False
            self.setWindowTitle(self.original_window_title)  # 恢复窗口标题

            return (True, [])

        except Exception as e:
            QMessageBox.critical(self, "保存失败", f"保存数据出错：\n{str(e)}")
            return (False, [])
    # def check_and_save_data(self, force=False):
    #     """
    #     保存及检查必填项
    #     :param force: 是否强制保存（确认按钮时 True，切换/关闭时 False）
    #     :return: 检查结果 + 缺失字段（元组）
    #     """
    #     if not getattr(self, "_is_valid_product", True):
    #         return True  # 空界面不用保存，返回成功和空列表
    #
    #     # 如果不是强制保存，并且没有修改过数据，就直接跳过 1012lxy修改 将此处注释
    #     # if not force and not getattr(self, "_is_modified", False):
    #     #     return True
    #
    #     try:
    #         # 检查必填项
    #         has_missing_dsg, missing_dsg = validate_required_fields(
    #             self.tableWidget_design_data, mode="设计数据"
    #         )
    #         has_missing_common, missing_common = validate_required_fields(
    #             self.tableWidget_general_data, mode="通用数据"
    #         )
    #
    #         if has_missing_dsg or has_missing_common:
    #             # ===lxy101 核心修改点 1: 打开实时验证的“开关” ===
    #             self._validation_triggered = True  # <--- 在发现错误时，激活实时高亮清除功能
    #
    #             missing_fields = [name for _, name in (missing_dsg + missing_common)]
    #             msg = (
    #                     "以下必填项：\n"
    #                     + "、".join(missing_fields)
    #                     + "\n对应参数值不能为空。\n是否继续保存？"
    #             )
    #
    #             # 自定义“是 / 否”按钮
    #             box = QMessageBox(self)
    #             box.setIcon(QMessageBox.Question)
    #             box.setWindowTitle("提示")
    #             box.setText(msg)
    #             yes_btn = box.addButton("是", QMessageBox.YesRole)
    #             no_btn = box.addButton("否", QMessageBox.NoRole)
    #             box.setDefaultButton(no_btn)
    #             box.exec_()
    #
    #             # 始终高亮未填项
    #             highlight_missing_required_rows(self.tableWidget_design_data, missing_dsg)
    #             highlight_missing_required_rows(self.tableWidget_general_data, missing_common)
    #
    #             if box.clickedButton() == no_btn:
    #                 return False
    #             # 如果点“是”，继续保存
    #
    #         # 保存操作
    #         if not save_local_condition_file(self.product_id, self):
    #             return False
    #         save_all_tables(self, self.product_id)
    #
    #         # ===lxy101 核心修改点 2: 保存成功后，关闭“开关”并清除高亮 ===
    #         self._validation_triggered = False  # <--- 保存成功，重置标志
    #         self.clear_all_highlights()      # <--- 调用您已有的清除函数
    #
    #         self.line_tip.setText("保存成功！")
    #         self.line_tip.setToolTip("保存成功！")
    #         self.line_tip.setStyleSheet("color: black;")
    #
    #         # 保存完成后清除修改标志
    #         self._is_modified = False
    #         return True
    #
    #     except Exception as e:
    #         QMessageBox.critical(self, "保存失败", f"保存数据出错：\n{str(e)}")
    #         return False

    # lxy101 新增清除高亮
    def clear_all_highlights(self):
        """清除所有表格的高亮显示"""
        # 清除设计数据表高亮
        highlight_missing_required_rows(self.tableWidget_design_data, [])
        # 清除通用数据表高亮
        highlight_missing_required_rows(self.tableWidget_general_data, [])
        # 若其他表格有高亮逻辑，在此补充
        # 示例：highlight_missing_required_rows(self.tableWidget_coating_data, [])

    def handle_cell_input(self, item):  # 信号会自动传入被修改的 QTableWidgetItem
        """处理单元格输入，实时校验并更新高亮状态"""

        # ▼▼▼【核心修改 2.1】检查“开关”状态 ▼▼▼
        # 如果从未触发过验证（即没点过“保存”并失败），则不进行任何实时高亮操作。
        if not self._validation_triggered:
            return

        # 正在加载数据时也忽略
        if self._is_loading_data:
            return

        table_widget = item.tableWidget()  # 从 item 对象获取它所属的表格

        # ▼▼▼【核心修改 2.2】在处理前，临时阻塞信号，防止无限循环 ▼▼▼
        table_widget.blockSignals(True)

        try:
            # 确定当前操作的是哪个表格，获取对应的模式名称
            mode = None
            if table_widget is self.tableWidget_design_data:
                mode = "设计数据"
            elif table_widget is self.tableWidget_general_data:
                mode = "通用数据"

            if mode:
                # 重新对当前表格的所有必填项进行校验
                has_missing, missing_fields = validate_required_fields(table_widget, mode=mode)

                # 根据最新的校验结果，直接更新高亮
                # 如果 missing_fields 为空，则会清除所有高亮
                highlight_missing_required_rows(table_widget, missing_fields)

        finally:
            # ▼▼▼【核心修改 2.3】处理完成后，一定要恢复信号 ▼▼▼
            table_widget.blockSignals(False)
    # # lxy101 新增单元格输入 1014lxy
    # def handle_cell_input(self, table_widget, row, col):
    #     """处理单元格输入，实时校验并更新高亮状态"""
    #
    #     # === 核心修改点 3: 检查“开关”状态 ===
    #     # # 如果验证从未被触发过，则直接返回，不执行任何操作
    #     # if not self._validation_triggered:
    #     #     return
    #
    #
    #     if self._is_loading_data:
    #         return # 排除加载阶段的修改
    #     # 关键：只要修改就标记为未保存（移除 _validation_triggered 判断）
    #     self._is_modified = True
    #     print(f"[调试] 数据修改后，_is_modified = {self._is_modified}")  # 新增日志
    #
    #     # === 关键修复：在处理前，临时阻塞信号，防止无限循环 ===
    #     table_widget.blockSignals(True)
    #     try:
    #         # 1. 确定当前操作的是哪个表格，获取对应的模式名称
    #         # mode = "设计数据" if table_widget == self.tableWidget_design_data else "通用数据"
    #         # 2. 重新对当前表格的所有必填项进行校验
    #         # has_missing, missing_fields = validate_required_fields(table_widget, mode=mode)
    #         # 3. 根据最新的校验结果，直接更新高亮
    #         # highlight_missing_required_rows(table_widget, missing_fields)
    #         pass
    #     finally:
    #         # === 关键修复：处理完成后，一定要恢复信号，确保用户下一次输入能被响应 ===
    #         table_widget.blockSignals(False)
    # # lxy101 - 之后的代码部分省略

    def export_condition_file(self):
        """
        导出条件输入数据表：先保存至本地文件，然后复制至用户选择的位置。
        """
        from PyQt5.QtWidgets import QFileDialog
        import shutil

        if not getattr(self, "_is_valid_product", True):
            if self.line_tip:
                self.line_tip.setText("❌ 当前未选择有效产品，无法导出。")
            return

        try:
            # 第一步：保存到本地文件
            success = save_local_condition_file(self.product_id, self)
            if not success:
                return

            # 获取本地文件路径
            local_path = get_ref_data_excel_path(self.product_id)

            # 第二步：让用户选择导出路径
            dest_path, _ = QFileDialog.getSaveFileName(
                self,
                "保存条件输入数据表",
                "条件输入数据表.xlsx",
                "Excel 文件 (*.xlsx);;所有文件 (*)"
            )
            if not dest_path:
                if self.line_tip:
                    self.line_tip.setText("导出已取消")
                return

            # 第三步：复制文件到目标位置
            shutil.copyfile(local_path, dest_path)

            message = f"已成功导出文件至: {dest_path}"
            if self.line_tip:
                self.line_tip.setText(message)
                self.line_tip.setToolTip(message)

        except Exception as e:
            err_msg = f"导出文件时出错: {str(e)}"
            if self.line_tip:
                self.line_tip.setText(err_msg[:80])
                self.line_tip.setToolTip(err_msg)
            else:
                QMessageBox.critical(self, "导出失败", err_msg)

    #新增 模式切换处理函数
    def on_mode_changed(self, mode_name: str):
        """
        仅改变界面显示顺序；数据库与本地Excel保存仍使用默认顺序。
        """
        print(f"[DEBUG] on_mode_changed 被调用，当前模式切换为: {mode_name}")  # ✅ 添加这行
        if not mode_name:
            return

        # 默认模式 = 恢复默认顺序（即初始载入时顺序） 设计模式
        if mode_name == self._default_mode_name or mode_name.strip() == "":
            # 用“默认ID顺序”再排一次（就是 capture_default_order 记录那次的出现次序）
            #ids_std = getattr(self.tableWidget_product_std, "_default_param_ids", None)
            ids_design = getattr(self.tableWidget_design_data, "_default_param_ids", None)
            #ids_general = getattr(self.tableWidget_general_data, "_default_param_ids", None)
            #if ids_std:
                #apply_mode_param_order(self.tableWidget_product_std, [i for i in ids_std if i is not None])
            if ids_design:
                apply_mode_param_order(self.tableWidget_design_data, [i for i in ids_design if i is not None])
            #if ids_general:
                #apply_mode_param_order(self.tableWidget_general_data, [i for i in ids_general if i is not None])
            return

        # 其他模式：查表里的“参数顺序”并应用
        target_ids = self._mode_orders.get(mode_name)
        if not target_ids:
            return

        # 仅重排三张含“参数ID”的表
        #apply_mode_param_order(self.tableWidget_product_std, target_ids)
        apply_mode_param_order(self.tableWidget_design_data, target_ids)
        #apply_mode_param_order(self.tableWidget_general_data, target_ids)

        # ===== 新增：模式切换后，将设计数据表格的序号列设为不可编辑 =====
        print(f"[DEBUG] 正在设置设计数据表格（tableWidget_design_data）的序号列（第0列）为不可编辑")  # ✅ 调试打印

        # ✅ 无论切换到什么模式，都执行这一段 ✅ 所有模式切换逻辑执行完毕后，统一设置序号列不可编辑
        if hasattr(self, 'tableWidget_design_data') and self.tableWidget_design_data is not None:
            # 序号列是第 0 列
            column = 0
            for row in range(self.tableWidget_design_data.rowCount()):
                item = self.tableWidget_design_data.item(row, column)
                if item is not None:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)  # 移除可编辑标志
            print(f"[DEBUG] 设计数据表格序号列已设为不可编辑")  # ✅ 调试打印

    def eventFilter(self, obj, event):
        """
        拦截“设计数据”表的单击：
        - 命中“参数名称”列 且 参数名为“设计压力*”或“设计压力”时，弹出多工况窗口
        - 单击即可触发（若想双击触发，把 MouseButtonRelease 改成 MouseButtonDblClick）
        """
        try:
            # 屏蔽“设计模式/工作模式”等页面顶部下拉框的鼠标滚轮
            if hasattr(self, "combo_mode") and obj is getattr(self, "combo_mode") and event.type() == QEvent.Wheel:
                return True

            if obj is self.tableWidget_design_data.viewport() and event.type() == QEvent.MouseButtonRelease:
                pos = event.pos()
                index = self.tableWidget_design_data.indexAt(pos)
                if not index.isValid():
                    return super().eventFilter(obj, event)

                row, col = index.row(), index.column()

                # 参数名称列索引是 1（0=序号, 1=参数名称）
                if col != 1:
                    return super().eventFilter(obj, event)

                # 获取参数名称
                name_item = self.tableWidget_design_data.item(row, col)
                param_name = name_item.text().strip() if name_item else ""

            return super().eventFilter(obj, event)
        except Exception as e:
            print(f"[多工况] eventFilter 异常：{e}")
            return super().eventFilter(obj, event)

    def _open_multi_conditions_dialog(self, row: int, col: int, side: str):
        """
        打开“多工况”窗口（6行参数+壳程/管程两列），切换工况可编辑不同工况数据，
        确认时直接保存到数据库。
        """
        dlg = MultiConditionsDialog(self, product_id=self.product_id)
        dlg.exec_()

    def _set_modified(self, modified=True):
        """标记数据是否已修改"""
        self._is_modified = modified
