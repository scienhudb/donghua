# modules/cailiaodingyi/funcs/check_dianpian.py
"""
垫片校验模块 - 负责垫片元件的公称压力PN计算、尺寸推荐及参数校验

主要功能：
1. 查询产品的所有垫片及其配套法兰信息
2. 根据材料牌号、设计温度、设计压力计算推荐的公称压力PN
3. 校验垫片尺寸（公称直径、温度）是否在允许范围内
4. 自动更新数据库中的垫片参数（PN、内外径等）
5. 支持用户手动输入与程序推荐的智能切换
"""

# 导入数据库连接工具（从项目内部模块）
from modules.cailiaodingyi.db_cnt import get_connection
# 导入PyQt5的消息框控件，用于弹出提示
from PyQt5.QtWidgets import QMessageBox
from PyQt5 import QtWidgets
# 导入相关的工具函数：调试标志、查询元件参数、更新元件数据
from modules.cailiaodingyi.funcs.funcs_pdf_change import (
    DEBUG_VERBOSE_DEFINE_UI,  # 调试输出开关（布尔值）
    query_element_name_param_value,  # 根据产品ID、元件名称、参数名查询参数值
    update_element_name_data,  # 更新元件参数数据到数据库
)

# ============================================================================
# PN（公称压力）用户输入缓存管理
# 用于跟踪哪些垫片的PN值是用户手动输入的，避免被程序覆盖
# ============================================================================
# 全局字典：键为 (product_id, gasket_id) 的字符串元组，值为 True 表示用户手动输入过
PN_USER_INPUT_CACHE = {}


def mark_pn_user_input(product_id, gasket_id):
    """
    标记指定垫片的PN为用户手动输入

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
    """
    try:
        # 将产品ID和垫片ID转为字符串后拼接为键，存入缓存字典
        PN_USER_INPUT_CACHE[(str(product_id or ''), str(gasket_id or ''))] = True
    except Exception:
        # 任何异常都静默忽略，保证函数不会崩溃
        pass


def clear_pn_user_input(product_id, gasket_id):
    """
    清除指定垫片的PN用户输入标记

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
    """
    try:
        # 从缓存中删除对应的键（若存在）
        PN_USER_INPUT_CACHE.pop((str(product_id or ''), str(gasket_id or '')), None)
    except Exception:
        pass


def is_pn_user_input(product_id, gasket_id):
    """
    检查指定垫片的PN是否为用户手动输入

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID

    返回:
        bool: True表示用户手动输入，False表示程序推荐
    """
    try:
        # 从缓存字典中获取布尔值，若键不存在则返回 False
        return bool(PN_USER_INPUT_CACHE.get((str(product_id or ''), str(gasket_id or '')), False))
    except Exception:
        return False


def _norm_out(v):
    """
    标准化输出值，将None或空值转换为"程序推荐"

    参数:
        v: 任意值（可能是 None、数字、字符串等）

    返回:
        str: 标准化后的字符串，空值返回"程序推荐"
    """
    if v is None:
        return "程序推荐"
    s = str(v).strip()
    return s if s else "程序推荐"


# ============================================================================
# DIM（尺寸参数）用户输入缓存管理
# 用于跟踪哪些垫片的尺寸参数（如D2n/D1n/d1）是用户手动输入的
# ============================================================================
# 全局字典：键为 (product_id, gasket_id, param_name) 的字符串元组，值为 True
DIM_USER_INPUT_CACHE = {}


def mark_dim_user_input(product_id, gasket_id, param_name):
    """
    标记指定垫片的某个尺寸参数为用户手动输入

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
        param_name: 参数名称（如"垫片名义外径D2n"）
    """
    try:
        # 三个字段拼接为键，存入缓存
        DIM_USER_INPUT_CACHE[(str(product_id or ''), str(gasket_id or ''), str(param_name or ''))] = True
    except Exception:
        pass


def clear_dim_user_input(product_id, gasket_id, param_name):
    """
    清除指定垫片某个尺寸参数的用户输入标记

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
        param_name: 参数名称
    """
    try:
        DIM_USER_INPUT_CACHE.pop((str(product_id or ''), str(gasket_id or ''), str(param_name or '')), None)
    except Exception:
        pass


def is_dim_user_input_cached(product_id, gasket_id, param_name):
    """
    检查指定垫片的某个尺寸参数是否在缓存中标记为用户输入

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
        param_name: 参数名称

    返回:
        bool: True表示用户手动输入
    """
    try:
        return bool(
            DIM_USER_INPUT_CACHE.get((str(product_id or ''), str(gasket_id or ''), str(param_name or '')), False))
    except Exception:
        return False


def is_dim_user_input(product_id, element_name, param_name):
    """
    检查指定元件的某个尺寸参数是否为用户输入（当前固定返回False）
    注：此函数是旧接口，目前始终返回 False，可能保留用于未来扩展

    参数:
        product_id: 产品ID
        element_name: 元件名称
        param_name: 参数名称

    返回:
        bool: 固定返回False
    """
    return False


def is_dim_user_input_any(product_id, gasket_id, element_name, param_name):
    """
    综合检查尺寸参数是否为用户输入（检查缓存或其他来源）

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
        element_name: 元件名称
        param_name: 参数名称

    返回:
        bool: 任一检查返回True则为True
    """
    try:
        # 优先检查缓存中的标记，若没有则调用 is_dim_user_input（当前总是 False）
        return is_dim_user_input_cached(product_id, gasket_id, param_name) or is_dim_user_input(product_id,
                                                                                                element_name,
                                                                                                param_name)
    except Exception:
        return False


def is_dim_weak(product_id, element_name, param_name):
    """
    检查尺寸参数是否为弱值（空值或"程序推荐"）
    弱值意味着可以安全地被程序推荐值覆盖

    参数:
        product_id: 产品ID
        element_name: 元件名称
        param_name: 参数名称

    返回:
        bool: True表示参数值为空或程序推荐，可以被覆盖
    """
    try:
        # 查询当前参数值
        val = query_element_name_param_value(product_id, element_name, param_name)
        s = str(val).strip() if val is not None else ""
        # 如果值为空字符串或"程序推荐"，则认为是弱值
        return s == "" or s == "程序推荐"
    except Exception:
        # 查询出错时也认为是弱值，允许覆盖
        return True


# ============================================================================
# 数据库配置
# ============================================================================
# 产品设计活动库的连接配置（存放产品和元件数据）
db_config1 = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "产品设计活动库"
}

# 材料库的连接配置（存放材料牌号、压力等级表等基础数据）
db_config2 = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "材料库"
}


def _normalize_forms(forms_text):
    """
    标准化产品型式字符串，转换为大写并分割为列表

    产品型式示例： "AEU,BEU" 或 "AEU，BEU"

    参数:
        forms_text: 产品型式文本（可能包含多个型式，用逗号分隔）

    返回:
        list: 标准化后的型式列表，如 ["AEU", "BEU"]
    """
    s = str(forms_text or "").strip().upper().replace("，", ",")
    # 按逗号分割，去除每个元素的首尾空格，过滤掉空字符串
    return [x.strip() for x in s.split(",") if x.strip()]


