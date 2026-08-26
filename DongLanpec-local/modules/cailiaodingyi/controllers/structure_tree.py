# -*- coding: utf-8 -*-
"""元件定义 - 结构树：配置读取、对话框、写库；隐藏清空材料并删除附加参数行，再显示时从模板回填。"""

from typing import Dict, List, Optional, Set, Tuple

import pymysql
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from modules.cailiaodingyi.controllers.style import apply_dialog_style
from modules.cailiaodingyi.db_cnt import get_connection
from modules.cailiaodingyi.funcs.funcs_pdf_input import db_config_1, db_config_2


def _element_display_name(row: dict) -> str:
    return (row.get("零件名称") or row.get("元件名称") or "").strip()


def _is_yes(val) -> bool:
    if val is None:
        return False
    s = str(val).strip()
    return s in ("是", "1", "true", "True", "Y", "y")


def query_structure_tree_config(product_type: str, product_form: str) -> List[dict]:
    """从材料库读取结构树配置。"""
    if not product_type or not product_form:
        return []
    conn = get_connection(**db_config_2)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 元件名称, 是否显示, 是否必选
                FROM 结构树配置表
                WHERE 所属类型 = %s AND 所属形式 = %s
                """,
                (product_type, product_form),
            )
            return cur.fetchall() or []
    except pymysql.MySQLError as e:
        print(f"[结构树] 读取配置失败: {e}")
        return []
    finally:
        conn.close()


def config_maps_by_name(
    product_type: str, product_form: str
) -> Tuple[Dict[str, dict], Set[str], Set[str]]:
    """
    返回 (name->config, 配置中默认显示的元件名, 必选元件名)。
    """
    rows = query_structure_tree_config(product_type, product_form)
    by_name: Dict[str, dict] = {}
    default_visible_names: Set[str] = set()
    mandatory_names: Set[str] = set()
    for row in rows:
        name = (row.get("元件名称") or "").strip()
        if not name:
            continue
        by_name[name] = row
        if _is_yes(row.get("是否显示")):
            default_visible_names.add(name)
        if _is_yes(row.get("是否必选")):
            mandatory_names.add(name)
    return by_name, default_visible_names, mandatory_names


def build_initial_visible_and_mandatory(
    template_elements: List[dict], product_type: str, product_form: str
) -> Tuple[List, Set]:
    """
    首次进入：按配置表 + 模板元件列表得到初始 visible 元件ID 与 mandatory 元件ID。
    配置中无记录的模板元件默认不显示。
    """
    _, default_visible_names, mandatory_names = config_maps_by_name(product_type, product_form)
    visible_ids: List = []
    mandatory_ids: Set = set()

    for item in template_elements or []:
        eid = item.get("元件ID")
        if eid is None:
            continue
        name = _element_display_name(item)
        if name in default_visible_names:
            visible_ids.append(eid)
        if name in mandatory_names:
            mandatory_ids.add(eid)

    return visible_ids, mandatory_ids


def mandatory_ids_for_elements(
    all_elements: List[dict], product_type: str, product_form: str
) -> Set:
    _, _, mandatory_names = config_maps_by_name(product_type, product_form)
    ids: Set = set()
    for item in all_elements or []:
        name = _element_display_name(item)
        if name in mandatory_names:
            eid = item.get("元件ID")
            if eid is not None:
                ids.add(eid)
    return ids


def visible_ids_from_rows(all_elements: List[dict]) -> List:
    ids = []
    for item in all_elements or []:
        disp = item.get("是否显示")
        if disp is None or disp == "" or _is_yes(disp):
            eid = item.get("元件ID")
            if eid is not None:
                ids.append(eid)
    return ids


def filter_visible_elements(element_rows: List[dict]) -> List[dict]:
    return [r for r in (element_rows or []) if r.get("元件ID") in set(visible_ids_from_rows(element_rows))]


class StructureTreeDialog(QDialog):
    """双列表：左=不显示，右=显示；必选元件不可从右侧移除。"""

    def __init__(
        self,
        parent,
        all_elements: List[dict],
        visible_element_ids: List,
        mandatory_element_ids: Optional[Set] = None,
        title: str = "结构树",
    ):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.resize(720, 480)
        apply_dialog_style(self)
        self._mandatory: Set = set(mandatory_element_ids or [])
        self._result_visible_ids: Optional[List] = None

        id_to_row = {item["元件ID"]: item for item in all_elements if item.get("元件ID") is not None}
        visible_set = set(visible_element_ids or [])
        all_ids = [item["元件ID"] for item in all_elements if item.get("元件ID") is not None]

        self.setLayout(QVBoxLayout())
        hint = QLabel("左侧：不显示的元件；右侧：显示的元件。灰色项为固定显示，不可移除。")
        hint.setWordWrap(True)
        self.layout().addWidget(hint)

        lists_row = QHBoxLayout()
        left_col = QVBoxLayout()
        left_col.addWidget(QLabel("不显示"))
        self.list_hidden = QListWidget()
        self.list_hidden.setSelectionMode(QListWidget.ExtendedSelection)
        left_col.addWidget(self.list_hidden)

        btn_col = QVBoxLayout()
        btn_col.addStretch()
        self.btn_add = QPushButton("添加 >>")
        self.btn_remove = QPushButton("<< 移除")
        btn_col.addWidget(self.btn_add)
        btn_col.addWidget(self.btn_remove)
        btn_col.addStretch()

        right_col = QVBoxLayout()
        right_col.addWidget(QLabel("显示"))
        self.list_visible = QListWidget()
        self.list_visible.setSelectionMode(QListWidget.ExtendedSelection)
        right_col.addWidget(self.list_visible)

        lists_row.addLayout(left_col, 1)
        lists_row.addLayout(btn_col)
        lists_row.addLayout(right_col, 1)
        self.layout().addLayout(lists_row)

        bbox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        ok_btn = bbox.button(QDialogButtonBox.Ok)
        cancel_btn = bbox.button(QDialogButtonBox.Cancel)
        if ok_btn:
            ok_btn.setText("确定")
        if cancel_btn:
            cancel_btn.setText("取消")
        bbox.accepted.connect(self._on_accept)
        bbox.rejected.connect(self.reject)
        self.layout().addWidget(bbox)

        for eid in all_ids:
            row = id_to_row.get(eid, {})
            name = _element_display_name(row) or str(eid)
            mandatory = eid in self._mandatory
            target = self.list_visible if eid in visible_set else self.list_hidden
            self._append_item(target, eid, name, mandatory)

        self.btn_add.clicked.connect(self._move_to_visible)
        self.btn_remove.clicked.connect(self._move_to_hidden)

    def _append_item(self, list_widget: QListWidget, element_id, name: str, mandatory: bool):
        text = f"{name} *" if mandatory and list_widget is self.list_visible else name
        item = QListWidgetItem(text)
        item.setData(Qt.UserRole, element_id)
        if mandatory and list_widget is self.list_visible:
            item.setForeground(QColor("#888888"))
            item.setToolTip("固定显示，不可移除")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable)
        list_widget.addItem(item)

    def _move_to_visible(self):
        for item in self.list_hidden.selectedItems():
            eid = item.data(Qt.UserRole)
            name = item.text().rstrip(" *").strip()
            row = self.list_hidden.row(item)
            self.list_hidden.takeItem(row)
            mandatory = eid in self._mandatory
            self._append_item(self.list_visible, eid, name, mandatory)

    def _move_to_hidden(self):
        for item in self.list_visible.selectedItems():
            eid = item.data(Qt.UserRole)
            if eid in self._mandatory:
                continue
            name = item.text().rstrip(" *").strip()
            row = self.list_visible.row(item)
            self.list_visible.takeItem(row)
            self._append_item(self.list_hidden, eid, name, False)

    def _on_accept(self):
        ids = []
        for i in range(self.list_visible.count()):
            ids.append(self.list_visible.item(i).data(Qt.UserRole))
        self._result_visible_ids = ids
        self.accept()

    def get_visible_element_ids(self) -> Optional[List]:
        return self._result_visible_ids


def show_structure_tree_dialog(
    parent,
    all_elements: List[dict],
    visible_element_ids: List,
    mandatory_element_ids: Optional[Set] = None,
    title: str = "结构树",
) -> Optional[List]:
    """
    弹出结构树；确认返回 visible 元件ID 列表，取消返回 None。
    """
    dlg = StructureTreeDialog(
        parent,
        all_elements,
        visible_element_ids,
        mandatory_element_ids,
        title=title,
    )
    if dlg.exec_() != QDialog.Accepted:
        return None
    return dlg.get_visible_element_ids()


def clear_element_product_data(product_id: str, element_id) -> None:
    """
    隐藏元件：清空材料表业务字段并标记是否显示=否；
    删除该元件在「元件附加参数表」中的全部行（再选中时从模板回填）；
    合并表仍清空参数值（保留行结构，保留「元件名称」）。
    """
    conn = get_connection(**db_config_1)
    elem_name = ""
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 元件名称 FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件ID = %s
                LIMIT 1
                """,
                (product_id, element_id),
            )
            row = cur.fetchone()
            if row:
                elem_name = str((row.get("元件名称") if isinstance(row, dict) else row[0]) or "").strip()

            cur.execute(
                """
                UPDATE 产品设计活动表_元件材料表
                SET 材料类型 = '', 材料牌号 = '', 材料标准 = '',
                    供货状态 = '', 有无覆层 = '', 定义状态 = '未定义',
                    是否显示 = '否'
                WHERE 产品ID = %s AND 元件ID = %s
                """,
                (product_id, element_id),
            )
            # 未选元件：直接删除附加参数行（不再仅清空参数值）
            cur.execute(
                """
                DELETE FROM 产品设计活动表_元件附加参数表
                WHERE 产品ID = %s AND 元件ID = %s
                """,
                (product_id, element_id),
            )
            # 合并表：其它参数清空，明确保留「元件名称」
            cur.execute(
                """
                UPDATE 产品设计活动表_元件附加参数合并表
                SET 参数值 = ''
                WHERE 产品ID = %s AND 元件ID = %s
                  AND 参数名称 <> '元件名称'
                """,
                (product_id, element_id),
            )
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"[结构树] 清空元件数据失败 product={product_id} element={element_id}: {e}")
    finally:
        conn.close()

    # 保温装置：清空后若元件名称为空，按管口附件表回填（不回填材料等模板参数）
    if elem_name == "保温装置":
        try:
            from modules.cailiaodingyi.controllers.datamanager import (
                sync_insulation_merged_component_names_from_attachment,
            )
            sync_insulation_merged_component_names_from_attachment(product_id, element_id)
        except Exception as e:
            print(f"[结构树][保温装置] 清空后回填元件名称失败: {e}")


