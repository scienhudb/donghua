
# ============================= 设备法兰紧固件 =============================
def on_clear_fastener_param_update(viewer_instance):
    """清空当前PNO页的设备法兰紧固件参数（仅清值，保留记录与结构）"""
    from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem

    tw = getattr(viewer_instance, "tabWidget_3", None)
    if tw is None or tw.currentIndex() < 0:
        return

    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()

    # 定位表格
    current_page = tw.widget(cur_idx)
    table_param = current_page.property('param_table') if current_page else None
    if table_param is None and hasattr(viewer_instance, 'dynamic_fastener_param_tabs'):
        table_param = viewer_instance.dynamic_fastener_param_tabs.get(tab_name)

    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return

    # 确认弹窗
    box = QMessageBox(QMessageBox.Information, "清空确认",
                      "清空后不可撤销，是否继续？",
                      QMessageBox.NoButton, tw)
    btn_ok = box.addButton("确认", QMessageBox.YesRole)
    btn_cancel = box.addButton("取消", QMessageBox.NoRole)
    box.setDefaultButton(btn_cancel)
    box.exec_()
    if box.clickedButton() is not btn_ok:
        print("[设备法兰紧固件清空] 用户取消操作")
        return

    # UI 清空，保留元件名称
    preserved_params = {"元件名称"}
    table_param.blockSignals(True)
    try:
        for r in range(table_param.rowCount()):
            it0 = table_param.item(r, 0)
            param_label = it0.text().strip() if it0 else ""
            if not param_label:
                continue

            if param_label in preserved_params:
                # 保持"设备法兰紧固件"字样
                it = table_param.item(r, 1)
                if it:
                    it.setText("设备法兰紧固件")
                else:
                    table_param.setItem(r, 1, QTableWidgetItem("设备法兰紧固件"))
                # 如果是多列，其他列清空
                for c in range(2, table_param.columnCount()):
                    itc = table_param.item(r, c)
                    if itc:
                        itc.setText("")
                continue

            for c in range(1, table_param.columnCount()):
                it = table_param.item(r, c)
                if it:
                    it.setText("")
    finally:
        table_param.blockSignals(False)

    # DB 清空（不删除记录，仅置空参数值，保留元件名称）
    product_id = getattr(viewer_instance, 'product_id', None)
    element_id = getattr(viewer_instance, 'current_element_id', None)
    # 若视图未缓存当前元件ID，尝试从列表选择处读取
    if element_id is None:
        element_id = getattr(viewer_instance, 'current_fastener_element_id', None)
    print(f"元件id{element_id}产品id{product_id}")
    try:
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                if product_id and element_id:
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数合并表
                        SET 参数值 = ''
                        WHERE 产品ID = %s AND 元件ID = %s AND Tab分类 = %s 
                        """,
                        (product_id, element_id, tab_name)
                    )
                    connection.commit()
        finally:
            connection.close()
    except Exception as e:
        print(f"[设备法兰紧固件清空] 数据库清空失败: {e}")

    print(f"[设备法兰紧固件清空] Tab {tab_name} 清空完成")




def update_fastener_tab_data_from_table(table_param, product_id, element_id, tab_name):
    """保存设备法兰紧固件当前Tab的所有参数到数据库。
    规则：
    - 2列结构：更新 参数名称
    - 3列结构：更新 参数名称1, 参数名称2
    - 4列结构：更新 参数名称1..3
    """
    # 拉取结构定义
    try:
        structures = get_fastener_param_structure_from_db()
        name2struct = {name: struct for name, struct, _ctl, _pre in structures}
    except Exception as e:
        print(f"[设备法兰紧固件保存] 获取结构失败，默认按3列处理: {e}")
        name2struct = {}

    try:
        connection = get_connection(**db_config_1)
        try:
            with connection.cursor() as cursor:
                row_cnt = table_param.rowCount()
                col_cnt = table_param.columnCount()

                for r in range(row_cnt):
                    it0 = table_param.item(r, 0)
                    if not it0:
                        continue
                    param_name = (it0.text() or '').strip()
                    struct = name2struct.get(param_name, '3列')

                    def _update_one(name, value):
                        try:
                            cursor.execute(
                                """
                                UPDATE 产品设计活动表_元件附加参数合并表
                                SET 参数值 = %s
                                WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = %s AND Tab分类 = %s
                                """,
                                (value, product_id, element_id, name, tab_name)
                            )
                        except Exception as inner:
                            print(f"[设备法兰紧固件保存] 更新失败 {name}={value}: {inner}")

                    if struct == '2列':
                        v = table_param.item(r, 1).text().strip() if table_param.item(r, 1) else ''
                        _update_one(param_name, v)
                    elif struct == '4列':
                        for i in range(1, min(col_cnt, 4)):
                            v = table_param.item(r, i).text().strip() if table_param.item(r, i) else ''
                            _update_one(f"{param_name}{i}", v)
                    else:  # 默认3列
                        # 可能为跨列单值，或两列独立值
                        v1 = table_param.item(r, 1).text().strip() if table_param.item(r, 1) else ''
                        v2 = table_param.item(r, 2).text().strip() if col_cnt > 2 and table_param.item(r, 2) else ''
                        # 始终写入 name1/name2，若仅单值则name1有值，name2为空
                        _update_one(f"{param_name}1", v1)
                        _update_one(f"{param_name}2", v2)

                connection.commit()
                print(f"[设备法兰紧固件保存] Tab {tab_name} 更新完成")
        finally:
            connection.close()
    except Exception as e:
        print(f"[设备法兰紧固件保存] 失败: {e}")
        raise


def on_confirm_fastener_param(viewer_instance):
    """设备法兰紧固件 - 确定按钮处理：保存并刷新UI"""
    from PyQt5.QtWidgets import QMessageBox

    tw = getattr(viewer_instance, "tabWidget_3", None)
    if tw is None or tw.currentIndex() < 0:
        print("[设备法兰紧固件确定] 未找到tabWidget_3")
        return

    cur_idx = tw.currentIndex()
    tab_name = tw.tabText(cur_idx).strip()

    # 表格
    page = tw.widget(cur_idx)
    table_param = page.property('param_table') if page else None
    if table_param is None and hasattr(viewer_instance, 'dynamic_fastener_param_tabs'):
        table_param = viewer_instance.dynamic_fastener_param_tabs.get(tab_name)

    if table_param is None:
        QMessageBox.warning(viewer_instance, "错误", f"未找到 {tab_name} 的参数表")
        return

    product_id = getattr(viewer_instance, "product_id", None)
    element_id = getattr(viewer_instance, 'current_element_id', None)
    if element_id is None:
        element_id = getattr(viewer_instance, 'current_fastener_element_id', None)

    if not product_id or not element_id:
        QMessageBox.warning(viewer_instance, "错误", "未找到产品或元件ID")
        return

    try:
        # 保存当前Tab全部参数
        update_fastener_tab_data_from_table(table_param, product_id, element_id, tab_name)

        # 强制提交
        if hasattr(viewer_instance, 'force_commit'):
            viewer_instance.force_commit()

        # 刷新UI：重新加载并渲染
        data = load_updated_fastener_define_data(product_id, element_id)
        render_fastener_param_to_ui(viewer_instance, data)

        QMessageBox.information(viewer_instance, "提示", f"{tab_name} 的参数已保存")
    except Exception as e:
        print(f"[设备法兰紧固件确定] 保存失败：{e}")
        QMessageBox.warning(viewer_instance, "错误", f"保存失败：{e}")















# paradefine_view

        # 设备法兰紧固件 清空/确定
        self.pushButton_fastener_clear = self.findChild(QPushButton, "pushButton_12")
        if self.pushButton_fastener_clear:
            from modules.cailiaodingyi.controllers.datamanager import on_clear_fastener_param_update
            self.pushButton_fastener_clear.clicked.connect(lambda: on_clear_fastener_param_update(self))

        self.pushButton_fastener_confirm = self.findChild(QPushButton, "pushButton_13")
        if self.pushButton_fastener_confirm:
            from modules.cailiaodingyi.controllers.datamanager import on_confirm_fastener_param
            self.pushButton_fastener_confirm.clicked.connect(lambda: on_confirm_fastener_param(self))
























            elif part_name == "设备法兰紧固件":
                self.stackedWidget.setCurrentIndex(3)  # page_4 - 设备法兰紧固件页面
                try:
                    element_id = self.element_data[row].get("元件ID")
                    print(f"[调试] 元件ID: {element_id}")
                    # 缓存当前选择的设备法兰紧固件 元件ID，供“清空/确定”使用
                    self.current_element_id = element_id
                    self.current_fastener_element_id = element_id

                    from modules.cailiaodingyi.funcs.funcs_pdf_change import load_updated_fastener_define_data
                    from modules.cailiaodingyi.funcs.funcs_pdf_render import render_fastener_param_to_ui
                    updated_fastener_define_info = load_updated_fastener_define_data(self.product_id, element_id)
                    print(f"更新设备法兰紧固件{updated_fastener_define_info}")
                    render_fastener_param_to_ui(self, updated_fastener_define_info)

                except Exception as e:
                    print(f"[设备法兰紧固件] 数据加载失败: {e}")
                    return







#pdf_change


def load_updated_fastener_define_data(product_id, element_id):
    """查询设备法兰紧固件合并展示表数据"""
    connection = get_connection(**db_config_1)
    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT  参数名称, 参数值, 参数单位,Tab分类,模板ID
            FROM 产品设计活动表_元件附加参数合并表
            WHERE 产品ID = %s AND 元件ID = %s
            """
            cursor.execute(sql, (product_id, element_id))
            result = cursor.fetchall()
            print(f"[DBG][fastener_data] 产品{product_id}的元件{element_id}查询到数据: {len(result)} 条")

            return result

    finally:
        connection.close()