def _get_product_form(product_id):
    """
    从数据库查询产品的型式（如AEU、BEU等）

    参数:
        product_id: 产品ID

    返回:
        str: 产品型式，大写字符串；未找到返回空字符串
    """
    conn = get_connection(**db_config1)
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT 产品型式
                FROM 产品设计活动表
                WHERE 产品ID = %s
                LIMIT 1
                """,
                (product_id,)
            )
            row = cursor.fetchone()
            # 如果查到数据且字段存在，则取出去除空格转大写，否则返回空字符串
            return (row.get("产品型式") or "").strip().upper() if row else ""
    finally:
        conn.close()


def _filter_mapping_rows_by_form(rows, product_form):
    """
    根据产品型式过滤垫片配套法兰映射表的行

    优先返回匹配当前产品型式的行，如果没有匹配则返回通用行（型式为空或包含"ALL"）

    参数:
        rows: 映射表行列表（每个元素是一个dict，包含"产品型式"字段）
        product_form: 当前产品型式（大写字符串）

    返回:
        list: 过滤后的行列表
    """
    preferred = []  # 存储匹配当前型式的行
    fallback = []  # 存储通用行（无型式限制或包含"ALL"）
    for r in rows or []:
        # 获取该行支持的产品型式列表（标准化后的列表）
        tokens = _normalize_forms(r.get("产品型式"))
        # 如果当前产品型式存在于该行的支持列表中，则加入优先组
        if product_form and product_form in tokens:
            preferred.append(r)
        # 如果该行没有限定型式（空列表）或包含"ALL"，则加入后备组
        elif (not tokens) or ("ALL" in tokens):
            fallback.append(r)
    # 优先返回匹配的行，若无则返回通用行
    return preferred if preferred else fallback


def get_gasket_elements(product_id):
    """
    查询指定产品ID的所有垫片及其配套法兰明细

    执行流程：
    STEP1-2: 查询产品中所有垫片元件及其名称
    STEP3-5: 查询每个垫片的配套法兰、法兰元件ID、法兰材料牌号
    STEP6: 查询产品的设计数据（压力、温度、公称直径）

    参数:
        product_id: 产品ID

    返回:
        list: 垫片配套法兰明细列表，每个元素包含：
            - 产品ID, 垫片名称, 垫片元件ID, 垫片管壳程
            - 配套法兰名称, 法兰元件ID, 法兰管壳程, 法兰材料牌号
            - 管程/壳程设计压力、设计温度、公称直径
    """
    # === STEP1 & STEP2: 查垫片元件 ===
    # 先连接产品设计活动库
    conn = get_connection(**db_config1)
    gasket_ids = []  # 存储所有垫片的元件ID
    gasket_names = {}  # 字典：元件ID -> 垫片名称
    try:
        with conn.cursor() as cursor:
            # 查询产品中所有名称包含"垫片"的元件ID
            cursor.execute("""
                SELECT 元件ID
                FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件名称 LIKE %s
            """, (product_id, "%垫片%"))
            rows = cursor.fetchall()
            gasket_ids = [row["元件ID"] for row in rows]

            # 获取每个垫片的详细名称（从元件附加参数表中查询"元件名称"参数）
            for eid in gasket_ids:
                cursor.execute("""
                    SELECT 元件名称
                    FROM 产品设计活动表_元件附加参数表
                    WHERE 产品ID = %s AND 元件ID = %s
                    LIMIT 1
                """, (product_id, eid))
                row = cursor.fetchone()
                if row:
                    gasket_names[eid] = row["元件名称"]
    finally:
        conn.close()

    # 如果没有找到任何垫片，直接返回空列表
    if not gasket_ids:
        return []

    # 获取产品型式，用于后续过滤映射表
    product_form = _get_product_form(product_id)

    # === STEP3-5: 查配套法兰 + 法兰元件ID + 材料牌号 ===
    # 连接材料库，查询垫片配套法兰映射表
    result = []  # 最终返回的结果列表
    conn2 = get_connection(**db_config2)
    try:
        with conn2.cursor() as cursor2:
            # 遍历每个垫片
            for gid, gname in gasket_names.items():
                # 从材料库查询该垫片名称对应的配套法兰映射记录
                cursor2.execute("""
                    SELECT *
                    FROM 垫片配套法兰映射表
                    WHERE 垫片名称 = %s
                """, (gname,))
                rows = cursor2.fetchall() or []
                # 根据产品型式过滤映射表（优先匹配当前产品型式）
                rows = _filter_mapping_rows_by_form(rows, product_form)

                # 对每条映射记录，查找对应的法兰元件ID和材料牌号
                for r in rows:
                    flange_name = r.get("配套法兰") or r.get("法兰名称")
                    gasket_course = r.get("垫片管壳程") if "垫片管壳程" in r else None
                    flange_course = r.get("法兰管壳程") if "法兰管壳程" in r else None

                    # === STEP4: 查配套法兰元件ID ===
                    # 重新连接产品设计活动库
                    conn3 = get_connection(**db_config1)
                    try:
                        with conn3.cursor() as cursor3:
                            # 在产品中查找该法兰名称对应的元件ID（可能有多个同名，但实际应该唯一）
                            cursor3.execute("""
                                SELECT 元件ID
                                FROM 产品设计活动表_元件材料表
                                WHERE 产品ID = %s AND 元件名称 = %s
                            """, (product_id, flange_name))
                            flange_rows = cursor3.fetchall()
                            flange_ids = [fr["元件ID"] for fr in flange_rows]

                            # 对每个法兰元件ID，查询其材料牌号
                            for fid in flange_ids:
                                # === STEP5: 查法兰材料牌号 ===
                                cursor3.execute("""
                                    SELECT 参数值
                                    FROM 产品设计活动表_元件附加参数表
                                    WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '材料牌号'
                                """, (product_id, fid))
                                mrows = cursor3.fetchall()
                                # 收集所有材料牌号值（一个法兰可能有多个牌号？一般只有一个）
                                mvals = [mr["参数值"] for mr in mrows if mr.get("参数值")]

                                # 暂存结果，等待STEP6添加设计数据后统一返回
                                result.append({
                                    "产品ID": product_id,
                                    "垫片名称": gname,
                                    "垫片元件ID": gid,
                                    "垫片管壳程": gasket_course,
                                    "配套法兰名称": flange_name,
                                    "法兰元件ID": fid,
                                    "法兰管壳程": flange_course,
                                    "法兰材料牌号": mvals
                                })
                    finally:
                        conn3.close()
    finally:
        conn2.close()

    # === STEP6: 查设计数据表（产品的设计压力、温度、公称直径） ===
    design_data = {
        "管程设计压力": None,
        "壳程设计压力": None,
        "管程设计温度": None,
        "壳程设计温度": None,
        "管程公称直径": None,
        "壳程公称直径": None,
    }
    conn4 = get_connection(**db_config1)
    try:
        with conn4.cursor() as cursor4:
            # 查询产品的设计压力、设计温度、公称直径（管程和壳程数值）
            cursor4.execute("""
                SELECT 参数名称, 管程数值, 壳程数值
                FROM 产品设计活动表_设计数据表
                WHERE 产品ID = %s
                  AND 参数名称 IN ('设计压力*', '设计温度（最高）*', '公称直径*')
            """, (product_id,))
            rows = cursor4.fetchall()

            # 将查询结果填充到 design_data 字典
            for r in rows:
                pname = r["参数名称"]
                if pname == "设计压力*":
                    design_data["管程设计压力"] = r.get("管程数值")
                    design_data["壳程设计压力"] = r.get("壳程数值")
                elif pname == "设计温度（最高）*":
                    design_data["管程设计温度"] = r.get("管程数值")
                    design_data["壳程设计温度"] = r.get("壳程数值")
                elif pname == "公称直径*":
                    design_data["管程公称直径"] = r.get("管程数值")
                    design_data["壳程公称直径"] = r.get("壳程数值")
    finally:
        conn4.close()

    # 把设计数据加到每一条记录里
    for item in result:
        item.update(design_data)
    return result


def clear_all_pn_user_input_for_product(product_id):
    """
    清除产品所有垫片的PN用户输入标记（仅针对当前值为空或"程序推荐"的垫片）

    参数:
        product_id: 产品ID
    """
    # 获取该产品所有垫片及其配套法兰信息
    items = get_gasket_elements(product_id)
    ids = set()
    # 收集所有唯一的垫片元件ID
    for it in items:
        gid = it.get("垫片元件ID")
        if gid:
            ids.add(gid)
    try:
        conn = get_connection(**db_config1)
        with conn.cursor() as cursor:
            for gid in ids:
                try:
                    # 查询当前PN值
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gid)
                    )
                    r0 = cursor.fetchone()
                    # 兼容处理返回行可能是字典或元组的情况
                    cur_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                    cur_text = str(cur_val).strip() if cur_val is not None else ""
                    # 仅清除空值或程序推荐的垫片，避免覆盖用户已手动输入的有效值
                    if cur_text == "" or cur_text == "程序推荐":
                        clear_pn_user_input(product_id, gid)
                except Exception:
                    pass
    finally:
        try:
            conn.close()
        except Exception:
            pass


def force_recompute_and_update_pn(product_id):
    """
    强制重新计算并更新产品所有垫片的公称压力PN及尺寸参数

    处理逻辑：
    1. 遍历所有垫片，检查是否为非标垫片
    2. 对于非用户手动输入的PN，调用compute_pn_for_gasket重新计算
    3. 更新数据库中的PN值，并清除用户输入标记
    4. 根据新的PN值重新计算垫片尺寸（D2n/D1n/d1）
    5. 统一提示所有非标垫片

    参数:
        product_id: 产品ID
    """
    # 延迟导入，避免循环依赖（funcs_pdf_change 中可能引用本模块）
    from modules.cailiaodingyi.funcs.funcs_pdf_change import compute_pn_for_gasket
    items = get_gasket_elements(product_id)
    groups = {}
    # 收集唯一的垫片ID和名称
    for it in items:
        gid = it.get("垫片元件ID")
        gname = (it.get("垫片名称") or "").strip()
        if gid:
            groups[(gid, gname)] = True
    if not groups:
        return

    conn = get_connection(**db_config1)
    nonstd_names = []  # 收集非标垫片名称，统一提示
    try:
        with conn.cursor() as cursor:
            for gid, gname in groups.keys():
                current_pn_val = None
                try:
                    # 查询当前PN值
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gid)
                    )
                    r0 = cursor.fetchone()
                    if r0:
                        current_pn_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                except Exception:
                    current_pn_val = None

                cur_text = str(current_pn_val).strip() if current_pn_val is not None else ""
                is_user_manual = is_pn_user_input(product_id, gid)

                # 如果用户手动输入且不是空值或程序推荐，则保留不覆盖
                if is_user_manual and (cur_text != "" and cur_text != "程序推荐"):
                    pass
                else:
                    # 重新计算PN值
                    try:
                        pn_inline = compute_pn_for_gasket(product_id, gname or "")
                    except Exception:
                        pn_inline = None
                    val_to_write = "程序推荐" if pn_inline is None else str(pn_inline)

                    # 更新数据库中的PN值
                    try:
                        cursor.execute(
                            """
                            UPDATE 产品设计活动表_元件附加参数表
                            SET 参数值=%s
                            WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                            """,
                            (val_to_write, product_id, gid)
                        )
                        conn.commit()
                    except Exception:
                        continue

                    # 清除用户输入标记
                    try:
                        clear_pn_user_input(product_id, gid)
                    except Exception:
                        pass

                # 计算并更新垫片尺寸（D2n/D1n/d1）
                try:
                    from modules.cailiaodingyi.funcs.funcs_pdf_change import resolve_gasket_dimensions, \
                        query_element_name_param_value
                    # 查询垫片标准
                    gasket_standard = query_element_name_param_value(product_id, gname, "垫片标准") or ""
                    if str(gasket_standard).strip() == "非标垫片":
                        # 收集非标垫片，后续统一提示
                        nonstd_names.append(gname)
                        continue
                    gasket_type = query_element_name_param_value(product_id, gname, "垫片型式") or query_element_name_param_value(product_id, gname, "垫片类型") or ""
                    spec = resolve_gasket_dimensions(product_id, gname, gasket_standard, gasket_type, pn=(cur_text if (is_user_manual and (cur_text != "" and cur_text != "程序推荐")) else str(val_to_write)))
                    try:
                        d_val = spec.get("外直径D")
                        d_in = spec.get("内直径d")
                        d1 = spec.get("环内径d1")
                        # 更新环内径、名义外径、名义内径（使用标准化输出函数）
                        update_element_name_data(product_id, gname, "环内径d1", _norm_out(d1))
                        update_element_name_data(product_id, gname, "垫片名义外径D2n", _norm_out(d_val))
                        update_element_name_data(product_id, gname, "垫片名义内径D1n", _norm_out(d_in))
                        if DEBUG_VERBOSE_DEFINE_UI:
                            print(
                                f"[条件保存后][DB] 已更新产品{product_id}, 垫片ID={gid}, D2n/D1n/d1={_norm_out(d_val)}/{_norm_out(d_in)}/{_norm_out(d1)}")
                    except Exception as e:
                        print(f"[条件保存后][DB] 更新D2n/D1n/d1失败: {e}")
                except Exception as e:
                    print(f"[条件保存后] 计算并更新垫片尺寸失败: {e}")

        # 统一弹窗提示所有非标垫片
        if nonstd_names:
            try:
                parent = QtWidgets.QApplication.activeWindow()
                msg = f"{'、'.join(nonstd_names)}为非标垫片，无法计算内外径！"
                box = QMessageBox(QMessageBox.Information, "提示", msg, QMessageBox.NoButton, parent)
                ok = box.addButton("确认", QMessageBox.YesRole)
                box.setDefaultButton(ok)
                box.exec_()
            except Exception:
                pass
    finally:
        conn.close()


def check_gasket_params(self):
    """
    主校验函数：对产品的所有垫片进行参数校验

    执行流程：
    1. 获取产品所有垫片数据
    2. 根据垫片名称匹配对应的校验规则
    3. 执行校验，收集警告信息
    4. 汇总结果显示在界面line_tip控件上
    5. 对同一垫片的多个法兰进行PN聚合（取最大值或按优先级选择）
    6. 更新数据库中的PN值和垫片尺寸

    参数:
        self: 界面对象，需包含last_confirmed_product_id属性和line_tip控件
    """
    product_id = getattr(self, "last_confirmed_product_id", None)

    # === 规则表（垫片名称 → 校验函数） ===
    # 不同垫片有不同的校验逻辑（浮头垫片、外头盖垫片等）
    GASKET_CHECK_RULES = {
        "管箱垫片": check_general_gasket,
        "头盖垫片": check_general_gasket,
        "平盖垫片": check_general_gasket,
        "管箱侧垫片": check_general_gasket,
        "浮头垫片": check_floating_head_gasket,
        "外头盖垫片": check_outer_head_gasket,
    }

    if not product_id:
        return

    try:
        # 获取所有垫片及其配套法兰数据
        gasket_data = get_gasket_elements(product_id)
        if not gasket_data:
            return

        all_msgs = []  # 收集所有警告消息
        # 遍历每条记录，调用对应的校验函数
        for i, item in enumerate(gasket_data, 1):
            gasket_name = item.get("垫片名称")
            check_func = GASKET_CHECK_RULES.get(gasket_name)
            if check_func:
                try:
                    res = check_func(item)
                    # 校验函数可能返回三个值（等级, 消息, PN值）或两个值
                    if isinstance(res, tuple) and len(res) == 3:
                        level, msg, pn_single = res
                    else:
                        level, msg = res
                        pn_single = None
                    # 将计算出的PN值暂存到item中，供后续聚合使用
                    item["_pn_val"] = pn_single
                    if msg:
                        all_msgs.append(f"[{level.upper()}] {msg}")
                except Exception as inner_e:
                    print(f"[垫片校验][ERROR] 校验函数出错: {inner_e}, item={item}")
            else:
                print(f"[垫片校验] ⚠️ 未定义校验规则: {gasket_name}")

        # 汇总结果显示到界面
        if all_msgs:
            msg_text = "；".join(all_msgs)
            if DEBUG_VERBOSE_DEFINE_UI:
                print("[垫片校验][汇总] 检查结果：\n  " + "\n  ".join(all_msgs))

            # 输出到界面 line_tip 控件
            self.line_tip.setText(msg_text)
            self.line_tip.setToolTip(msg_text)
            self.line_tip.setStyleSheet("color: black;")
        else:
            if DEBUG_VERBOSE_DEFINE_UI:
                print("[垫片校验][汇总] 所有配套法兰校验通过")
            self.line_tip.setText("所有配套法兰校验通过")
            self.line_tip.setToolTip("所有配套法兰校验通过")
            self.line_tip.setStyleSheet("color: black;")

        # === 对同一垫片的多个法兰进行PN聚合 ===
        # 按垫片元件ID分组，每个垫片可能对应多个法兰（如管箱法兰和壳程法兰）
        groups = {}
        for it in gasket_data:
            gid = it.get("垫片元件ID")
            gname = (it.get("垫片名称") or "").strip()
            groups.setdefault((gid, gname), []).append(it)

        for (gid, gname), items in groups.items():
            flanges = [(it.get("配套法兰名称") or "").strip() for it in items]
            if DEBUG_VERBOSE_DEFINE_UI:
                print(f"[垫片校验][组] 垫片ID={gid}, 名称={gname}, 配套法兰={flanges}")

            chosen_pn = None

            # 平盖垫片特殊处理：优先选择管箱法兰的PN值
            if gname == "平盖垫片":
                pn_map = {}
                for it2 in items:
                    nm2 = (it2.get("配套法兰名称") or "").strip()
                    pv2 = it2.get("_pn_val")
                    if pv2 is not None:
                        pn_map[nm2] = pv2
                        if DEBUG_VERBOSE_DEFINE_UI:
                            print(f"[垫片校验][平盖校验] 垫片={gname}, 法兰={nm2}, PN={pv2}")
                # 优先使用管箱法兰的PN
                if "管箱法兰" in pn_map:
                    chosen_pn = pn_map["管箱法兰"]
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][平盖选择] 垫片={gname}, 选法兰=管箱法兰, PN={chosen_pn}")
                else:
                    # 如果没有管箱法兰，则取任意一个非空值
                    for it2 in items:
                        nm2 = (it2.get("配套法兰名称") or "").strip()
                        if nm2 in pn_map:
                            chosen_pn = pn_map[nm2]
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(f"[垫片校验][平盖选择] 垫片={gname}, 选法兰={nm2}, PN={chosen_pn}")
                            break
            else:
                # 其他垫片：取所有法兰PN的最大值（最严格的要求）
                pn_vals = []
                for it in items:
                    pv = it.get("_pn_val")
                    if pv is not None:
                        pn_vals.append(pv)
                if pn_vals:
                    try:
                        chosen_pn = max(pn_vals)
                    except Exception:
                        chosen_pn = pn_vals[-1]
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][聚合最大] 垫片={gname}, 候选PN={pn_vals} → 取最大={chosen_pn}")

            # 更新数据库中的PN值
            if chosen_pn is not None:
                try:
                    conn = get_connection(**db_config1)
                    with conn.cursor() as cursor:
                        current_pn_val = None
                        try:
                            cursor.execute(
                                """
                                SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                                WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                                LIMIT 1
                                """,
                                (product_id, gid)
                            )
                            r0 = cursor.fetchone()
                            if r0:
                                current_pn_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                        except Exception:
                            pass

                        cur_text = str(current_pn_val).strip() if current_pn_val is not None else ""
                        is_user_manual = is_pn_user_input(product_id, gid)

                        # 仅在非用户手动输入或当前值为空/程序推荐时更新
                        if (not is_user_manual) or (cur_text == "" or cur_text == "程序推荐"):
                            cursor.execute(
                                """
                                UPDATE 产品设计活动表_元件附加参数表
                                SET 参数值=%s
                                WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                                """,
                                (chosen_pn, product_id, gid)
                            )
                            conn.commit()
                            try:
                                clear_pn_user_input(product_id, gid)
                            except Exception:
                                pass

                            # 根据新PN值重新计算垫片尺寸
                            try:
                                from modules.cailiaodingyi.funcs.funcs_pdf_change import resolve_gasket_dimensions, \
                                    query_element_name_param_value
                                gasket_standard = query_element_name_param_value(product_id, gname, "垫片标准") or ""
                                gasket_type = query_element_name_param_value(product_id, gname,
                                                                             "垫片型式") or query_element_name_param_value(
                                    product_id, gname, "垫片类型") or ""
                                spec = resolve_gasket_dimensions(product_id, gname, gasket_standard, gasket_type,
                                                                 pn=str(chosen_pn))
                                try:
                                    d_val = spec.get("外直径D")
                                    d_in = spec.get("内直径d")
                                    d1 = spec.get("环内径d1")
                                    # 只有当用户未手动输入且当前值为弱值时，才更新尺寸
                                    if (not is_dim_user_input_any(product_id, gid, gname, "环内径d1")) and is_dim_weak(
                                            product_id, gname, "环内径d1"):
                                        update_element_name_data(product_id, gname, "环内径d1", _norm_out(d1))
                                    if (not is_dim_user_input_any(product_id, gid, gname,
                                                                  "垫片名义外径D2n")) and is_dim_weak(product_id, gname,
                                                                                                      "垫片名义外径D2n"):
                                        update_element_name_data(product_id, gname, "垫片名义外径D2n", _norm_out(d_val))
                                    if (not is_dim_user_input_any(product_id, gid, gname,
                                                                  "垫片名义内径D1n")) and is_dim_weak(product_id, gname,
                                                                                                      "垫片名义内径D1n"):
                                        update_element_name_data(product_id, gname, "垫片名义内径D1n", _norm_out(d_in))
                                    if DEBUG_VERBOSE_DEFINE_UI:
                                        print(
                                            f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gid}, D2n/D1n/d1={_norm_out(d_val)}/{_norm_out(d_in)}/{_norm_out(d1)}")
                                except Exception as e:
                                    print(f"[垫片校验][DB] 更新D2n/D1n/d1失败: {e}")
                            except Exception as e:
                                print(f"[垫片校验] 计算并更新垫片尺寸失败: {e}")
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gid}, 公称压力={chosen_pn}")
                        else:
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(f"[垫片校验][DB] 保留当前PN，不覆盖推荐={chosen_pn}")
                finally:
                    conn.close()


    except Exception as e:
        print(f"[垫片校验] 执行出错: {e}")


# ============================================================================
# 各类垫片的校验函数
# ============================================================================

def check_general_gasket(item):
    """
    校验函数：管箱垫片/头盖垫片/平盖垫片/管箱侧垫片

    校验内容：
    1. 法兰材料牌号是否存在
    2. 根据法兰管壳程获取对应的设计压力和设计温度
    3. 调用calc_pressure_limit计算允许的公称压力PN
    4. 更新数据库中的PN值和垫片尺寸

    参数:
        item: 单个垫片配套法兰的数据字典

    返回:
        tuple: (level, message, pn_val)
            - level: "ok"或"warn"
            - message: 警告信息
            - pn_val: 计算得到的PN值
    """
    gasket_name = item["垫片名称"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    # 如果没有材料牌号，无法进行压力校验
    if not material_list:
        return "warn", f"[{gasket_name}] 未找到材料牌号，无法校验", None

    material = material_list[0]
    messages = []
    pn_candidates = []

    # === 直径校验（代码略，实际在完整函数中，但由于原代码中此部分被注释了，我们保留注释） ===
    # ...

    # === 压力校验 ===
    # 根据法兰所属的管壳程，确定使用管程还是壳程的设计压力和温度
    course_flange = item["法兰管壳程"]
    p_val = item.get("管程设计压力") if course_flange == "管程" else item.get("壳程设计压力")
    t_val = item.get("管程设计温度") if course_flange == "管程" else item.get("壳程设计温度")

    flange_name = item["配套法兰名称"]
    if DEBUG_VERBOSE_DEFINE_UI:
        print(
            f"[垫片校验][逐条] 垫片={gasket_name}, 法兰={flange_name}, 侧别={course_flange}, 材料={material}, P={p_val}, T={t_val}")

    # 调用压力限制计算函数（核心算法）
    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, flange_name
    )
    if msg:
        messages.append(msg)
    pn_out = pn_val if pn_val else None

    # 更新数据库中的PN值
    if pn_out is not None:
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                current_pn_val = None
                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    r0 = cursor.fetchone()
                    if r0:
                        current_pn_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                except Exception:
                    pass

                cur_text = str(current_pn_val).strip() if current_pn_val is not None else ""
                is_user_manual = is_pn_user_input(product_id, gasket_id)

                # 仅在非用户手动输入或当前值为空/程序推荐时更新
                if (not is_user_manual) or (cur_text == "" or cur_text == "程序推荐"):
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        """,
                        (pn_out, product_id, gasket_id)
                    )
                    conn.commit()
                    try:
                        clear_pn_user_input(product_id, gasket_id)
                    except Exception:
                        pass

                    # 根据新PN值重新计算垫片尺寸
                    try:
                        from modules.cailiaodingyi.funcs.funcs_pdf_change import resolve_gasket_dimensions, \
                            query_element_name_param_value
                        gasket_standard = query_element_name_param_value(product_id, gasket_name, "垫片标准") or ""
                        gasket_type = query_element_name_param_value(product_id, gasket_name,
                                                                     "垫片型式") or query_element_name_param_value(
                            product_id, gasket_name, "垫片类型") or ""
                        spec = resolve_gasket_dimensions(product_id, gasket_name, gasket_standard, gasket_type,
                                                         pn=str(pn_out))
                        try:
                            d_val = spec.get("外直径D")
                            d_in = spec.get("内直径d")
                            d1 = spec.get("环内径d1")
                            # 对于每个尺寸参数，仅当用户未手动输入且当前值为弱值时更新
                            if (
                            not is_dim_user_input_any(product_id, gasket_id, gasket_name, "环内径d1")) and is_dim_weak(
                                    product_id, gasket_name, "环内径d1"):
                                update_element_name_data(product_id, gasket_name, "环内径d1", _norm_out(d1))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义外径D2n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义外径D2n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义外径D2n", _norm_out(d_val))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义内径D1n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义内径D1n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义内径D1n", _norm_out(d_in))
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(
                                    f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, D2n/D1n/d1={_norm_out(d_val)}/{_norm_out(d_in)}/{_norm_out(d1)}")
                        except Exception as e:
                            print(f"[垫片校验][DB] 更新D2n/D1n/d1失败: {e}")
                    except Exception as e:
                        print(f"[垫片校验] 计算并更新垫片尺寸失败: {e}")
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={pn_out}")
                else:
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 保留当前PN，不覆盖推荐={pn_out}")
        finally:
            conn.close()

    # 若有警告消息则返回 warn 等级，否则 ok
    if messages:
        return "warn", "；".join(messages), pn_out
    return "ok", "", pn_out


def check_floating_head_gasket(item):
    """
    校验函数：浮头垫片

    特殊规则：
    - 设计压力/温度：取max(管程, 壳程)
    - 公称直径：同普通规则（空/程序推荐跳过）
    - 设计压力：调用calc_pressure_limit（返回候选PN，汇总取最大）

    参数:
        item: 单个垫片配套法兰的数据字典

    返回:
        tuple: (level, message, pn_val)
    """
    gasket_name = item["垫片名称"]
    flange_name = item["配套法兰名称"]
    course_gasket = item["垫片管壳程"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    # 材料牌号缺失则无法校验
    if not material_list:
        return "warn", f"[{gasket_name}-{flange_name}] 未找到材料牌号，无法校验", None

    material = material_list[0]
    messages = []
    pn_candidates = []

    # === STEP1: 查压力等级表基本范围（温度、直径的上下限） ===
    conn = get_connection(**db_config2)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DNmin, DNmax, Tmin, Tmax
                FROM 压力等级表
                WHERE Name = %s
                LIMIT 1
            """, (material,))
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return "warn", f"[{gasket_name}-{flange_name}] 材料牌号 {material} 未在压力等级表中找到"

    dn_min, dn_max = float(row["DNmin"]), float(row["DNmax"])
    t_min, t_max = float(row["Tmin"]), float(row["Tmax"])

    # === STEP2: 取设计压力 / 温度（最大值，允许为空） ===
    # 浮头垫片同时连接管程和壳程，应取两者中更严苛的值
    try:
        p_candidates = [float(v) for v in (
            item.get("管程设计压力"), item.get("壳程设计压力")
        ) if v not in (None, "", "程序推荐")]
        t_candidates = [float(v) for v in (
            item.get("管程设计温度"), item.get("壳程设计温度")
        ) if v not in (None, "", "程序推荐")]

        p_val = max(p_candidates) if p_candidates else None
        t_val = max(t_candidates) if t_candidates else None
    except Exception as e:
        print(f"[浮头垫片][ERROR] 压力/温度转换失败: {e}")
        p_val, t_val = None, None

    # === STEP3: 公称直径校验 ===
    # 根据垫片所在的管壳程，获取对应的公称直径
    if course_gasket == "管程":
        dn_val = item.get("管程公称直径")
    else:
        dn_val = item.get("壳程公称直径")

    if not dn_val or str(dn_val).strip() in ("", "程序推荐"):
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[直径校验][INFO] {gasket_name}-{flange_name} 公称直径为空/程序推荐 → 跳过直径校核")
    else:
        try:
            dn_val_f = float(dn_val)
            if DEBUG_VERBOSE_DEFINE_UI:
                print(f"[直径校验][DEBUG] {gasket_name}-{flange_name} 公称直径={dn_val_f}, 限值=[{dn_min}, {dn_max}]")
            if not (dn_min <= dn_val_f <= dn_max):
                messages.append(f"[{gasket_name}-{flange_name}] 公称直径已超限，垫片尺寸将由程序推荐，用户可对其进行更改")
        except Exception as e:
            print(f"[直径校验][ERROR] {gasket_name}-{flange_name} 公称直径值无效: {dn_val}, 错误={e}")

    # === STEP4: 温度校验 ===
    if not t_val:
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[温度校验][INFO] {gasket_name}-{flange_name} 设计温度为空 → 跳过校核")
    else:
        if not (t_min <= t_val <= t_max):
            messages.append(f"[{gasket_name}-{flange_name}] 设计温度超限，垫片尺寸将由程序推荐，用户可对其进行更改")

    # === STEP5: 设计压力校验 ===
    if DEBUG_VERBOSE_DEFINE_UI:
        print(
            f"[垫片校验][逐条] 垫片={gasket_name}, 法兰={flange_name}, 侧别={course_gasket}, 材料={material}, P={p_val}, T={t_val}")
    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, flange_name
    )
    if msg:
        messages.append(msg)
    pn_out = pn_val if pn_val else None

    # 更新数据库中的PN值（逻辑与通用垫片相同）
    if pn_out is not None:
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                current_pn_val = None
                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    r0 = cursor.fetchone()
                    if r0:
                        current_pn_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                except Exception:
                    pass

                def _to_float_safe(x):
                    """安全转换为浮点数，处理PN前缀（如 "PN1.6" -> 1.6）"""
                    try:
                        s = str(x).strip()
                        if s.upper().startswith("PN"):
                            s = s[2:].strip()
                        return float(s)
                    except Exception:
                        return None

                cur_text = str(current_pn_val).strip() if current_pn_val is not None else ""
                is_user_manual = is_pn_user_input(product_id, gasket_id)

                # 仅在非用户手动输入或当前值为空/程序推荐时更新
                if (not is_user_manual) or (cur_text == "" or cur_text == "程序推荐"):
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        """,
                        (pn_out, product_id, gasket_id)
                    )
                    conn.commit()
                    try:
                        clear_pn_user_input(product_id, gasket_id)
                    except Exception:
                        pass

                    # 根据新PN值重新计算垫片尺寸
                    try:
                        from modules.cailiaodingyi.funcs.funcs_pdf_change import resolve_gasket_dimensions, \
                            query_element_name_param_value
                        gasket_standard = query_element_name_param_value(product_id, gasket_name, "垫片标准") or ""
                        gasket_type = query_element_name_param_value(product_id, gasket_name,
                                                                     "垫片型式") or query_element_name_param_value(
                            product_id, gasket_name, "垫片类型") or ""
                        spec = resolve_gasket_dimensions(product_id, gasket_name, gasket_standard, gasket_type,
                                                         pn=str(pn_out))
                        try:
                            d_val = spec.get("外直径D")
                            d_in = spec.get("内直径d")
                            d1 = spec.get("环内径d1")
                            if (
                            not is_dim_user_input_any(product_id, gasket_id, gasket_name, "环内径d1")) and is_dim_weak(
                                    product_id, gasket_name, "环内径d1"):
                                update_element_name_data(product_id, gasket_name, "环内径d1", _norm_out(d1))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义外径D2n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义外径D2n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义外径D2n", _norm_out(d_val))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义内径D1n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义内径D1n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义内径D1n", _norm_out(d_in))
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(
                                    f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, D2n/D1n/d1={_norm_out(d_val)}/{_norm_out(d_in)}/{_norm_out(d1)}")
                        except Exception as e:
                            print(f"[垫片校验][DB] 更新D2n/D1n/d1失败: {e}")
                    except Exception as e:
                        print(f"[垫片校验] 计算并更新垫片尺寸失败: {e}")
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={pn_out}")
                else:
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 保留当前PN，不覆盖推荐={pn_out}")
        finally:
            conn.close()

    if messages:
        return "warn", "；".join(messages), pn_out
    return "ok", "", pn_out


def check_outer_head_gasket(item):
    """
    校验函数：外头盖垫片

    特殊规则：
    - 公称直径从外头盖圆筒获取
    - 如果公称直径=="程序推荐" 或为空，则跳过直径校验
    - 温度校验：空值跳过
    - 设计压力校验：调用calc_pressure_limit（返回候选PN，汇总取最大）

    参数:
        item: 单个垫片配套法兰的数据字典

    返回:
        tuple: (level, message, pn_val)
    """
    gasket_name = item["垫片名称"]
    flange_name = item["配套法兰名称"]
    course_flange = item["法兰管壳程"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    if not material_list:
        return "warn", f"[{gasket_name}-{flange_name}] 未找到材料牌号，无法校验", None

    material = material_list[0]
    messages = []
    pn_candidates = []

    # === STEP1: 查压力等级表基本范围 ===
    conn = get_connection(**db_config2)
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT DNmin, DNmax, Tmin, Tmax
                FROM 压力等级表
                WHERE Name = %s
                LIMIT 1
            """, (material,))
            row = cursor.fetchone()
    finally:
        conn.close()

    if not row:
        return "warn", f"[{gasket_name}-{flange_name}] 材料牌号 {material} 未在压力等级表中找到"

    dn_min, dn_max = float(row["DNmin"]), float(row["DNmax"])
    t_min, t_max = float(row["Tmin"]), float(row["Tmax"])

    # === STEP2: 获取外头盖圆筒的公称直径 ===
    dn_val = None
    conn = get_connection(**db_config1)
    try:
        with conn.cursor() as cursor:
            # 查询外头盖圆筒元件ID
            cursor.execute("""
                SELECT 元件ID
                FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件名称 = %s
                LIMIT 1
            """, (product_id, "外头盖圆筒"))
            row = cursor.fetchone()
            if row:
                yuanjian_id = row["元件ID"]
                # 查询外头盖圆筒的公称直径参数
                cursor.execute("""
                    SELECT 参数值
                    FROM 产品设计活动表_元件附加参数表
                    WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '公称直径'
                    LIMIT 1
                """, (product_id, yuanjian_id))
                row2 = cursor.fetchone()
                if row2:
                    dn_val = row2["参数值"]
    finally:
        conn.close()

    # === STEP3: 公称直径校验 ===
    if not dn_val or str(dn_val).strip() in ("", "程序推荐"):
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[直径校验][INFO] {gasket_name}-{flange_name} 公称直径为空/程序推荐 → 跳过直径校核")
    else:
        try:
            dn_val_f = float(dn_val)
            if DEBUG_VERBOSE_DEFINE_UI:
                print(f"[直径校验][DEBUG] {gasket_name}-{flange_name} 公称直径={dn_val_f}, 限值=[{dn_min}, {dn_max}]")
            if not (dn_min <= dn_val_f <= dn_max):
                messages.append(f"[{gasket_name}-{flange_name}] 公称直径已超限，垫片尺寸将由程序推荐，用户可对其进行更改")
        except Exception as e:
            print(f"[直径校验][ERROR] {gasket_name}-{flange_name} 公称直径值无效: {dn_val}, 错误={e}")

    # === STEP4: 温度校验 ===
    t_val = None
    if course_flange == "管程":
        t_val = item.get("管程设计温度")
    elif course_flange == "壳程":
        t_val = item.get("壳程设计温度")

    if not t_val or str(t_val).strip() == "":
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[温度校验][INFO] {gasket_name}-{flange_name} 设计温度为空 → 跳过校核")
    else:
        try:
            t_val_f = float(t_val)
            if not (t_min <= t_val_f <= t_max):
                messages.append(f"[{gasket_name}-{flange_name}] 设计温度超限，垫片尺寸将由程序推荐，用户可对其进行更改")
        except Exception as e:
            print(f"[温度校验][ERROR] {gasket_name}-{flange_name} 温度值无效: {t_val}, 错误={e}")
            t_val_f = None

    # === STEP5: 设计压力校验 ===
    if course_flange == "管程":
        p_val = item.get("管程设计压力")
        t_val = item.get("管程设计温度")
    elif course_flange == "壳程":
        p_val = item.get("壳程设计压力")
        t_val = item.get("壳程设计温度")
    else:
        p_val, t_val = None, None

    if DEBUG_VERBOSE_DEFINE_UI:
        print(
            f"[垫片校验][逐条] 垫片={gasket_name}, 法兰={flange_name}, 侧别={course_flange}, 材料={material}, P={p_val}, T={t_val}")
    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, flange_name
    )
    if msg:
        messages.append(msg)
    pn_out = pn_val if pn_val else None

    # 更新数据库中的PN值（逻辑与通用垫片相同）
    if pn_out is not None:
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                current_pn_val = None
                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    r0 = cursor.fetchone()
                    if r0:
                        current_pn_val = (r0.get("参数值") if isinstance(r0, dict) else (r0[0] if r0 else None))
                except Exception:
                    pass

                cur_text = str(current_pn_val).strip() if current_pn_val is not None else ""
                is_user_manual = is_pn_user_input(product_id, gasket_id)

                # 仅在非用户手动输入或当前值为空/程序推荐时更新
                if (not is_user_manual) or (cur_text == "" or cur_text == "程序推荐"):
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        """,
                        (pn_out, product_id, gasket_id)
                    )
                    conn.commit()
                    try:
                        clear_pn_user_input(product_id, gasket_id)
                    except Exception:
                        pass

                    # 根据新PN值重新计算垫片尺寸
                    try:
                        from modules.cailiaodingyi.funcs.funcs_pdf_change import resolve_gasket_dimensions, \
                            query_element_name_param_value
                        gasket_standard = query_element_name_param_value(product_id, gasket_name, "垫片标准") or ""
                        gasket_type = query_element_name_param_value(product_id, gasket_name,
                                                                     "垫片型式") or query_element_name_param_value(
                            product_id, gasket_name, "垫片类型") or ""
                        spec = resolve_gasket_dimensions(product_id, gasket_name, gasket_standard, gasket_type,
                                                         pn=str(pn_out))
                        try:
                            d_val = spec.get("外直径D")
                            d_in = spec.get("内直径d")
                            d1 = spec.get("环内径d1")
                            if (
                            not is_dim_user_input_any(product_id, gasket_id, gasket_name, "环内径d1")) and is_dim_weak(
                                    product_id, gasket_name, "环内径d1"):
                                update_element_name_data(product_id, gasket_name, "环内径d1", _norm_out(d1))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义外径D2n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义外径D2n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义外径D2n", _norm_out(d_val))
                            if (not is_dim_user_input_any(product_id, gasket_id, gasket_name,
                                                          "垫片名义内径D1n")) and is_dim_weak(product_id, gasket_name,
                                                                                              "垫片名义内径D1n"):
                                update_element_name_data(product_id, gasket_name, "垫片名义内径D1n", _norm_out(d_in))
                            if DEBUG_VERBOSE_DEFINE_UI:
                                print(
                                    f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, D2n/D1n/d1={_norm_out(d_val)}/{_norm_out(d_in)}/{_norm_out(d1)}")
                        except Exception as e:
                            print(f"[垫片校验][DB] 更新D2n/D1n/d1失败: {e}")
                    except Exception as e:
                        print(f"[垫片校验] 计算并更新垫片尺寸失败: {e}")
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={pn_out}")
                else:
                    if DEBUG_VERBOSE_DEFINE_UI:
                        print(f"[垫片校验][DB] 保留当前PN，不覆盖推荐={pn_out}")
        finally:
            conn.close()

    if messages:
        return "warn", "；".join(messages), pn_out
    return "ok", "", pn_out


def calc_pressure_limit(material, T, P, product_id, gasket_id, gasket_name, flange_name):
    """
    根据压力等级表计算设计压力是否超限，并返回合适的公称压力PN

    算法逻辑：
    1. 如果设计压力/温度为空或"程序推荐"，跳过校核
    2. 查询材料库中该材料牌号的压力等级表
    3. 遍历所有PN等级，找到满足条件的最小PN：
       - 在当前温度T下，该PN等级的允许压力px_val >= 设计压力P
       - 如果温度T不在表格列中，则通过线性插值计算允许压力
    4. 返回满足条件的最小PN值

    参数:
        material: 法兰材料牌号
        T: 设计温度（℃）
        P: 设计压力（MPa）
        product_id: 产品ID（用于日志）
        gasket_id: 垫片元件ID（用于日志）
        gasket_name: 垫片名称（用于日志）
        flange_name: 法兰名称（用于日志）

    返回:
        tuple: (level, message, pn_val)
            - level: "ok"或"warn"
            - message: 警告信息（超限时）
            - pn_val: 推荐的公称压力PN值
    """
    if DEBUG_VERBOSE_DEFINE_UI:
        print(f"[设计压力校验][DEBUG] 开始校验 → 垫片={gasket_name}, 法兰={flange_name}, 材料={material}, T={T}, P={P}")

    # === 空值保护 ===
    # 如果温度或压力缺失或为"程序推荐"，则无法进行有效校验，直接返回
    if not T or not P or str(T).strip() == "" or str(P).strip() == "" or str(P).strip() == "程序推荐":
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[设计压力校验][INFO] {gasket_name}-{flange_name} 设计压力/温度为空或程序推荐 → 跳过校核")
        return "ok", "", None

    try:
        T = float(T)
        P = float(P)
    except Exception as e:
        print(f"[设计压力校验][ERROR] 转换失败: T={T}, P={P}, 错误={e}")
        return "warn", f"[{gasket_name}-{flange_name}] 设计压力/温度值无效", None

    # === 查库：从材料库的压力等级表中获取该材料的所有PN等级数据 ===
    conn = get_connection(**db_config2)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM 压力等级表 WHERE Name=%s", (material,))
            rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        return "warn", f"[{gasket_name}-{flange_name}] 材料牌号 {material} 未在压力等级表中找到", None

    # 工具函数：获取指定温度列的压力值（精确匹配）
    def get_col_value(row, temp):
        """
        从行数据中获取指定温度列的压力值

        参数:
            row: 压力等级表的一行数据（字典）
            temp: 温度值

        返回:
            float: 该温度下的允许压力值，未找到返回None
        """
        for k in row.keys():
            try:
                # 尝试将键转为浮点数，若相等则返回对应的值
                if float(k) == float(temp):
                    return float(row[k])
            except:
                continue
        return None

    # 提取所有温度列（排除元数据列：Name, PN, DNmin, DNmax, Tmin, Tmax）
    temp_cols = [float(k) for k in rows[0].keys()
                 if k not in ("Name", "PN", "DNmin", "DNmax", "Tmin", "Tmax")]
    temp_cols.sort()
    if DEBUG_VERBOSE_DEFINE_UI:
        print(f"[设计压力校验][DEBUG] 可用温度列: {temp_cols}")

    candidate = None  # 候选的允许压力值
    candidate_row = None  # 候选的行（包含PN等信息）

    # 遍历所有PN等级，找到满足条件的最小PN
    for row in rows:
        PN_val = row.get("PN")
        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[设计压力校验][DEBUG] 检查行: PN={PN_val}")

        # 获取当前温度T下的允许压力px_val
        px_val = get_col_value(row, T)
        if px_val is not None:
            if DEBUG_VERBOSE_DEFINE_UI:
                print(f"[设计压力校验][DEBUG] 命中温度列 T={T}℃ → px_val={px_val}")
        else:
            # 温度T不在表格列中，需要线性插值
            # 找到小于T的最大温度和大于T的最小温度
            lower = max([x for x in temp_cols if x < T], default=None)
            upper = min([x for x in temp_cols if x > T], default=None)
            if lower is None or upper is None:
                if DEBUG_VERBOSE_DEFINE_UI:
                    print(f"[设计压力校验][WARN] 温度 {T} 超范围 → 跳过")
                continue
            y1 = get_col_value(row, lower)
            y2 = get_col_value(row, upper)
            if y1 is None or y2 is None:
                if DEBUG_VERBOSE_DEFINE_UI:
                    print(f"[设计压力校验][WARN] 行缺失: PN={PN_val}, lower={lower}, upper={upper}")
                continue
            # 线性插值公式： y = y1 + (y2 - y1) * (T - lower) / (upper - lower)
            px_val = y1 + (y2 - y1) * (T - lower) / (upper - lower)
            if DEBUG_VERBOSE_DEFINE_UI:
                print(f"[设计压力校验][DEBUG] 插值: ({lower},{y1})-({upper},{y2}) → px_val={px_val}")

        if DEBUG_VERBOSE_DEFINE_UI:
            print(f"[设计压力校验][DEBUG] 对比 P={P}, px_val={px_val}")

        # 如果允许压力 >= 设计压力，则作为候选
        if px_val >= P:
            # 选择允许压力最小的那个PN（即最经济的满足条件的PN）
            if candidate is None or px_val < candidate:
                candidate = px_val
                candidate_row = row
                if DEBUG_VERBOSE_DEFINE_UI:
                    print(f"[设计压力校验][DEBUG] 更新候选: PN={PN_val}, px_val={px_val}")

    if candidate is None:
        # 所有PN等级都不能满足设计压力要求
        return "warn", f"[{gasket_name}-{flange_name}] 设计压力已超限", None

    PN_val = candidate_row.get("PN")
    if DEBUG_VERBOSE_DEFINE_UI:
        print(f"[设计压力校验][RESULT] 选中 PN={PN_val}, px_val={candidate}")
    return "ok", "", PN_val