def _get_element_visibility_flag(product_id: str, element_id) -> Optional[str]:
    """返回 '是' / '否' / None（无行或空值）。"""
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 是否显示 FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件ID = %s
                LIMIT 1
                """,
                (product_id, element_id),
            )
            row = cur.fetchone()
            if not row:
                return None
            flag = str((row.get("是否显示") if isinstance(row, dict) else row[0]) or "").strip()
            if _is_yes(flag):
                return "是"
            if flag in ("否", "0", "false", "False", "N", "n"):
                return "否"
            return None
    except pymysql.MySQLError:
        return None
    finally:
        conn.close()


def _element_para_row_count(product_id: str, element_id) -> int:
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT COUNT(*) AS cnt FROM 产品设计活动表_元件附加参数表
                WHERE 产品ID = %s AND 元件ID = %s
                """,
                (product_id, element_id),
            )
            row = cur.fetchone()
            if not row:
                return 0
            return int(row.get("cnt") if isinstance(row, dict) else row[0] or 0)
    except pymysql.MySQLError:
        return 0
    finally:
        conn.close()


def _needs_element_para_restore(product_id: str, element_id) -> bool:
    """
    需要从模板回填附加参数：此前隐藏（是否显示=否），或附加参数表已无行。
    已显示且仍有参数行时不回填，避免覆盖用户已改数据。
    """
    if _get_element_visibility_flag(product_id, element_id) == "否":
        return True
    return _element_para_row_count(product_id, element_id) <= 0


