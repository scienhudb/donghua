import os
import re
import sys
import traceback
from collections import defaultdict
from urllib.parse import urljoin
from urllib.request import pathname2url

from PyQt5 import QtWidgets, uic, QtCore, QtGui
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtWidgets import QApplication, QWidget, QTableWidgetItem, QMessageBox, QMenu, QAction, QComboBox, \
    QStyledItemDelegate, QPushButton, QTableWidget, QVBoxLayout, QTabWidget, QLabel, QAbstractItemView, QLineEdit, \
    QDialog, QCheckBox, QHeaderView, QHBoxLayout, QToolButton

from modules import chanpinguanli
from modules.cailiaodingyi.controllers.add_tab import PlusTabManager
from modules.cailiaodingyi.controllers.checkcombo import CheckComboDelegate
from modules.cailiaodingyi.controllers.combo import ComboDelegate, ComboPopupEventFilter
from modules.cailiaodingyi.controllers.rename import RenamableLineEdit
from modules.cailiaodingyi.controllers.table import CustomHeaderView
from modules.cailiaodingyi.controllers.template_handler import (
    handle_template_change,
    apply_combobox_to_table,
    set_table_tooltips
)
from modules.cailiaodingyi.controllers.datamanager import (
    handle_table_click,
    handle_guankou_table_click,
    on_confirm_param_update,
    on_confirm_guankouparam, apply_paramname_dependent_combobox, apply_paramname_combobox,
    apply_gk_paramname_combobox, bind_define_table_click, on_clear_param_update, load_data_by_template, on_clear_guankou_param_update,
)
from modules.cailiaodingyi.funcs.funcs_pdf_change import load_guankou_para_data_leibie, load_guankou_define_leibie, \
    load_updated_guankou_define_data, load_update_element_data, load_update_guankou_define_data, \
    load_update_guankou_para_data, get_design_params_by_product_id, \
    query_template_id, query_guankou_codes,insert_or_update_element_merged_para_data
from modules.cailiaodingyi.controllers.style import ReturnKeyJumpFilter
from modules.cailiaodingyi.funcs.funcs_pdf_input import (
    load_design_product_data,
    load_elementoriginal_data,
    load_element_details,
    move_guankou_to_first,
    load_guankou_define_data,
    load_guankou_material_detail,
    insert_element_data,
    insert_guankou_material_data,
    query_template_guankou_para_data,
    insert_guankou_para_data,
    query_template_element_para_data,
    insert_element_para_data,
    load_material_dropdown_values,
    select_template_id,
    insert_add_guankou_define,
    insert_all_guankou_param,
    has_product, query_all_guankou_categories, load_element_info, query_guankou_define_data_by_category,
    query_guankou_param_by_product, update_template_input_editable_state, is_all_defined_in_left_table,
    save_to_template_library, get_template_id_by_name, insert_updated_element_para_data, insert_guankou_define_data,
    insert_guankou_para_info, load_template, load_guankou_material_detail_template, get_grouped,
    update_material_category_in_db, query_guankou_param_by_template, load_guankou_param_leibie, load_guankou_param_byid,
    delete_guankou_data_from_db, load_dropdown_options, load_guankou_param_structure_from_db,
    insert_guankou_param_leibie, query_guankou_default, insert_guankou_info, query_assigned_codes_by_tab, _find_row,
    query_guankou_codes_by_product, query_unassigned_codes, query_codes_for_tab_raw, init_buguan_defaults,
    clear_guankou_leibie,query_template_element_merged_para_data
)
from modules.cailiaodingyi.funcs.funcs_pdf_render import render_guankou_param_to_ui, _set_text_center
from modules.chanpinguanli import chanpinguanli_main
from modules.chanpinguanli.chanpinguanli_main import product_manager
from modules.condition_input.funcs.funcs_cdt_input import sync_corrosion_to_guankou_param
from modules.condition_input.view import DesignConditionInputViewer, check_project_and_product
from modules.condition_input.view import check_project_and_product
from modules.guankoudingyi.dynamically_adjust_ui import Stats

product_id = None


def on_product_id_changed(new_id):
    print(f"Received new PRODUCT_ID: {new_id}")
    global product_id
    product_id = new_id


# 测试用产品 ID（真实情况中由外部输入）
product_manager.product_id_changed.connect(on_product_id_changed)