def get_fastener_component_options_by_template_id(template_id):
    """根据模板ID获取元件所属的候选项"""
    component_options_map = {
        "5": ["管箱平盖", "管箱法兰"],
        "22": ["管箱平盖", "管箱法兰"],
        "23": ["管箱平盖", "管箱法兰"],
        "6": ["管箱法兰"],
        "20": ["管箱法兰"],
        "24": ["管箱法兰"],
        "4": ["管箱平盖", "管箱法兰", "外头盖法兰", "浮头法兰"],
        "25": ["管箱平盖", "管箱法兰", "外头盖法兰", "浮头法兰"],
        "26": ["管箱平盖", "管箱法兰", "外头盖法兰", "浮头法兰"],
        "7": ["管箱法兰", "外头盖法兰", "浮头法兰"],
        "27": ["管箱法兰", "外头盖法兰", "浮头法兰"],
        "28": ["管箱法兰", "外头盖法兰", "浮头法兰"],
        "8": ["前端管箱平盖", "后端管箱平盖"],
        "30": ["前端管箱平盖", "后端管箱平盖"],
        "31": ["前端管箱平盖", "后端管箱平盖"],
        "29": ["前端管箱法兰", "前端管箱法兰"]
    }

    return component_options_map.get(str(template_id), [])