def _resolve_product_template_name(product_id: str, all_elements: Optional[List[dict]] = None) -> str:
    for item in all_elements or []:
        name = (item.get("模板名称") or "").strip()
        if name:
            return name
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 模板名称 FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s
                LIMIT 1
                """,
                (product_id,),
            )
            row = cur.fetchone()
            if row:
                return str((row.get("模板名称") if isinstance(row, dict) else row[0]) or "").strip() or "None"
    except pymysql.MySQLError as e:
        print(f"[结构树] 读取模板名称失败: {e}")
    finally:
        conn.close()
    return "None"


def restore_element_para_from_template(
    product_id: str,
    element_id,
    template_id=None,
    template_name: Optional[str] = None,
) -> None:
    """
    再次选中（此前隐藏）时：从材料库模板读出该元件有哪些附加参数行并 INSERT；
    参数值一律为空（仅「元件名称」写标准名）。
    未选中时已删除附加参数行，此处不再重复 DELETE。
    """
    if not product_id or element_id is None:
        return

    from modules.cailiaodingyi.funcs.funcs_pdf_input import (
        get_template_id_by_name,
        query_template_element_para_data,
    )

    tpl_name = (template_name or "").strip() or "None"
    if template_id is None:
        template_id = get_template_id_by_name(tpl_name)
    if template_id is None:
        print(f"[结构树] 无法解析模板ID，跳过附加参数回填 product={product_id} element={element_id} template={tpl_name}")
        return

    template_rows = query_template_element_para_data(template_id) or []
    eid_str = str(element_id).strip()
    element_rows = [
        r for r in template_rows
        if str(r.get("元件ID") or "").strip() == eid_str
    ]
    if not element_rows:
        print(f"[结构树] 模板无附加参数可回填 product={product_id} element={element_id} template_id={template_id}")
        return

    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            for item in element_rows:
                param_name = str(item.get("参数名称", "") or "").strip()
                element_name = str(item.get("元件名称", "") or "").strip()
                # 只恢复参数行结构；业务参数值清空。元件名称与旧清空逻辑一致予以保留。
                if param_name == "元件名称":
                    param_value = element_name
                else:
                    param_value = ""
                para_id = item.get("元件附加参数ID")
                if para_id is None:
                    continue
                cur.execute(
                    """
                    INSERT INTO 产品设计活动表_元件附加参数表
                    (元件附加参数ID, 产品ID, 元件ID, 元件名称, 参数名称, 参数值, 参数单位)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        para_id,
                        product_id,
                        item.get("元件ID"),
                        item.get("元件名称"),
                        item.get("参数名称"),
                        param_value,
                        item.get("参数单位"),
                    ),
                )
        conn.commit()
        print(f"[结构树] 已从模板回填附加参数结构(参数值清空) product={product_id} element={element_id} rows={len(element_rows)}")
    except pymysql.MySQLError as e:
        print(f"[结构树] 从模板回填附加参数失败 product={product_id} element={element_id}: {e}")
    finally:
        conn.close()