class DesignParameterDefineInputerViewer(QWidget):
    def __init__(self, line_tip=None, main_window=None):
        super().__init__()
        # # 0903会议纪要 首先进行项目和产品检查
        # print("准备检查项目和产品状态...")
        # can_open, msg = check_project_and_product()
        # if not can_open:
        #     QMessageBox.information(self, "提示", msg)
        #     self.deleteLater()  # 不打开界面
        #     return  # 立即返回

        self.line_tip = line_tip
        self.main_window = main_window
        self.guankou_define_info = None

        # # 使用绝对路径加载UI文件，避免工作目录变化导致的问题
        # import os
        # current_dir = os.path.dirname(os.path.abspath(__file__))
        # ui_path = os.path.join(current_dir, "ui", "paradefine.ui")
        # self.ui = uic.loadUi(ui_path, self)
        # self.init_widgets()  # 获取所有控件、绑定事件
        # self.product_id = product_id

        self.ui = uic.loadUi("modules/cailiaodingyi/ui/paradefine.ui", self)  # 加载UI文件
        self.init_widgets()  # 获取所有控件、绑定事件
        self.product_id = product_id
        print("self.product_id", self.product_id)
        self.product_type, self.product_form = load_design_product_data(self.product_id)
        print("产品类型", self.product_form)
        # 初始化管口材料tab页列表
        self.dynamic_guankou_tabs = []
        self.dynamic_guankou_param_tabs = {}
        self.dynamic_guankou_define_tabs = {}
        self.load_original_data()
        # self.product_id = "PD20250526001"
        # self.product_type = "管壳式热交换器"
        # self.product_form = "BEU"
        self.dropdown_initialized = False

        # 回退筛选
        self.visible_rows_stack = []

        self.setWindowTitle("参数定义")

        # 监听下拉框选择变化
        self.comboBox_template.currentIndexChanged.connect(lambda idx: handle_template_change(self, idx))
        ## 绑定管口与右侧表格事件：选项变化时触发筛选函数
        self.tableWidget_parts.cellClicked.connect(self.handle_table_click_guankou)
    def init_widgets(self):
        # 获取界面中所有控件的对象
        self.comboBox_template = self.findChild(QtWidgets.QComboBox, "comboBox_template")
        self.tableWidget_parts = self.findChild(QtWidgets.QTableWidget, "tableWidget")
        self.tableWidget_parts.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, self.tableWidget_parts))
        self.tableWidget_parts.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tableWidget_parts.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.tableWidget_parts.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tableWidget_parts.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_parts))
        self.stackedWidget = self.findChild(QtWidgets.QStackedWidget, "stackedWidget")
        self.textBrowser_part_image = self.findChild(QtWidgets.QTextBrowser, "textBrowser")
        # 获取右侧表格控件
        self.tableWidget_detail = self.findChild(QtWidgets.QTableWidget, "tableWidget_para")
        # 绘制非管口参数表头
        self.tableWidget_detail.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, self.tableWidget_detail))
        self.pushButton_detail = self.findChild(QPushButton, "pushButton_8")
        if self.pushButton_detail:
            self.pushButton_detail.clicked.connect(lambda: on_confirm_param_update(self))
        # 设置列宽自适应
        header = self.tableWidget_detail.horizontalHeader()
        for i in range(self.tableWidget_detail.columnCount()):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

        # 零件列表表格行高亮
        self.tableWidget_parts.itemSelectionChanged.connect(self.on_selection_changed)

        # 获取快速筛选输入框
        self.lineEdit_filter = self.findChild(QtWidgets.QLineEdit, "lineEdit")
        self.lineEdit_filter.setPlaceholderText("输入关键词筛选所有列...")
        self.lineEdit_filter.textChanged.connect(self.filter_table_globally)
        # 获取管口表格控件
        self.tableWidget_guankou = self.findChild(QtWidgets.QTableWidget, "tableWidget_define1")
        self.tableWidget_guankou.cellClicked.connect(self.on_guankou_cell_clicked)

        # 通用元件的清空
        self.pushButton_clear = self.findChild(QPushButton, "pushButton_9")
        self.pushButton_clear.clicked.connect(lambda: on_clear_param_update(self))

        # 管口元件的清空
        self.pushButton_guankou_clear = self.findChild(QPushButton, "pushButton_6")
        self.pushButton_guankou_clear.clicked.connect(lambda: on_clear_guankou_param_update(self))

        # 合并元件的清空
        self.pushButton_fixed_saddle_clear = self.findChild(QPushButton, "pushButton_10")  # 假设按钮ID为pushButton_10
        if self.pushButton_fixed_saddle_clear:
            from modules.cailiaodingyi.controllers.datamanager import on_clear_element_merged_para_update
            self.pushButton_fixed_saddle_clear.clicked.connect(lambda: on_clear_element_merged_para_update(self))
        
        # 合并元件的确定
        self.pushButton_fixed_saddle_confirm = self.findChild(QPushButton, "pushButton_11")  # 假设按钮ID为pushButton_11
        if self.pushButton_fixed_saddle_confirm:
            from modules.cailiaodingyi.controllers.datamanager import on_confirm_element_merged_para_param
            self.pushButton_fixed_saddle_confirm.clicked.connect(lambda: on_confirm_element_merged_para_param(self))




        # # 绘制管口定义表格
        # self.tableWidget_guankou_define.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, self.tableWidget_guankou_define))
        # self.tableWidget_guankou_define.cellClicked.connect(lambda row, col: handle_guankou_table_click(self, row, col))
        # self.tableWidget_guankou_param = self.findChild(QtWidgets.QTableWidget, "tableWidget_gpara1")
        # self.tableWidget_guankou_define.cellClicked.connect(lambda row, col: handle_guankou_table_click(self, row, col))
        # # 绘制管口参数表格
        # self.tableWidget_guankou_param.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, self.tableWidget_guankou_param))
        # self.tableWidget_guankou_param.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_guankou_param))

        self.label_part_image = self.findChild(QLabel, "label_4")
        print("self.label_part_image", self.label_part_image)
        # 管口参数定义的确定按钮
        self.pushButton_guankouparam = self.findChild(QPushButton, "pushButton_7")
        if self.pushButton_guankouparam:
            self.pushButton_guankouparam.clicked.connect(lambda: on_confirm_guankouparam(self))
        self.clicked_guankou_define_data = {}
        # 监听表格选中项变化，将选中的零件示意图显示到右侧
        self.tableWidget_parts.cellClicked.connect(lambda row, col: handle_table_click(self, row, col))

        self.tableWidget_parts.selectionModel().selectionChanged.connect(self.show_image_in_text_browser)
        # 针对模板选用
        self.comboBox_template.insertItem(0, "")
        self.comboBox_template.setCurrentIndex(0)  # 默认选中第0个，也就是空白
        # 对于非管口的零件获取参数定义表格
        self.tableWidget_para_define = self.findChild(QtWidgets.QTableWidget, "tableWidget_para")
        self.tableWidget_para_define.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_para_define))

        # # 监控非管口的参数定义
        # self.tableWidget_para_define.itemChanged.connect(self.on_para_define_item_changed)

        # 对于非管口的零件参数表格设置高亮
        self.tableWidget_para_define.itemSelectionChanged.connect(self.on_param_table_selection_changed)


        # 获取管口定义对应的tabs
        self.guankou_tabWidget = self.findChild(QTabWidget, "tabWidget")
        # self.guankou_tabWidget.currentChanged.connect(self.on_tab_changed)
        # 第一个 tab 页
        self.default_param_table = self.tableWidget_guankou  # 记录真正默认页的表
        page0 = self.guankou_tabWidget.widget(0)
        if page0 and page0.property('param_table') is None:
            page0.setProperty('param_table', self.default_param_table)


        # 监听双击 tab 重命名
        self.guankou_tabWidget.tabBarDoubleClicked.connect(self.on_tab_double_clicked)


        bar = self.guankou_tabWidget.tabBar()
        bar.setUsesScrollButtons(True)  # 出现滚动箭头
        bar.setExpanding(False)  # 关键：不要等分拉伸，才能判断“是否能放下+”
        bar.setElideMode(Qt.ElideNone)  # 不要省略号
        bar.setContextMenuPolicy(Qt.CustomContextMenu)
        bar.customContextMenuRequested.connect(self.on_guankou_tab_right_menu)

        # 挂上管理器（只保留这一句）
        self.plus_mgr = PlusTabManager(
            self.guankou_tabWidget,
            lambda src_idx, src_name: self._add_single_table_tab_copy_only(
                source_tab_name=src_name,
                insert_after_index=src_idx
            )
        )

        # 建一个：tab 名 → 对应表格 的映射，便于切换时找到表
        self.dynamic_guankou_param_tabs = getattr(self, "dynamic_guankou_param_tabs", {})

        # 切换 tab 时，把当前表指向该 tab 的表格（便于你其他逻辑沿用原来的 self.tableWidget_guankou）
        self.guankou_tabWidget.currentChanged.connect(self._on_guankou_tab_changed)

        QTimer.singleShot(0, lambda: self._on_guankou_tab_changed(self.guankou_tabWidget.currentIndex()))

        # 获取存为模板输入框
        self.lineEdit_template = self.findChild(QtWidgets.QLineEdit, "lineEdit_2")
        self.lineEdit_template.returnPressed.connect(self.on_template_name_entered)


        # self.tableWidget_parts.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_parts))
        self.tableWidget_parts.installEventFilter(
            ReturnKeyJumpFilter(
                self.tableWidget_parts,
                after_jump_callback=lambda r, c: handle_table_click(self, r, c)
            )
        )
        # self.tableWidget_guankou_param.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_guankou_param))
        # self.tableWidget_para_define.installEventFilter(ReturnKeyJumpFilter(self.tableWidget_para_define))

        # 用户修改，才标记未保存
        self.detail_table_modified = True




    def on_tab_changed(self, index):
        self.guankou_material_category.setCurrentIndex(0)



    def _ensure_default_tab_registered(self):
        tw = self.guankou_tabWidget
        if not tw or tw.count() == 0:
            return

        page0 = tw.widget(0)

        # ① 优先用第一页 page 上的属性
        table0 = page0.property('param_table') if page0 is not None else None
        # ② 其次用初始化时缓存的真正默认表
        if table0 is None:
            table0 = getattr(self, "default_param_table", None)
        # ③ 最后才兜底旧字段（仅当以上都没有时）
        if table0 is None:
            table0 = getattr(self, "tableWidget_guankou", None)

        if page0 is not None and page0.property('param_table') is None and table0 is not None:
            page0.setProperty('param_table', table0)

        if table0 is not None:
            if not hasattr(self, "dynamic_guankou_param_tabs"):
                self.dynamic_guankou_param_tabs = {}
            self.dynamic_guankou_param_tabs[tw.tabText(0).strip()] = table0

    def _on_guankou_tab_changed(self, index: int):
        tw = self.guankou_tabWidget
        if not tw or index < 0 or index >= tw.count():
            return

        name = tw.tabText(index).strip()
        if name in {"+", "＋"}:
            # 点击 + 标签，跳回上一页
            tw.setCurrentIndex(max(0, index - 1))
            return

        if index == 0:
            self._ensure_default_tab_registered()

        # 获取当前 page 对应的 table
        page = tw.widget(index)
        table = page.property('param_table') if page else None

        if table is None:
            # 兜底，找 default table 或全局 tableWidget_guankou
            table = getattr(self, "default_param_table", None) or getattr(self, "tableWidget_guankou", None)
            if table:
                if page:
                    page.setProperty('param_table', table)
            else:
                print(f"[警告] 没找到 {name} 的参数表，跳过刷新")
                return

        # 临时赋值给 self.tableWidget_guankou 用于渲染
        old_table = getattr(self, "tableWidget_guankou", None)
        self.tableWidget_guankou = table

        try:
            # ★ 用数据库为准：覆盖“已选值”，并更新候选
            self.patch_codes_for_current_tab(table, name)

        finally:
            # 恢复旧的 table
            self.tableWidget_guankou = old_table

    def _add_single_table_tab_copy_only(self, source_tab_name: str, insert_after_index: int):
        """
        新建单表 tab：
        - 拷贝源：始终取“当前选中的 tab”（如果当前是 '+'，则取最后一个真正的 tab）
        - 插入位置：始终插在最后一个已创建的 tab 后面（即 '+' 之前）
        - 布局：page + QVBoxLayout 包住表格，并拷贝初始 tab 的边距/间距，保证顶部空隙一致
        """
        tw = self.guankou_tabWidget

        # —— 1) 取“当前选中 tab”作为拷贝源（若当前是 +，退回到最后一个真正的 tab）——
        cur = tw.currentIndex()
        if cur < 0:
            cur = 0
        cur_name = tw.tabText(cur) if tw.count() > 0 else ""
        if cur_name == "+":
            last_real = tw.count() - 2 if (tw.count() >= 2 and tw.tabText(tw.count() - 1) == "+") else tw.count() - 1
            cur = max(0, last_real)
            cur_name = tw.tabText(cur) if cur >= 0 else ""
        source_tab_name = cur_name  # 用 tab 名判断并加载数据


        # —— 2) 计算插入位置：始终放到最后一个新建 tab 的后面（即 '+' 的前面）——
        last_is_plus = (tw.count() > 0 and tw.tabText(tw.count() - 1) == "+")
        insert_pos = tw.count() - 1 if last_is_plus else tw.count()
        insert_pos = max(0, insert_pos)

        print(f"[调试] 新 tab 将插入位置: {insert_pos}")

        # —— 3) 新建表格 + 外壳布局（拷贝初始 tab 的边距/间距，保证顶部空隙一致）——
        table_guankou = QTableWidget()
        table_guankou.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, table_guankou))
        table_guankou.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        page = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(page)

        base_layout = None
        if tw.count() > 0:
            w0 = tw.widget(0)
            base_layout = w0.layout() if w0 else None
        if base_layout:
            m = base_layout.contentsMargins()
            main_layout.setContentsMargins(m.left(), m.top(), m.right(), m.bottom())
            main_layout.setSpacing(base_layout.spacing())
            # 如需保持完全一致的外观，也可同步样式（可选）
            page.setStyleSheet(w0.styleSheet())
        else:
            main_layout.setContentsMargins(9, 6, 9, 6)
            main_layout.setSpacing(6)

        main_layout.addWidget(table_guankou)

        # —— 4) 生成唯一标签并插入到目标位置 ——
        tab_label = self.generate_unique_guankou_label()
        tw.insertTab(insert_pos, page, tab_label)
        tw.setCurrentIndex(insert_pos)

        page.setProperty('param_table', table_guankou)

        # 记录映射
        self.dynamic_guankou_param_tabs[tab_label] = table_guankou

        # —— 5) 加载并渲染：严格用“拷贝源 tab 名”加载相同内容 ——
        select_template = self.comboBox_template.currentText() or 'None'
        guankou_para_info = load_guankou_param_leibie(source_tab_name, self.product_id, select_template)

        # === 新增: 腐蚀裕量处理逻辑 ===
        ca_map = get_design_params_by_product_id(self.product_id)
        tube_ca = ca_map.get("腐蚀裕量*", {}).get("管程数值", "")
        shell_ca = ca_map.get("腐蚀裕量*", {}).get("壳程数值", "")

        for row in guankou_para_info:
            pname = row.get("参数名称", "")
            if "接管腐蚀裕量" not in pname:
                continue

            # case1: 管壳程腐蚀裕量相同 → 默认填值
            if tube_ca and shell_ca and str(tube_ca) == str(shell_ca):
                row["参数值"] = str(tube_ca)
                print(f"[调试] 新建Tab {tab_label} {pname} → {tube_ca} (case1: 相同)")
            else:
                # case2/3: 新建 tab 默认没有管口号 → 留空
                row["参数值"] = ""
                print(f"[调试] 新建Tab {tab_label} {pname} → 空 (case2/3: 默认无管口号)")
        # === 新增结束 ===


        insert_guankou_param_leibie(self.product_id, tab_label, select_template, guankou_para_info,
                                        keep_values=True)

        old_ref = getattr(self, "tableWidget_guankou", None)
        self.tableWidget_guankou = table_guankou
        try:
            render_guankou_param_to_ui(self, guankou_para_info)
        finally:
            self.tableWidget_guankou = old_ref  # ← 一定要恢复旧引用

        # ✅ 关键：新增后也刷新
        if hasattr(self, "plus_mgr") and self.plus_mgr:
            self.plus_mgr.refresh_after_model_change()

    def on_guankou_tab_right_menu(self, pos):
        bar = self.guankou_tabWidget.tabBar()
        index = bar.tabAt(pos)
        if index < 0:
            return

        text = self.guankou_tabWidget.tabText(index).strip()
        if text in {"+", "＋"}:
            return

        total = self.guankou_tabWidget.count()
        has_plus = total > 0 and self.guankou_tabWidget.tabText(total - 1).strip() in {"+", "＋"}
        real_count = total - (1 if has_plus else 0)

        menu = QMenu(self)
        act_enlarge = menu.addAction("放大查看参数表格")
        act_delete = menu.addAction("删除此分类")
        act = menu.exec_(bar.mapToGlobal(pos))
        if act is act_enlarge:
            self.show_floating_table(index)  # ← 用上面新版
            return
        if act is act_delete:
            self.remove_guankou_tab(index)

    def remove_guankou_tab(self, index):
        # 防止删除 “+”
        tab_text = self.guankou_tabWidget.tabText(index).strip()
        if tab_text in {"+", "＋"}:
            return

        # 至少保留一个（排除“+”）
        total = self.guankou_tabWidget.count()
        has_plus = total > 0 and self.guankou_tabWidget.tabText(total - 1).strip() in {"+", "＋"}
        real_count = total - (1 if has_plus else 0)
        if real_count <= 1:
            QMessageBox.information(self, "提示", "至少保留一个管口材料分类，不能删除最后一个 tab")
            return

        tab_name = self.guankou_tabWidget.tabText(index)
        print(f"[调试] 正在删除 tab: {tab_name}")

        # 删库
        if getattr(self, "product_id", None):
            delete_guankou_data_from_db(self.product_id, tab_name)
            clear_guankou_leibie(self.product_id, tab_name)
        else:
            print("[警告] 当前 product_id 不存在，无法删除数据库记录")

        # ==== 关键改动：放大窗口安全处理 ====
        if hasattr(self, "dynamic_guankou_param_tabs"):
            table = self.dynamic_guankou_param_tabs.pop(tab_name, None)
            if table:
                # 如果在放大窗口中
                win = getattr(table, "_dock_float_win", None)
                if win and win.isVisible():
                    print(f"[调试] {tab_name} 正在放大显示，删除时关闭放大窗口")
                    # 标记放弃还原，防止 restore 把它塞到别的 tab
                    table._dock_abandoned = True
                    win.close()  # 会触发 restore，走“销毁”分支
        # ====================================

        # UI 移除
        self.guankou_tabWidget.removeTab(index)

        # 选中一个合理的 tab
        cnt = self.guankou_tabWidget.count()
        if cnt:
            sel = min(index, cnt - 1)
            if self.guankou_tabWidget.tabText(sel).strip() in {"+", "＋"} and sel > 0:
                sel -= 1
            self.guankou_tabWidget.setCurrentIndex(sel)

        # ✅ 让 PlusTabManager 重新判断“+”用页签还是右上角按钮
        if hasattr(self, "plus_mgr") and self.plus_mgr:
            self.plus_mgr.refresh_after_model_change()

    def on_tab_double_clicked(self, index):
        """更改tab页标题"""
        if index == -1:
            return  # 用户双击了空白处

        tab_bar = self.guankou_tabWidget.tabBar()
        old_label = tab_bar.tabText(index)

        def confirm_edit(new_label):
            if not new_label or new_label == old_label:
                return

            existing_labels = [self.guankou_tabWidget.tabText(i) for i in range(self.guankou_tabWidget.count())]
            if new_label in existing_labels:
                QMessageBox.warning(self, "重名", "该名称已存在，请重新输入")
                return

            self.guankou_tabWidget.setTabText(index, new_label)
            self.dynamic_guankou_param_tabs[new_label] = self.dynamic_guankou_param_tabs.pop(old_label, None)
            update_material_category_in_db(self.product_id, old_label, new_label)
            print(f"[调试] tab 重命名：{old_label} → {new_label}")

        rect = tab_bar.tabRect(index)
        line_edit = RenamableLineEdit(old_label, confirm_edit, tab_bar)
        line_edit.setFrame(False)
        line_edit.setAlignment(Qt.AlignCenter)
        line_edit.setGeometry(rect)
        line_edit.setFocus()
        line_edit.selectAll()
        line_edit.show()

        def finish_edit():
            new_label = line_edit.text().strip()
            if not new_label or new_label == old_label:
                line_edit.deleteLater()
                return

            # ⚠️ 防止重名
            existing_labels = [self.guankou_tabWidget.tabText(i) for i in range(self.guankou_tabWidget.count())]
            if new_label in existing_labels:
                QMessageBox.warning(self, "重名", "该名称已存在，请重新输入")
                return

            self.guankou_tabWidget.setTabText(index, new_label)

            # ✅ 同步更新映射 dict
            self.dynamic_guankou_param_tabs[new_label] = self.dynamic_guankou_param_tabs.pop(old_label, None)
            self.dynamic_guankou_define_tabs[new_label] = self.dynamic_guankou_define_tabs.pop(old_label, None)

            line_edit.deleteLater()

        line_edit.editingFinished.connect(finish_edit)
        line_edit.show()

    def generate_unique_guankou_label(self, prefix="管口材料分类"):
        existing_labels = set(self.dynamic_guankou_param_tabs.keys())
        existing_labels.update([self.guankou_tabWidget.tabText(i) for i in range(self.guankou_tabWidget.count())])

        for i in range(1, 100):  # 最多允许99个
            label = f"{prefix}{i}"
            if label not in existing_labels:
                return label
        raise ValueError("管口材料分类数量超限，无法生成唯一标签")

    def show_floating_table(self, tab_index: int):
        tw = self.guankou_tabWidget
        tab_page = tw.widget(tab_index)
        if tab_page is None:
            return

        tab_name = tw.tabText(tab_index)

        # —— 找到该页的表格：优先映射 → 页内找第一个 QTableWidget → （可选）默认表引用 ——
        table = None
        if hasattr(self, "dynamic_guankou_param_tabs"):
            table = self.dynamic_guankou_param_tabs.get(tab_name)

        if table is None:
            tables = tab_page.findChildren(QTableWidget)
            table = tables[0] if tables else None

        if table is None and hasattr(self, "tableWidget_guankou"):
            # 若这是默认第一页，可以兜底用默认表引用
            try:
                if tw.indexOf(tab_page) == 0:
                    table = self.tableWidget_guankou
            except Exception:
                pass

        if table is None:
            QMessageBox.warning(self, "未找到", f"未找到 {tab_name} 对应的参数表格")
            return

        # ==== 放大前：在原位塞占位器，占坑以便还原 ====
        # 清理历史占位器（如果之前放大过还没清掉）
        old_ph = getattr(table, "_dock_placeholder", None)
        if old_ph and old_ph.parent() is not None:
            try:
                old_ph.setParent(None)
                old_ph.deleteLater()
            except Exception:
                pass

        layout = tab_page.layout()
        if layout is None:
            layout = QtWidgets.QVBoxLayout(tab_page)

        idx = layout.indexOf(table)
        if idx < 0:
            idx = layout.count()

        placeholder = QtWidgets.QWidget(tab_page)
        placeholder.setFixedHeight(0)
        placeholder.setObjectName("dock_placeholder")
        layout.insertWidget(idx, placeholder)

        # 绑定“停靠信息”到 table 本身（最稳妥）
        table._dock_parent_page = tab_page
        table._dock_parent_layout = layout
        table._dock_index = idx
        table._dock_placeholder = placeholder
        table._dock_tab_name = tab_name
        table._dock_abandoned = False  # 默认允许还原

        # 从原布局移除，放到弹窗
        try:
            layout.removeWidget(table)
        except Exception:
            pass

        float_win = QDialog(self)
        float_win.setWindowTitle(f"{tab_name} - 参数表格放大查看")
        float_win.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint)
        float_win.setAttribute(Qt.WA_DeleteOnClose, True)
        float_win.resize(1200, 700)

        dlg_layout = QVBoxLayout(float_win)
        dlg_layout.setContentsMargins(0, 0, 0, 0)
        dlg_layout.addWidget(table)

        # 把放大窗引用也绑到 table，删除时可直接关闭
        table._dock_float_win = float_win

        # —— 如果这个页被删除（removeTab 会导致 page.destroyed）→ 标记放弃还原并关闭放大窗 ——
        def _on_parent_page_destroyed():
            try:
                table._dock_abandoned = True
                # 对应分类已不存在，移除映射（避免之后错误引用）
                if hasattr(self, "dynamic_guankou_param_tabs"):
                    self.dynamic_guankou_param_tabs.pop(tab_name, None)
                win = getattr(table, "_dock_float_win", None)
                if win and win.isVisible():
                    win.close()  # 会触发 restore，走“销毁”分支
            except Exception:
                pass

        # 只在本次放大会话里连接一次
        try:
            tab_page.destroyed.connect(_on_parent_page_destroyed)
        except Exception:
            pass

        def restore():
            # 从弹窗拿出来（解除父子关系）
            try:
                dlg_layout.removeWidget(table)
            except Exception:
                pass

            parent_page = getattr(table, "_dock_parent_page", None)
            placeholder = getattr(table, "_dock_placeholder", None)
            abandoned = getattr(table, "_dock_abandoned", False)

            # ==== 关键：若父页已删除或标记放弃还原 → 不塞到别的分类，直接销毁 ====
            if abandoned or parent_page is None or tw.indexOf(parent_page) < 0:
                try:
                    if placeholder and placeholder.parent() is not None:
                        pl = placeholder.parent().layout()
                        if pl:
                            pl.removeWidget(placeholder)
                    if placeholder:
                        placeholder.setParent(None)
                        placeholder.deleteLater()
                except Exception:
                    pass

                try:
                    table.setParent(None)
                except Exception:
                    pass
                table.deleteLater()

                # 清理临时属性
                for attr in ("_dock_parent_page", "_dock_parent_layout", "_dock_index",
                             "_dock_placeholder", "_dock_tab_name", "_dock_float_win", "_dock_abandoned"):
                    if hasattr(table, attr):
                        try:
                            delattr(table, attr)
                        except Exception:
                            pass
                return

            # ==== 正常还原到占位器原位 ====
            lay = parent_page.layout() or QtWidgets.QVBoxLayout(parent_page)
            try:
                ph_index = lay.indexOf(placeholder) if placeholder else -1
                if ph_index >= 0:
                    lay.insertWidget(ph_index, table)
                    lay.removeWidget(placeholder)
                    placeholder.setParent(None)
                    placeholder.deleteLater()
                else:
                    # 占位器丢了也能用原 index 兜底
                    insert_index = getattr(table, "_dock_index", lay.count())
                    insert_index = insert_index if isinstance(insert_index, int) else lay.count()
                    if 0 <= insert_index <= lay.count():
                        lay.insertWidget(insert_index, table)
                    else:
                        lay.addWidget(table)
            finally:
                # 清理临时属性
                for attr in ("_dock_parent_page", "_dock_parent_layout", "_dock_index",
                             "_dock_placeholder", "_dock_tab_name", "_dock_float_win", "_dock_abandoned"):
                    if hasattr(table, attr):
                        try:
                            delattr(table, attr)
                        except Exception:
                            pass

            # 再保证映射仍然指向这个 table（防止外部代码重建引用）
            if hasattr(self, "dynamic_guankou_param_tabs"):
                self.dynamic_guankou_param_tabs[tab_name] = table

        float_win.finished.connect(restore)
        float_win.show()

    def on_selection_changed(self):
        table = self.tableWidget_parts

        # 先恢复条纹背景
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if not item:
                    continue
                # 直接用硬编码色，模拟条纹 (你Designer里设定的可以替换这里)
                if r % 2 == 0:
                    item.setBackground(QColor("#ffffff"))  # 偶数行
                else:
                    item.setBackground(QColor("#f6f6f6"))  # 奇数行 (假设你的条纹色)

        selected_items = table.selectedItems()
        if not selected_items:
            return

        selected_cells = set((item.row(), item.column()) for item in selected_items)
        selected_rows = set(r for r, _ in selected_cells)

        for row in selected_rows:
            for c in range(table.columnCount()):
                if (row, c) in selected_cells:
                    continue  # 系统选中项不动
                item = table.item(row, c)
                if item:
                    item.setBackground(QColor("#d0e7ff"))  # 高亮色

    def on_guankou_cell_clicked(self, row, col):
        table = self.tableWidget_guankou

        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item:
                    item.setBackground(QColor("#ffffff"))

        for c in range(table.columnCount()):
            item = table.item(row, c)
            if item:
                item.setBackground(QColor("#d0e7ff"))

    def show_error_message(self, title, message):
        # 创建QMessageBox来显示错误信息
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Critical)  # 设置为错误图标
        msg_box.setWindowTitle(title)  # 设置窗口标题
        msg_box.setText(message)  # 设置显示的错误信息
        msg_box.setStandardButtons(QMessageBox.Ok)  # 设置“确定”按钮
        msg_box.exec_()  # 显示弹窗

    def show_info_message(self, title, message):
        # 创建QMessageBox来显示正常提示信息
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Information)  # 设置为信息图标
        msg_box.setWindowTitle(title)  # 设置窗口标题
        msg_box.setText(message)  # 设置显示的提示信息
        msg_box.setStandardButtons(QMessageBox.Ok)  # 设置“确定”按钮
        msg_box.exec_()  # 显示弹窗


    def populate_guankou_combo(self, combo_box):

        results = get_grouped(product_id)

        category_dict = defaultdict(list)
        for row in results:
            category = row['类别']
            code = row['管口代号']
            category_dict[category].append(code)

        combo_items = [
            ';'.join(codes)
            for category, codes in category_dict.items()
        ]

        combo_box.clear()
        combo_box.addItem("选择管口分配")  # 默认提示项
        combo_box.addItems(combo_items)
        combo_box.setCurrentIndex(0)


    def update_template_input_editable_state(self):
        """
        根据当前 comboBox_template 的内容来启用或禁用 '存为模板' 输入框
        """
        current_template = self.comboBox_template.currentText()
        if not current_template or current_template == "None":
            # 没有模板
            self.lineEdit_template.setEnabled(False)
        else:
            # 有模板
            self.lineEdit_template.setEnabled(True)

    def _new_param_tab_like_default(self, label: str, insert_pos: int = None):
        """创建一个和第0个tab外观完全一致的新页，返回 (page, table)"""
        tw = self.guankou_tabWidget

        # 目标插入位：默认插在 '+' 前，否则末尾
        if insert_pos is None:
            last_is_plus = (tw.count() > 0 and tw.tabText(tw.count() - 1).strip() in {"+", "＋"})
            insert_pos = tw.count() - 1 if last_is_plus else tw.count()
            insert_pos = max(0, insert_pos)

        # —— 表格（和你一致）——
        table = QTableWidget()
        table.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, table))
        table.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        # —— 页壳 + 布局（完全复制第0页的边距/间距/样式）——
        page = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(page)

        base_layout = None
        w0 = tw.widget(0) if tw.count() > 0 else None
        if w0:
            base_layout = w0.layout()
            # 页壳样式 + 页壳contentsMargins
            page.setStyleSheet(w0.styleSheet())
            m_page = w0.contentsMargins()
            page.setContentsMargins(m_page.left(), m_page.top(), m_page.right(), m_page.bottom())

        if base_layout:
            m = base_layout.contentsMargins()
            main_layout.setContentsMargins(m.left(), m.top(), m.right(), m.bottom())
            main_layout.setSpacing(base_layout.spacing())
        else:
            main_layout.setContentsMargins(9, 6, 9, 6)
            main_layout.setSpacing(6)

        main_layout.addWidget(table)

        # 插入
        self.guankou_tabWidget.insertTab(insert_pos, page, label)
        self.guankou_tabWidget.setCurrentIndex(insert_pos)

        # 记录映射
        page.setProperty('param_table', table)
        if not hasattr(self, "dynamic_guankou_param_tabs"):
            self.dynamic_guankou_param_tabs = {}
        self.dynamic_guankou_param_tabs[label] = table

        return page, table

    def patch_codes_for_current_tab(self, table, tab_name: str):
        """
        下拉候选只包含：
          1) 当前 tab 已分配的管口号（保持查询顺序）
          2) 未分类(材料分类 IS NULL) 的管口号（保持查询顺序）

        会把其它 tab 已占用的管口号排除掉。
        """
        # 找到“管口号”这一行
        row = _find_row(table, "管口号")
        if row is None or row < 0:
            print("[管口号] 未找到“管口号”行，跳过。")
            return

        # 读取数据库
        assigned = query_assigned_codes_by_tab(self.product_id, tab_name) or []  # 本 tab 已分配
        unassigned = query_unassigned_codes(self.product_id) or []  # 未分类（天然已排除其它 tab）

        # 显示：把“已分配”的值写到第1列，用 '、' 连接
        _set_text_center(table, row, 1, "、".join(assigned))

        # 候选：已分配 + 未分类（去重但保序）
        merged, seen = [], set()
        for code in assigned + unassigned:
            if code and code not in seen:
                seen.add(code)
                merged.append(code)

        # 写到表属性，CheckComboDelegate 会优先读这里
        table.setProperty("gk_code_candidates", merged)

        # 重新设置代理（先清掉可能存在的旧代理，避免悬空引用引发崩溃）
        table.setItemDelegateForRow(row, None)
        table.setItemDelegateForRow(row, CheckComboDelegate(options=merged, table=table))


    def build_or_refresh_guankou_tabs_from_db(self, param_map: dict):
        tw = self.guankou_tabWidget
        if not hasattr(self, "dynamic_guankou_param_tabs"):
            self.dynamic_guankou_param_tabs = {}

        labels = list(param_map.keys()) or ["管口材料分类1"]

        # 保留第0页，删其余
        has_plus = (tw.count() > 0 and tw.tabText(tw.count() - 1).strip() in {"+", "＋"})
        last_real = tw.count() - (1 if has_plus else 0)
        for i in range(last_real - 1, 0, -1):
            w = tw.widget(i)
            tw.removeTab(i)
            if w:
                w.deleteLater()
        self.dynamic_guankou_param_tabs.clear()

        for idx, label in enumerate(labels):
            if idx == 0:
                tw.setTabText(0, label)
                page0 = tw.widget(0)
                tables = page0.findChildren(QTableWidget) if page0 else []
                table = tables[0] if tables else getattr(self, "tableWidget_guankou", None)
                if table is None:
                    _, table = self._new_param_tab_like_default(label, insert_pos=0)
                    tw.removeTab(1)
                page0.setProperty("param_table", table)
            else:
                page, table = self._new_param_tab_like_default(label)
                page.setProperty("param_table", table)

            # 保存到字典
            self.dynamic_guankou_param_tabs[label] = table

            # 渲染
            data = param_map.get(label, [])
            old_table = getattr(self, "tableWidget_guankou", None)
            self.tableWidget_guankou = table
            try:
                render_guankou_param_to_ui(self, data)
                print(f"[DBG][refresh] 渲染完成 label={label}, data条数={len(data)}")  # ← zhange添加
                # 渲染完再补“管口号”
                self.patch_codes_for_current_tab(table, label)

            finally:
                self.tableWidget_guankou = old_table


    def load_original_data(self):

        def _norm_label(s: str) -> str:
            # 仅用于调试对齐：去掉全角空格/首尾空格
            if s is None:
                return ""
            return str(s).replace("\u3000", " ").strip()

        # 如果模板名称为空，则设置为 "None"字符串
        template_name = "None"
        self.product_type, self.product_form = load_design_product_data(product_id)
        self.product_id = product_id

        print(
            f"[DBG] load_original_data: product_id={self.product_id}, type={self.product_type}, form={self.product_form}")

        template_names = load_template(self.product_type, self.product_form)
        template_list = [
            "" if row['模板名称'] == "None" else row['模板名称']
            for row in template_names
        ]
        print(f"[DBG] 模板候选：{template_list}")

        self.comboBox_template.clear()
        self.comboBox_template.addItems(template_list)
        # 默认选中空白项
        index_blank = template_list.index("") if "" in template_list else 0
        # self.comboBox_template.setCurrentIndex(index_blank)

        # 👉 添加：监听下拉框变化，动态更新 lineEdit_template 的状态
        if not getattr(self, "_template_signal_connected", False):
            def _update_lineEdit_enabled(text):
                text = text.strip()
                # 控制可编辑状态
                if not text or text.lower() == "none":
                    self.lineEdit_template.setEnabled(False)
                    current_template_name = "None"
                else:
                    self.lineEdit_template.setEnabled(True)
                    current_template_name = text

                # ----------------------------
                # 这里是新增的核心逻辑：重新加载数据库数据
                element_original_info = load_elementoriginal_data(
                    current_template_name, self.product_type, self.product_form
                )

                # 插入数据库
                insert_element_data(element_original_info, self.product_id, current_template_name)

                # 渲染表格
                element_original_info = move_guankou_to_first(element_original_info)
                self.element_data = element_original_info
                self.render_data_to_table(element_original_info)

                # 渲染示意图
                self.image_paths = [item.get('零件示意图', '') for item in element_original_info]
                if self.image_paths:
                    self.display_image(self.image_paths[0])

            self.comboBox_template.currentTextChanged.connect(_update_lineEdit_enabled)
            self._template_signal_connected = True

        # 检查产品设计活动库数据
        if has_product(product_id):
            # 获取零件列表信息
            element_original_info = load_element_info(product_id)
            print(
                f"[DBG] 元件列表条数={len(element_original_info)}  示例前3项={[e.get('零件名称') for e in element_original_info[:3]]}")
            template_name_from_db = element_original_info[0].get("模板名称", "None")
            print(f"[DBG] DB模板名={repr(template_name_from_db)}")
            index = self.comboBox_template.findText(template_name_from_db)
            if index != -1:
                self.comboBox_template.setCurrentIndex(index)
            else:
                print(f"[WARN] 模板下拉框中找不到：{template_name_from_db}")

            # 👉 手动刷新一次 lineEdit 状态（避免没触发信号）
            current_text = self.comboBox_template.currentText()
            if not current_text or current_text.strip() == "" or current_text.strip().lower() == "None":
                self.lineEdit_template.setEnabled(False)
            else:
                self.lineEdit_template.setEnabled(True)


            guankou_define_dict = {}
            category_labels = query_all_guankou_categories(product_id)
            print(f"[DBG] 分类(原始)：{category_labels}")
            print(f"[DBG] 分类(repr)：{[repr(x) for x in category_labels]}")
            print(f"[DBG] 分类(规范化)：{[_norm_label(x) for x in category_labels]}")

            for label in category_labels:
                define_data = query_guankou_define_data_by_category(product_id, label)
                guankou_define_dict[label] = define_data
                print(
                    f"[DBG] 定义数据[{repr(label)}] 条数={len(define_data)}  示例={[d.get('参数名称') for d in define_data[:5]]}")
                self.label = label

        # 从模板库中读数据
        elif self.product_type and self.product_form:

            self.lineEdit_template.setEnabled(False)  # 首次无模板，禁用输入框

            element_original_info = load_elementoriginal_data(template_name, self.product_type, self.product_form)
            insert_element_data(element_original_info, product_id, template_name)
            if not element_original_info:
                self.show_error_message("数据加载错误", "没有找到零件数据")
                return

            # 管口类别表的读取插入
            guankou_info = query_guankou_default(self.product_type, self.product_form)
            insert_guankou_info(product_id, guankou_info)

            # 管口附加参数表的读取插入与渲染
            first_template_id = element_original_info[0].get('模板ID', None)
            guankou_para_info = query_template_guankou_para_data(first_template_id)
            insert_guankou_para_data(product_id, guankou_para_info, template_name)
            print(f"[DBG] 首次模板渲染参数条数={len(guankou_para_info)}")
            render_guankou_param_to_ui(self, guankou_para_info)

            element_para_info = query_template_element_para_data(first_template_id)
            insert_element_para_data(product_id, element_para_info)

            # 批量插入元件附加参数合并表数据（包括支座）
            from modules.cailiaodingyi.controllers.datamanager import batch_insert_element_merged_para_data
            batch_insert_element_merged_para_data(product_id, first_template_id, template_name)

            #加载布管参数表至数据库
            init_buguan_defaults(product_id)


        else:
            self.show_info_message("提示", "未选择产品，界面以空白状态打开。")
            self.lineEdit_template.setEnabled(False)
            return

        # 渲染零件列表数据(包括零件示意图)
        element_original_info = move_guankou_to_first(element_original_info)
        self.element_data = element_original_info
        self.render_data_to_table(element_original_info)

        # 示意图
        self.image_paths = [item.get('零件示意图', '') for item in element_original_info]
        if self.image_paths:
            QTimer.singleShot(1, lambda: self.display_image(self.image_paths[0]))

        # 取当前/默认 tab 的标题
        if self.guankou_tabWidget.count() > 0:
            current_index = self.guankou_tabWidget.currentIndex()
            category_label = self.guankou_tabWidget.tabText(current_index)
        else:
            category_label = category_labels[0] if category_labels else "管口材料分类1"
        print(
            f"[DBG] 当前Tab：index={getattr(self.guankou_tabWidget, 'currentIndex', lambda: -1)()} title={repr(category_label)}")

        if has_product(product_id):

            # 同步腐蚀裕量
            category_labels = query_all_guankou_categories(product_id)
            print(f"[DBG] 准备同步腐蚀裕量的分类：{category_labels}")
            for category_label in category_labels:
                guankou_codes = query_guankou_codes(self.product_id, category_label) or []
                print(f"[DBG] 产品 {self.product_id}, 分类 {repr(category_label)} 的管口号: {guankou_codes}")
                sync_corrosion_to_guankou_param(product_id, guankou_codes, category_label)

            # 构建 param_map -> 渲染
            labels = query_all_guankou_categories(self.product_id) or ["管口材料分类1"]
            param_map = {}
            for label in labels:
                rows = query_guankou_param_by_product(self.product_id, label) or []
                param_map[label] = rows
                print(f"[DBG] param_map[{repr(label)}] 条数={len(rows)} "
                      f"示例参数={[r.get('参数名称') for r in rows[:5]]}")

            print(f"[DBG] 传入 build_or_refresh 的 keys：{[repr(k) for k in param_map.keys()]}")

            # 调用建/刷 tabs
            self.build_or_refresh_guankou_tabs_from_db(param_map)

            # 打印最终 QTabWidget 的标题列表
            titles = [self.guankou_tabWidget.tabText(i) for i in range(self.guankou_tabWidget.count())]
            print(f"[DBG] QTabWidget 当前tabs：{[repr(t) for t in titles]}")


    def render_data_to_table(self, element_original_info):
        # 获取表格控件
        table = self.tableWidget_parts

        # 清理原有数据（防止重复）
        table.clear()

        # 设置表格的列标题
        headers = ["序号", "零件名称", "材料类型", "材料牌号", "材料标准", "供货状态", "有无覆层", "是否定义",
                   "所属部件"]
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)

        # 设置表格的行数为数据条数
        table.setRowCount(len(element_original_info))

        # 启用表头点击事件
        header = table.horizontalHeader()
        header.setSectionsClickable(True)
        header.setSectionsMovable(True)
        try:
            header.sectionClicked.disconnect(self.on_header_clicked)
        except TypeError:
            pass
        header.sectionClicked.connect(self.on_header_clicked)

        # 设置列宽
        for i in range(table.columnCount()):
            if i in (0, 7, 8):
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

        # 强制不出现水平滚动条
        table.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)

        # 让表头更高一点，留出分隔感
        table.horizontalHeader().setFixedHeight(35)

        # 用 QSS 尝试在表头底部挤出视觉间隔
        table.setStyleSheet("""
        QHeaderView::section {
            padding-bottom: 5px;
            background-color: #f9f9f9;
            border: none;
        }
        QTableWidget::item {
            margin-top: 2px;
        }
        """)

        # 限制最后一列最大宽度（可选）
        last_col = table.columnCount() - 1
        table.setColumnWidth(last_col, 100)

        # 遍历数据并填入表格
        for row_index, row_data in enumerate(element_original_info):
            for col_idx, key in enumerate(headers):
                if key == "序号":
                    item = QTableWidgetItem(f"{row_index + 1:02d}")
                else:
                    item = QTableWidgetItem(str(row_data.get(key, "")))
                item.setTextAlignment(Qt.AlignCenter)
                item.setToolTip(item.text())  # ✅ 添加悬浮提示
                table.setItem(row_index, col_idx, item)

        # ✅ 视觉分隔效果【核心】
        table.setShowGrid(True)
        table.setGridStyle(QtCore.Qt.SolidLine)
        table.setStyleSheet("QTableWidget { gridline-color: lightgray; }")

    def on_header_clicked(self, column):
        """表头点击事件：显示筛选菜单"""
        table = self.tableWidget_parts
        header = table.horizontalHeader()
        header_text = table.horizontalHeaderItem(column).text()

        # 创建菜单
        menu = QtWidgets.QMenu(self)

        # 添加排序和筛选选项
        sort_asc_action = menu.addAction(f"升序排序 ({header_text})")
        sort_desc_action = menu.addAction(f"降序排序 ({header_text})")
        menu.addSeparator()

        # 添加筛选选项
        filter_menu = menu.addMenu("筛选")
        filter_all_action = filter_menu.addAction("显示全部")
        reset_filter_action = filter_menu.addAction("重置筛选（清空所有记录）")
        filter_menu.addSeparator()

        # 只考虑当前未隐藏的行
        visible_values = set()
        for row in range(table.rowCount()):
            if not table.isRowHidden(row):
                item = table.item(row, column)
                if item:
                    visible_values.add(item.text())

        for value in sorted(visible_values):
            filter_action = filter_menu.addAction(value)

        # 显示菜单并等待用户选择
        selected_action = menu.exec_(QtGui.QCursor.pos())

        # 处理用户选择
        if selected_action == sort_asc_action:
            table.sortItems(column, Qt.AscendingOrder)
        elif selected_action == sort_desc_action:
            table.sortItems(column, Qt.DescendingOrder)
        elif selected_action == filter_all_action:
            if self.visible_rows_stack:
                previous_visible = self.visible_rows_stack.pop()
                for row in range(table.rowCount()):
                    table.setRowHidden(row, row not in previous_visible)
            else:
                for row in range(table.rowCount()):
                    table.setRowHidden(row, False)

        elif selected_action == reset_filter_action:
            self.visible_rows_stack.clear()
            for row in range(table.rowCount()):
                table.setRowHidden(row, False)
        elif selected_action in filter_menu.actions():
            filter_value = selected_action.text()
            current_visible_rows = [row for row in range(table.rowCount()) if not table.isRowHidden(row)]
            self.visible_rows_stack.append(current_visible_rows)
            for row in current_visible_rows:
                item = table.item(row, column)
                if not item or item.text() != filter_value:
                    table.setRowHidden(row, True)
        menu.close()
        # 关键修复：取消表头选中状态
        header.setHighlightSections(False)  # 禁用高亮
        header.clearSelection()  # 清除选中状态
        table.clearSelection()  # 清除表格单元格的选中状态（可选）

    def filter_table_globally(self, keyword):
        """全局筛选：匹配所有列的任意单元格"""
        table = self.tableWidget_parts
        keyword = keyword.strip().lower()  # 忽略大小写和前后空格
        # 遍历所有行（跳过表头筛选行）
        for row in range(0, table.rowCount()):  # 假设第0行是筛选行
            row_visible = False
            # 检查当前行的每一列是否匹配关键词
            for col in range(table.columnCount()):
                item = table.item(row, col)
                if item and keyword in item.text().lower():
                    row_visible = True
                    break  # 只要有一列匹配就显示该行

            # 设置行可见性
            table.setRowHidden(row, not row_visible)

    def show_image_in_text_browser(self, selected, deselected):
        # 获取选中的行
        selected_row = self.tableWidget_parts.selectedIndexes()

        if selected_row:
            row = selected_row[0].row()  # 获取选中行的索引
            # print(f"Selected row index: {row}")

            # 从内存中获取零件示意图的路径
            if row < len(self.image_paths):  # 确保索引有效
                image_path = self.image_paths[row]
                # print(f"Image path: {image_path}")

                # 显示图片到右侧的QTextBrowser控件
                self.display_image(image_path)
            else:
                self.show_error_message("无效的行索引", "所选行没有有效的图片路径。")
        else:
            print("No row selected")

    def display_image(self, image_path):
        if not image_path:
            self.label_part_image.clear()
            return

        image_path = os.path.normpath(image_path.strip())
        if not os.path.isabs(image_path):
            base_dir = os.path.dirname(os.path.abspath(__file__))
            # 这里添加 img 目录
            abs_path = os.path.join(base_dir, "img", image_path)
        else:
            abs_path = image_path

        if not os.path.exists(abs_path):
            print(f"[警告] 图片路径不存在: {abs_path}")
            self.label_part_image.clear()
            return

        pixmap = QPixmap(abs_path)
        if pixmap.isNull():
            print(f"[警告] 图片无法加载: {abs_path}")
            self.label_part_image.clear()
            return

        # ✅ 获取控件实际尺寸
        label_size = self.label_part_image.size()
        if label_size.width() <= 0 or label_size.height() <= 0:
            print("[提示] QLabel 尺寸未准备好，跳过")
            return

        # ✅ 使用 Qt.SmoothTransformation 进行平滑缩放
        scaled_pixmap = pixmap.scaled(
            label_size,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # ✅ 设置图片
        self.label_part_image.setPixmap(scaled_pixmap)
        self.label_part_image.setAlignment(Qt.AlignCenter)

    def render_details_to_table(self, element_details):
        print("render_details_to_table called")

        if self.first_element_id:
            print(f"Calling load_element_details with element_id: {self.first_element_id}")
            element_details = load_element_details(self.first_element_id)
        else:
            print("没有找到元件ID")
            return

        details_table = self.tableWidget_detail
        headers = ["参数名称", "参数数值", "参数单位"]

        details_table.setColumnCount(len(headers))
        details_table.setRowCount(len(element_details))
        details_table.setHorizontalHeaderLabels(headers)

        header = details_table.horizontalHeader()
        for i in range(details_table.columnCount()):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

        for row_index, row_data in enumerate(element_details):
            for col_idx, header_name in enumerate(headers):
                item = QTableWidgetItem(str(row_data.get(header_name, "")))
                item.setTextAlignment(QtCore.Qt.AlignCenter)

                # ✅ 设置只读（不可编辑）列：参数名称 和 参数单位
                if col_idx in [0, 2]:  # 参数名称列 和 参数单位列
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                details_table.setItem(row_index, col_idx, item)

    def render_guankou_param_table(self, table: QTableWidget, guankou_param_info):

        """渲染上半部分管口参数表"""

        headers = ["零件名称", "材料类型", "材料牌号", "材料标准", "供货状态"]
        table.setColumnCount(len(headers))
        table.setRowCount(len(guankou_param_info))
        table.setHorizontalHeaderLabels(headers)

        header = table.horizontalHeader()

        # 隐藏列序号
        table.verticalHeader().setVisible(False)

        for i in range(table.columnCount()):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

        for row_index, row_data in enumerate(guankou_param_info):
            for col_idx, header_name in enumerate(headers):
                item = QTableWidgetItem(str(row_data.get(header_name, "")))
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row_index, col_idx, item)

    def render_guankou_material_detail_table(self, table: QTableWidget, material_details):

        """渲染右下半部分管口零件材料详细表"""
        # 清空现有数据
        print(f"覆盖")
        table.clear()  # 清除所有行列和表头
        table.setRowCount(0)
        table.setColumnCount(0)

        headers = ["参数名称", "参数值", "参数单位"]
        table.setColumnCount(len(headers))
        table.setRowCount(len(material_details))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)

        header = table.horizontalHeader()

        # 隐藏列序号
        table.verticalHeader().setVisible(False)

        for i in range(table.columnCount()):
            header.setSectionResizeMode(i, QtWidgets.QHeaderView.Stretch)

        for row_index, row_data in enumerate(material_details):
            for col_idx, header_name in enumerate(headers):
                item = QTableWidgetItem(str(row_data.get(header_name, "")))
                item.setTextAlignment(QtCore.Qt.AlignCenter)

                # ✅ 设置只读（不可编辑）列：参数名称 和 参数单位
                if col_idx in [0, 2]:  # 参数名称列 和 参数单位列
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)

                table.setItem(row_index, col_idx, item)

    def add_guankou_category_tab(self, mode='add'):
        print(f"[调试] 开始执行 add_guankou_category_tab，模式: {mode}")
        new_tab = QWidget()
        table_guankou_define = QTableWidget()
        table_guankou_param = QTableWidget()
        table_guankou_define.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, table_guankou_define))
        table_guankou_param.setHorizontalHeader(CustomHeaderView(QtCore.Qt.Horizontal, table_guankou_param))
        table_guankou_define.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        table_guankou_param.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)

        upper_layout = QtWidgets.QVBoxLayout()
        upper_layout.addWidget(table_guankou_define)
        lower_layout = QtWidgets.QVBoxLayout()
        lower_layout.addWidget(table_guankou_param)
        main_layout = QtWidgets.QVBoxLayout()
        main_layout.addLayout(upper_layout, 1)
        main_layout.addLayout(lower_layout, 1)
        new_tab.setLayout(main_layout)

        # ✅ 使用唯一 tab 名
        tab_label = self.generate_unique_guankou_label()
        category_label = tab_label
        print(f"[调试] 新 tab_label = {tab_label}")

        index = self.guankou_tabWidget.addTab(new_tab, tab_label)

        # 注册映射
        self.dynamic_guankou_param_tabs[tab_label] = table_guankou_param
        self.dynamic_guankou_define_tabs[tab_label] = table_guankou_define

        select_template = self.comboBox_template.currentText() or 'None'
        print(f"[调试] 当前选择的模板: {select_template}")
        template_id = select_template_id(select_template, self.product_form, self.product_type)
        print(f"[调试] 模板ID: {template_id}, 分类标签: {category_label}")

        if mode == 'add':
            guankou_define_data = load_guankou_define_data(self.product_type, self.product_form, template_id)
            insert_add_guankou_define(guankou_define_data, category_label, self.product_id, select_template)
            self.render_guankou_param_table(table_guankou_define, guankou_define_data)
        elif mode == 'copy':
            current_index = self.guankou_tabWidget.currentIndex()
            current_tab = self.guankou_tabWidget.tabText(current_index)
            guankou_define_data = load_guankou_define_leibie(current_tab, self.product_id, select_template)
            insert_add_guankou_define(guankou_define_data, category_label, self.product_id, select_template)
            self.render_guankou_param_table(table_guankou_define, guankou_define_data)

        dropdown_data = load_material_dropdown_values()
        column_index_map = {'材料类型': 1, '材料牌号': 2, '材料标准': 3, '供货状态': 4}
        column_data_map = {column_index_map[k]: v for k, v in dropdown_data.items()}
        apply_combobox_to_table(table_guankou_define, column_data_map, guankou_define_data,
                                self.product_id, self, category_label)
        self.guankou_define_info = guankou_define_data
        set_table_tooltips(table_guankou_define)

        table_guankou_define.cellClicked.connect(
            lambda row, col, d=guankou_define_data, t=table_guankou_param, c=category_label:
            self.on_define_table_clicked(row, d, t, c)
        )

        if mode == 'add':
            guankou_param_id = guankou_define_data[0].get('管口零件ID')
            guankou_param_data = load_guankou_material_detail_template(guankou_param_id, template_id)
            ca_map = get_design_params_by_product_id(self.product_id)
            tube_ca = ca_map.get("腐蚀裕量*", {}).get("管程数值", "")
            shell_ca = ca_map.get("腐蚀裕量*", {}).get("壳程数值", "")
            for item in guankou_param_data:
                if item.get("参数名称") == "管程接管腐蚀裕量" and tube_ca != "":
                    item["参数值"] = str(tube_ca)
                elif item.get("参数名称") == "壳程接管腐蚀裕量" and shell_ca != "":
                    item["参数值"] = str(shell_ca)
                    break
            print(f"[调试] 新增的管口零件参数信息: {guankou_param_data}")
            all_guankou_param_data = query_template_guankou_para_data(template_id)
            insert_all_guankou_param(all_guankou_param_data, category_label, self.product_id, select_template)
            sync_corrosion_to_guankou_param(self.product_id)
            self.render_guankou_material_detail_table(table_guankou_param, guankou_param_data)
        elif mode == 'copy':
            current_index = self.guankou_tabWidget.currentIndex()
            current_tab = self.guankou_tabWidget.tabText(current_index)
            guankou_param_data = load_guankou_param_leibie(current_tab, self.product_id, select_template)
            guankou_param_id = guankou_define_data[0].get('管口零件ID')
            guankou_param = load_guankou_param_byid(current_tab, self.product_id, select_template, guankou_param_id)
            self.render_guankou_material_detail_table(table_guankou_param, guankou_param)
            insert_all_guankou_param(guankou_param_data, category_label, self.product_id, select_template)

        apply_gk_paramname_combobox(table_guankou_param, param_col=0, value_col=1)
        self.dynamic_guankou_tabs.append(new_tab)

    def on_define_table_clicked(self, row, define_data, table_param, category_label):
        """
        监控添加管口零件分类的材料定义
        """

        guankou_row = define_data[row] if row < len(define_data) else {}
        print(f"管口定义{guankou_row}")
        guankou_id = guankou_row.get('管口零件ID')
        part_name = guankou_row.get('零件名称', '')


        if not guankou_id:
            print("[调试] 跳过：无有效管口ID")
            return  # 避免空数据覆盖

        # 保存当前点击项（供后续使用）
        self.clicked_guankou_define_data = guankou_row
        self.clicked_guankou_define_data["类别"] = category_label
        image_path = guankou_row.get('元件示意图')
        self.display_image(image_path)

        # 查询参数：先查产品库，再查模板库
        param_data = query_guankou_param_by_product(self.product_id, guankou_id, category_label)
        print(f"当前产品{self.product_id}，当前管口ID{guankou_id}，当前类别{category_label}")
        print(f"产品库数据{param_data}")

        if not param_data:
            param_data = query_guankou_param_by_template(guankou_id, category_label, )
            print(f"材料库数据{param_data}")

        if param_data:
            self.render_guankou_material_detail_table(table_param, param_data)
            param_row_data = param_data[0]  # ✅ 取出第一行参数数据当作 component_info


            # 绑定参数下拉逻辑
            param_options = load_material_dropdown_values()
            # apply_paramname_dependent_combobox(
            #     self.tableWidget_guankou_param,
            #     param_col=0,
            #     value_col=1,
            #     param_options=param_options,
            #     component_info=guankou_row,
            #     viewer_instance=self
            # )
            # apply_paramname_dependent_combobox(
            #     table_param,
            #     param_col=0,
            #     value_col=1,
            #     param_options=param_options
            # )
            apply_gk_paramname_combobox(
                table_param,
                param_col=0,
                value_col=1,
                component_info=param_row_data,
                viewer_instance=self
            )
        else:
            # 无数据时清空参数表格（防止显示旧内容）
            table_param.clear()
            table_param.setRowCount(0)
            table_param.setColumnCount(3)
            table_param.setHorizontalHeaderLabels(["参数名称", "参数值", "参数单位"])

    #
    # def handle_table_click_guankou(self, row, column):
    #     # 获取当前行的“零件名称”
    #     part_name_item = self.tableWidget_parts.item(row, 1)
    #     if part_name_item and part_name_item.text() == "管口":
    #         self.stackedWidget.setCurrentIndex(0)
    #     else:
    #         self.stackedWidget.setCurrentIndex(1)

    def handle_table_click_guankou(self, row, column):
        # 获取当前行的"零件名称"
        part_name_item = self.tableWidget_parts.item(row, 1)
        if part_name_item:
            part_name = part_name_item.text()
            print(f"[调试] 点击的零件名称: {part_name}")

            if part_name == "管口":
                self.stackedWidget.setCurrentIndex(0)  # 管口页面
            elif part_name in ["支座", "铭牌", "保温支撑"]:  # 支座和铭牌支架使用同一个UI界面  # 新增保温支撑
                self.stackedWidget.setCurrentIndex(2)  # 鞍座页面 (page_3)
                print(f"[调试] 跳转到鞍座页面: {part_name}")
            elif "鞍座" in part_name:  # 其他鞍座类型（如滑动鞍座）使用普通渲染
                self.stackedWidget.setCurrentIndex(1)  # 其他元件页面
            else:
                self.stackedWidget.setCurrentIndex(1)  # 其他元件页面
        else:
            self.stackedWidget.setCurrentIndex(1)  # 默认其他元件页面


    def save_associated_data(self, template_id):
        """保存关联数据到其他表（直接使用template_id）"""
        try:
            # 1. 保存元件参数
            updated_element_para = load_update_element_data(self.product_id)
            insert_updated_element_para_data(template_id, updated_element_para)
            # 2. 保存管口定义
            updated_guankou_define = load_update_guankou_define_data(self.product_id)
            insert_guankou_define_data(
                template_id,
                updated_guankou_define,
                self.product_type,
                self.product_form
            )
            # 3. 保存管口参数
            updated_guankou_para = load_update_guankou_para_data(self.product_id)
            insert_guankou_para_info(template_id, updated_guankou_para)
        except Exception as e:
            print(f"关联数据保存失败: {e}")
            raise

    def load_template_by_id(self, template_id):
        """直接通过模板ID加载数据（复用现有逻辑）"""
        # 调用现有的load_data_by_template函数，优先使用template_id
        load_data_by_template(self, template_id=template_id)


    # 监控存为模板输入框
    def on_template_name_entered(self):
        template_name = self.lineEdit_template.text().strip()
        print(f"当前输入的模板名称{template_name}")
        if not template_name:
            self.show_error_message("提示", "请输入模板名称后再按回车。")
            return

        # ✅ 从界面上检查未定义的元件
        undefined_parts = []
        name_col = 1  # 假设第1列是“元件名称”
        status_col = 7  # 第7列是“定义状态”（根据你的注释）
        table = self.tableWidget_parts
        for row in range(table.rowCount()):
            name_item = table.item(row, name_col)
            status_item = table.item(row, status_col)
            if not name_item:
                continue
            name = name_item.text().strip()
            status = status_item.text().strip() if status_item else ""
            if status != "已定义":
                undefined_parts.append(name)

        # ✅ 查询产品材料数据
        product_data = load_element_info(self.product_id)
        if not product_data:
            self.show_error_message("错误", "未找到产品材料数据。")
            return

        # ✅ 写入模板库
        save_to_template_library(template_name, product_data, self.product_type, self.product_form)

        # ✅ 更新模板关联数据
        template_id = get_template_id_by_name(template_name)
        if template_id is not None:
            print(f"查询到模板ID：{template_id}")
            updated_element_para = load_update_element_data(self.product_id)
            insert_updated_element_para_data(template_id, updated_element_para)
            updated_guankou_define = load_updated_guankou_define_data(self.product_id)
            print(f"u管口{updated_guankou_define}")
            insert_guankou_define_data(template_id, updated_guankou_define)
        else:
            print("未找到对应模板ID")

        # ✅ 合并提示信息（只弹一次）
        if undefined_parts:
            msg = f"模板 '{template_name}' 已保存到材料库。\n以下元件未定义：\n" + "、".join(undefined_parts)
        else:
            msg = f"模板 '{template_name}' 已保存到材料库。"

        QMessageBox.information(self, "模板保存结果", msg)


    def on_param_table_selection_changed(self):
        table = self.tableWidget_para_define

        selected_items = table.selectedItems()
        selected_cells = {(item.row(), item.column()) for item in selected_items}
        selected_rows = {row for row, _ in selected_cells}

        # 1. 清除所有背景
        for r in range(table.rowCount()):
            for c in range(table.columnCount()):
                item = table.item(r, c)
                if item:
                    if (r, c) in selected_cells:
                        continue  # 保留深蓝
                    item.setBackground(Qt.white)

        # 2. 高亮选中行其他未选中单元格
        for row in selected_rows:
            for col in range(table.columnCount()):
                if (row, col) in selected_cells:
                    continue
                item = table.item(row, col)
                if item:
                    item.setBackground(QColor("#d0e7ff"))


# def startCailiao():
#     app = QApplication(sys.argv)
#     window = DesignParameterDefineInputerViewer()
#     window.show()  # 显示窗口
#     sys.exit(app.exec_())  # 启动事件循环