def get_fastener_bolt_type_options():
    """获取螺柱型式的候选项"""
    return ["（A）等径双头螺柱", "（B）缩径双头螺柱", "（C）全螺纹螺柱"]


# pdf_input


def get_fastener_param_structure_from_db() -> list:
    connection = pymysql.connect(**db_config_2)
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 参数名称, 显示结构, 控件类型, 字段前缀 FROM 设备法兰紧固件合并展示表 ORDER BY 参数ID")
            results = cursor.fetchall()
            return results
    finally:
        connection.close()





# render

def render_fastener_param_to_ui(viewer_instance, fastener_para_info: list):
    """渲染设备法兰紧固件参数到UI - 支持PNO.x格式的tab页面"""
    print(
        f"[DBG][fastener_render] 开始渲染设备法兰紧固件，数据条数={0 if fastener_para_info is None else len(fastener_para_info)}")

    # 获取参数结构
    param_structures = get_fastener_param_structure_from_db()
    print(f"[DBG][fastener_render] 参数结构: {param_structures}")

    # 根据参数结构确定列数
    max_cols = 3  # 默认3列：参数名 + 参数值1 + 参数值2
    for _, structure, _, _ in param_structures:
        if structure == "4列":
            max_cols = 4
            break
        elif structure == "3列":
            max_cols = 3  # 3列结构：参数名 + 参数值1 + 参数值2
        elif structure == "2列":
            max_cols = 3  # 2列结构也使用3列表格，但会合并单元格

    # 获取候选项
    template_id = fastener_para_info[0].get('模板ID') if fastener_para_info else None
    print(f"[DBG][fastener_render] 模板ID: {template_id}")
    component_options = get_fastener_component_options_by_template_id(template_id)
    print(f"[DBG][fastener_render] 元件所属候选项: {component_options}")
    bolt_type_options = get_fastener_bolt_type_options()
    print(f"[DBG][fastener_render] 螺柱型式候选项: {bolt_type_options}")

    dropdown_options = {
        "元件所属": component_options,
        "螺柱型式": bolt_type_options,
    }
    print(f"[DBG][fastener_render] 下拉框选项: {dropdown_options}")

    # 处理数据分组 - 按Tab分类字段分组
    param_map = {}
    if fastener_para_info:
        for item in fastener_para_info:
            # 使用Tab分类字段进行分组
            tab_class = item.get('Tab分类', 'PNO.1')  # 默认PNO.1
            if tab_class not in param_map:
                param_map[tab_class] = []
            param_map[tab_class].append(item)
    else:
        # 如果没有数据，创建默认的PNO.1
        param_map = {"PNO.1": []}

    print(f"[DBG][fastener_render] 参数分组: {list(param_map.keys())}")

    # 获取或创建tabWidget - 设备法兰紧固件使用tabWidget_3
    tw = getattr(viewer_instance, "tabWidget_3", None)
    if not tw:
        print("[DBG][fastener_render] 未找到tabWidget_3")
        return
    # 清空现有tab页（保留+号tab）
    has_plus = (tw.count() > 0 and tw.tabText(tw.count() - 1).strip() in {"+", "＋"})
    last_real = tw.count() - (1 if has_plus else 0)
    for i in range(last_real - 1, 0, -1):
        w = tw.widget(i)
        tw.removeTab(i)
        if w:
            w.deleteLater()

    # 初始化动态tab字典
    if not hasattr(viewer_instance, "dynamic_fastener_param_tabs"):
        viewer_instance.dynamic_fastener_param_tabs = {}
    viewer_instance.dynamic_fastener_param_tabs.clear()

    # 为每个PNO创建tab页
    for idx, (pno_label, data) in enumerate(param_map.items()):
        if idx == 0:
            # 第一个tab，复用现有的
            tw.setTabText(0, pno_label)
            page0 = tw.widget(0)
            tables = page0.findChildren(QTableWidget) if page0 else []
            table = tables[0] if tables else getattr(viewer_instance, "tableWidget_define1_3", None)
            if table is None:
                print("[DBG][fastener_render] 未找到tableWidget_define1_3")
                return
            page0.setProperty("param_table", table)
        else:
            # 创建新的tab页
            page, table = viewer_instance._new_param_tab_like_default(pno_label)
            page.setProperty("param_table", table)

        # 保存到字典
        viewer_instance.dynamic_fastener_param_tabs[pno_label] = table

        # 渲染数据到表格
        _render_fastener_table_data(table, data, param_structures, dropdown_options, max_cols, viewer_instance)

        print(f"[DBG][fastener_render] 完成渲染 {pno_label}，共 {table.rowCount()} 行")

    # 设置+号tab页的复制逻辑 - 复制最后一个PNO tab而不是管口tab
    if hasattr(viewer_instance, '_add_single_table_tab_copy_only'):
        # 重写复制函数，让它复制设备法兰紧固件的PNO tab
        original_copy_func = viewer_instance._add_single_table_tab_copy_only

        def fastener_copy_func(source_tab_name, insert_after_index):
            # 获取最后一个PNO tab作为源
            pno_tabs = list(param_map.keys())
            if pno_tabs:
                last_pno = pno_tabs[-1]  # 使用最后一个PNO作为源
                print(f"[DBG][fastener_render] +号tab复制源: {last_pno}")
                # 调用原始的复制函数，但使用PNO tab作为源
                return original_copy_func(last_pno, insert_after_index)
            else:
                return original_copy_func(source_tab_name, insert_after_index)

        viewer_instance._add_single_table_tab_copy_only = fastener_copy_func