def ensure_element_name_param(product_id: str, element_id, element_name: str) -> None:
    """显示元件时，若附加参数中「元件名称」为空则写回标准名。"""
    name = (element_name or "").strip()
    if not name:
        return
    # 保温装置合并表「元件名称」是子零件多选 JSON，不能写成父级名
    skip_merged = name == "保温装置"
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            tables = ["产品设计活动表_元件附加参数表"]
            if not skip_merged:
                tables.append("产品设计活动表_元件附加参数合并表")
            for table in tables:
                cur.execute(
                    f"""
                    UPDATE {table}
                    SET 参数值 = %s
                    WHERE 产品ID = %s AND 元件ID = %s
                      AND 参数名称 = '元件名称'
                      AND (参数值 IS NULL OR TRIM(参数值) = '')
                    """,
                    (name, product_id, element_id),
                )
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"[结构树] 恢复元件名称参数失败 product={product_id} element={element_id}: {e}")
    finally:
        conn.close()


def set_element_visible(product_id: str, element_id, visible: bool) -> None:
    flag = "是" if visible else "否"
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE 产品设计活动表_元件材料表
                SET 是否显示 = %s
                WHERE 产品ID = %s AND 元件ID = %s
                """,
                (flag, product_id, element_id),
            )
        conn.commit()
    except pymysql.MySQLError as e:
        print(f"[结构树] 更新是否显示失败: {e}")
    finally:
        conn.close()


def fetch_hidden_element_names(product_id: str) -> Set[str]:
    """读取切换模板前用户设为不显示的元件名称（按元件名称匹配，跨模板保留）。"""
    if not product_id:
        return set()
    conn = get_connection(**db_config_1)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 元件名称
                FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 是否显示 = '否'
                """,
                (product_id,),
            )
            rows = cur.fetchall() or []
            return {
                (r.get("元件名称") or "").strip()
                for r in rows
                if (r.get("元件名称") or "").strip()
            }
    except pymysql.MySQLError as e:
        print(f"[结构树] 读取隐藏元件失败: {e}")
        return set()
    finally:
        conn.close()


def restore_structure_tree_visibility_after_template_switch(
    product_id: str,
    template_elements: List[dict],
    hidden_element_names: Set[str],
) -> None:
    """
    切换模板后：此前不显示的元件保持隐藏，并清空其模板数据（不做模板替换）。
    新模板中同名的元件仍按 hidden_element_names 处理。
    """
    if not product_id or not template_elements:
        return
    hidden = hidden_element_names or set()
    visible_ids: List = []
    all_for_apply: List[dict] = []
    for item in template_elements:
        eid = item.get("元件ID")
        if eid is None:
            continue
        name = _element_display_name(item)
        row = dict(item)
        if name:
            row.setdefault("零件名称", name)
        all_for_apply.append(row)
        if name not in hidden:
            visible_ids.append(eid)
    if hidden:
        apply_structure_tree_selection(product_id, all_for_apply, visible_ids)
        print(f"[结构树] 切换模板后保留隐藏元件: {sorted(hidden)}")


def apply_structure_tree_selection(
    product_id: str,
    all_elements: List[dict],
    visible_element_ids: List,
) -> None:
    """
    按用户选择写是否显示：
    - 隐藏：清空材料表字段 + 删除元件附加参数表行 + 清空合并表参数值；
    - 显示：标记是否显示=是；若此前隐藏或附加参数已无行，则从模板恢复参数行结构（参数值清空，仅保留元件名称）。
    """
    visible_set = set(visible_element_ids or [])
    template_name = _resolve_product_template_name(product_id, all_elements)
    template_id = None
    try:
        from modules.cailiaodingyi.funcs.funcs_pdf_input import get_template_id_by_name
        template_id = get_template_id_by_name(template_name)
    except Exception as e:
        print(f"[结构树] 解析模板ID失败 template={template_name}: {e}")

    for item in all_elements or []:
        eid = item.get("元件ID")
        if eid is None:
            continue
        if eid in visible_set:
            # 必须在改「是否显示」之前判断，才能识别「再次选中」
            need_restore = _needs_element_para_restore(product_id, eid)
            item_tpl_id = item.get("模板ID")
            set_element_visible(product_id, eid, True)
            if need_restore:
                restore_element_para_from_template(
                    product_id,
                    eid,
                    template_id=item_tpl_id if item_tpl_id is not None else template_id,
                    template_name=(item.get("模板名称") or template_name),
                )
            ensure_element_name_param(product_id, eid, _element_display_name(item))
        else:
            clear_element_product_data(product_id, eid)
    # 保温装置：无附件触发时不应残留合并表结构（与管口附件一致）
    try:
        from modules.cailiaodingyi.controllers.datamanager import (
            reconcile_insulation_merged_para_with_attachment,
        )
        reconcile_insulation_merged_para_with_attachment(product_id)
    except Exception as e:
        print(f"[结构树][保温装置] 合并表对齐失败: {e}")