def _render_fastener_table_data(table, data, param_structures, dropdown_options, max_cols, viewer_instance=None):
    """渲染设备法兰紧固件数据到表格"""
    from PyQt5.QtWidgets import QTableWidgetItem, QComboBox, QLineEdit
    from PyQt5.QtCore import Qt

    # 定义辅助函数
    def ensure_editable_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt)
            table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
        it.setText(txt)
        return it

    def ensure_readonly_item(r, c, txt=""):
        it = table.item(r, c)
        if it is None:
            it = QTableWidgetItem(txt)
            table.setItem(r, c, it)
        it.setTextAlignment(Qt.AlignCenter)
        it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        it.setText(txt)
        it.setBackground(Qt.lightGray)
        return it

    # 定义ComboDelegate
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

    table.clear()
    table.setRowCount(0)
    table.setColumnCount(max_cols)
    table.verticalHeader().setVisible(False)
    table.horizontalHeader().setVisible(False)  # 隐藏表头
    table.setSelectionBehavior(QTableWidget.SelectItems)
    table.setSelectionMode(QTableWidget.ExtendedSelection)
    table.setEditTriggers(QAbstractItemView.SelectedClicked)  # 允许点击编辑

    # 设置表格样式，使其与管口表格一致
    table.setAlternatingRowColors(False)
    table.setStyleSheet("""
        QTableWidget {
            gridline-color: #d0d0d0;
            background-color: white;
        }
        QTableWidget::item {
            border: 1px solid #d0d0d0;
            padding: 4px;
        }
        QTableWidget::item:selected {
            background-color: #e3f2fd;
        }
    """)

    # 设置表格大小策略，确保表格可见
    from PyQt5.QtWidgets import QSizePolicy
    table.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    table.setMinimumSize(400, 200)  # 设置最小尺寸

    # 安装过滤器
    flt = ComboPopupEventFilter(table)
    table._popup_filter = flt
    table.viewport().installEventFilter(flt)

    # 创建数据映射 - 支持多列数据格式
    display_map = {}
    if data:
        for item in data:
            param_name = item.get('参数名称', '')
            param_value = item.get('参数值', '')

            # 检查是否是带数字后缀的参数名（如"元件类型1"、"元件类型2"）
            import re
            match = re.match(r'^(.*?)(\d+)$', param_name)
            if match:
                base_name, col_index = match.groups()
                col_index = int(col_index)

                # 如果是多列参数，创建字典结构
                if base_name not in display_map:
                    display_map[base_name] = {}
                display_map[base_name][col_index] = param_value
            else:
                # 单列参数
                display_map[param_name] = param_value
        # 清空后，数据库仍有记录但值可能为空，这里补默认值
        # 1) 元件名称
        if not display_map.get("元件名称"):
            display_map["元件名称"] = "设备法兰紧固件"
        # 2) 元件类型（两列）
        typemap = display_map.get("元件类型")
        if not isinstance(typemap, dict):
            typemap = {}
        if not typemap.get(1):
            typemap[1] = "螺柱"
        if not typemap.get(2):
            typemap[2] = "螺母"
        display_map["元件类型"] = typemap
        # 3) 表面处理工艺
        if not display_map.get("表面处理工艺"):
            display_map["表面处理工艺"] = "/"

        print(f"[DBG][fastener_render] 数据映射: {display_map}")
    else:
        print(f"[DBG][fastener_render] 没有数据需要渲染")
        # 如果没有数据，为每个参数设置默认值
        for param_name, structure, control_type, prefix in param_structures:
            if param_name == "元件名称":
                display_map[param_name] = "设备法兰紧固件"
            elif param_name == "元件所属":
                display_map[param_name] = ""  # 空值，让用户选择
            elif param_name == "表面处理工艺":
                display_map[param_name] = "/"  # 默认值
            elif param_name == "元件类型":
                display_map[param_name] = {1: "螺柱", 2: "螺母"}
            else:
                display_map[param_name] = ""  # 其他字段为空

    # 渲染参数
    for param_name, structure, control_type, prefix in param_structures:
        row = table.rowCount()
        table.insertRow(row)

        # 左侧名称列
        label_item = QTableWidgetItem(param_name)
        label_item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        table.setItem(row, 0, label_item)

        option_key = prefix or param_name
        options = dropdown_options.get(option_key, [])
        value = display_map.get(param_name, "")

        if structure == "2列":
            table.setSpan(row, 1, 1, 3)

            if control_type == "combo":
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                table.setItem(row, 1, item)

                # 特殊处理：只有元件名称设为只读
                if param_name == "元件名称":
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # 移除可编辑标志
                    item.setBackground(Qt.lightGray)

                if options:
                    table.setItemDelegateForRow(row, ComboDelegate(options, table))

            elif control_type == "text":
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                table.setItem(row, 1, item)

                # 特殊处理：元件名称设为只读
                if param_name == "元件名称":
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)  # 移除可编辑标志
                    item.setBackground(Qt.lightGray)

                # 表面处理工艺特殊处理
                if param_name == "表面处理工艺":
                    item.setText("/")  # 默认值
                    item.setVisible(False)  # 隐藏处理

        elif structure == "3列":
            # 3列结构：除"元件名称"外，始终显示两格（参数值1、参数值2），不合并，避免清空后看起来变成单列
            value_map = display_map.get(param_name, {})
            if not isinstance(value_map, dict):
                value_map = {}

            if param_name == "元件名称":
                # 元件名称只读，跨两列显示
                table.setSpan(row, 1, 1, 2)
                val = value_map.get(1, "") if value_map else display_map.get(param_name, "")
                display_val = str(val) if val and str(val) != "null" else ""
                ensure_readonly_item(row, 1, display_val)
            else:
                # 始终提供两个可编辑单元格
                for col in range(1, 3):
                    val = value_map.get(col, "")
                    display_val = str(val) if val and str(val) != "null" else ""
                    if param_name == "元件类型":
                        # 两列均只读，不允许用户单独编辑
                        ensure_readonly_item(row, col, display_val or ("螺柱" if col == 1 else "螺母"))
                    else:
                        ensure_editable_item(row, col, display_val)

            # 为3列结构安装委托 - 材料字段由联动逻辑处理，其他字段使用ComboDelegate
            if options and control_type == "combo":
                # 材料字段由材料联动逻辑处理，不安装ComboDelegate
                material_fields = ["材料类型", "材料牌号", "材料标准", "供货状态"]
                if param_name not in material_fields:
                    # "元件类型"固定，不安装下拉委托
                    if param_name != "元件类型":
                        table.setItemDelegateForRow(row, ComboDelegate(options, table))
                    print(f"[DBG][fastener_render] 为{param_name}安装下拉框委托，选项: {options}")
                else:
                    print(f"[DBG][fastener_render] {param_name}由材料联动逻辑处理，跳过ComboDelegate")

        elif structure == "4列":
            # 4列结构处理
            value_map = display_map.get(param_name, {})
            if not isinstance(value_map, dict):
                value_map = {}
            for col in range(1, 4):
                val = value_map.get(col, "")
                item = QTableWidgetItem(str(val))
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                table.setItem(row, col, item)

            if options:
                if control_type == "combo":
                    # 材料字段由材料联动逻辑处理，不安装ComboDelegate
                    material_fields = ["材料类型", "材料牌号", "材料标准", "供货状态"]
                    if param_name not in material_fields:
                        table.setItemDelegateForRow(row, ComboDelegate(options, table))
                        print(f"[DBG][fastener_render] 为{param_name}安装下拉框委托，选项: {options}")
                    else:
                        print(f"[DBG][fastener_render] {param_name}由材料联动逻辑处理，跳过ComboDelegate")

    # 表头自适应 - 参考管口的设置
    header = table.horizontalHeader()
    header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # 参数名称列自适应
    for col in range(1, max_cols):
        header.setSectionResizeMode(col, QHeaderView.Stretch)  # 其他列平均分配

    # 设置行高，使其与管口表格一致
    for row in range(table.rowCount()):
        table.setRowHeight(row, 30)  # 设置行高为30像素

    # 调试信息：确保表格正确设置
    print(f"[DBG][fastener_render] 表格设置完成: 行数={table.rowCount()}, 列数={table.columnCount()}")
    print(f"[DBG][fastener_render] 表格可见性: {table.isVisible()}, 大小={table.size()}")
    print(f"[DBG][fastener_render] 表格父控件: {table.parent()}")

    # 强制刷新表格显示
    table.update()
    table.repaint()

    # 安装材料字段联动逻辑 - 使用四联组识别方式，确保列间独立性
    try:
        from modules.cailiaodingyi.funcs.funcs_pdf_render import find_material_groups_fuzzy_strict
        from modules.cailiaodingyi.controllers.combo import MultiSelectDynamicOptionsDelegate

        # 使用四联组识别方式，确保每列有独立的材料联动
        groups, row2field, row2group = find_material_groups_fuzzy_strict(table)
        found_rows = sorted(row2field.keys())

        if found_rows:
            print(f"[DBG][fastener_render] 识别到材料四联组: {len(groups)} 组，涉及行: {found_rows}")

            # 确保可编辑 & 去掉 cellWidget
            for r in found_rows:
                for c in (1, 2):  # 只处理列1和列2
                    it = table.item(r, c)
                    if it is None:
                        it = QTableWidgetItem("")
                        it.setTextAlignment(Qt.AlignCenter)
                        table.setItem(r, c, it)
                    it.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable)
                    if table.cellWidget(r, c):
                        table.setCellWidget(r, c, None)

            # 安装动态代理（只对这些行）
            for r in found_rows:
                table.setItemDelegateForRow(r, None)
            dyn = MultiSelectDynamicOptionsDelegate(table, groups, row2field, row2group)
            for r in found_rows:
                table.setItemDelegateForRow(r, dyn)

            print(f"[DBG][fastener_render] 材料四联组联动逻辑安装完成")
        else:
            print(f"[DBG][fastener_render] 未识别到材料四联组，跳过材料联动逻辑")

    except Exception as e:
        print(f"[DBG][fastener_render] 材料字段联动逻辑安装失败: {e}")
        import traceback
        traceback.print_exc()

    # 添加事件处理逻辑 - 参考固定鞍座的实现
    def _on_item_changed(item: QTableWidgetItem):
        # 总闸
        if getattr(table, "_loading", False):
            return
        if item.column() == 0:  # 参数名称列不处理
            return

        r = item.row()
        pitem = table.item(r, 0)
        if not pitem:
            return

        pname = pitem.text().strip()
        val = (item.text() or "").strip()
        print(f"[设备法兰紧固件-参数修改] {pname}={val} (仅UI更新，未保存到数据库)")

    # 单击进入编辑
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

    print(f"[DBG][fastener_render] 事件处理逻辑安装完成")

