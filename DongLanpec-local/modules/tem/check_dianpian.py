# modules/cailiaodingyi/funcs/check_dianpian.py
from modules.cailiaodingyi.db_cnt import get_connection
from modules.cailiaodingyi.funcs.funcs_pdf_change import (
    resolve_gasket_dimensions,
    update_element_name_data
)

db_config1 = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "产品设计活动库"
}

db_config2 = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "database": "材料库"
}


# === 强制更新PN：用于“条件输入保存”场景 ===
def force_update_pn(product_id: str, gasket_id: str, new_pn):
    """
    将指定垫片的公称压力PN强制写为程序推荐值，并设置来源为“程序推荐”。
    仅用于条件输入保存时的强制覆盖场景。
    """
    try:
        conn = get_connection(**db_config1)
        with conn.cursor() as cursor:
            # 更新PN
            cursor.execute(
                """
                UPDATE 产品设计活动表_元件附加参数表
                SET 参数值=%s
                WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                """,
                (new_pn, product_id, gasket_id)
            )
            # 更新/插入来源
            cursor.execute(
                """
                SELECT 1 FROM 产品设计活动表_元件附加参数表
                WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源' LIMIT 1
                """,
                (product_id, gasket_id)
            )
            exists_flag = cursor.fetchone()
            if exists_flag:
                cursor.execute(
                    """
                    UPDATE 产品设计活动表_元件附加参数表
                    SET 参数值=%s
                    WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                    """,
                    ("程序推荐", product_id, gasket_id)
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO 产品设计活动表_元件附加参数表(产品ID, 元件ID, 参数名称, 参数值)
                    VALUES (%s, %s, '公称压力PN_来源', %s)
                    """,
                    (product_id, gasket_id, "程序推荐")
                )
            conn.commit()
            print(f"[条件输入保存][强制PN] 产品{product_id}, 垫片ID={gasket_id}, PN→{new_pn} (来源=程序推荐)")
    except Exception as e:
        print(f"[条件输入保存][强制PN] 更新失败: {e}")
    finally:
        try:
            conn.close()
        except Exception:
            pass


def get_gasket_elements(product_id):
    """
    查询指定产品ID的所有垫片配套法兰明细
    返回结构：[
        {
          "产品ID":..., "垫片名称":..., "垫片元件ID":..., "垫片管壳程":...,
          "配套法兰名称":..., "法兰元件ID":..., "法兰管壳程":..., "法兰材料牌号": [...],
          "管程设计压力":..., "壳程设计压力":...,
          "管程设计温度":..., "壳程设计温度":...,
          "管程公称直径":..., "壳程公称直径":...
        }, ...
    ]
    """
    # === STEP1 & STEP2: 查垫片元件 ===
    conn = get_connection(**db_config1)
    gasket_ids, gasket_names = [], {}
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 元件ID
                FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件名称 LIKE %s
            """, (product_id, "%垫片%"))
            rows = cursor.fetchall()
            gasket_ids = [row["元件ID"] for row in rows]

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

    if not gasket_ids:
        return []

    # === STEP3-5: 查配套法兰 + 法兰元件ID + 材料牌号 ===
    result = []
    conn2 = get_connection(**db_config2)
    try:
        with conn2.cursor() as cursor2:
            for gid, gname in gasket_names.items():
                cursor2.execute("""
                    SELECT *
                    FROM 垫片配套法兰映射表
                    WHERE 垫片名称 = %s
                """, (gname,))
                rows = cursor2.fetchall()

                for r in rows:
                    flange_name = r.get("配套法兰") or r.get("法兰名称")
                    gasket_course = r.get("垫片管壳程") if "垫片管壳程" in r else None
                    flange_course = r.get("法兰管壳程") if "法兰管壳程" in r else None

                    # === STEP4: 查配套法兰元件ID ===
                    conn3 = get_connection(**db_config1)
                    try:
                        with conn3.cursor() as cursor3:
                            cursor3.execute("""
                                SELECT 元件ID
                                FROM 产品设计活动表_元件材料表
                                WHERE 产品ID = %s AND 元件名称 = %s
                            """, (product_id, flange_name))
                            flange_rows = cursor3.fetchall()
                            flange_ids = [fr["元件ID"] for fr in flange_rows]

                            for fid in flange_ids:
                                # === STEP5: 查材料牌号 ===
                                cursor3.execute("""
                                    SELECT 参数值
                                    FROM 产品设计活动表_元件附加参数表
                                    WHERE 产品ID = %s AND 元件ID = %s AND 参数名称 = '材料牌号'
                                """, (product_id, fid))
                                mrows = cursor3.fetchall()
                                mvals = [mr["参数值"] for mr in mrows if mr.get("参数值")]

                                # 先存起来，等STEP6加设计数据后再统一返回
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

    # === STEP6: 查设计数据表 ===
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
            cursor4.execute("""
                SELECT 参数名称, 管程数值, 壳程数值
                FROM 产品设计活动表_设计数据表
                WHERE 产品ID = %s
                  AND 参数名称 IN ('设计压力*', '设计温度（最高）*', '公称直径*')
            """, (product_id,))
            rows = cursor4.fetchall()

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


def update_gasket_dimensions_after_pn(product_id: str, gasket_id: str, gasket_name: str, max_pn):
    """
    通用函数：在更新PN后，更新垫片尺寸（外直径、内直径、环内径）

    参数:
        product_id: 产品ID
        gasket_id: 垫片元件ID
        gasket_name: 垫片名称
        max_pn: 刚计算出的最大PN值
    """
    try:
        # 1. 查询垫片的元件名称、垫片标准、垫片类型
        conn = get_connection(**db_config1)
        element_name = None
        gasket_standard = ""
        gasket_type = ""
        gasket_name_final = gasket_name
        try:
            with conn.cursor() as cursor:
                # 查询元件名称
                cursor.execute("""
                    SELECT 元件名称
                    FROM 产品设计活动表_元件附加参数表
                    WHERE 产品ID = %s AND 元件ID = %s
                    LIMIT 1
                """, (product_id, gasket_id))
                row = cursor.fetchone()
                if row:
                    element_name = row.get("元件名称", "").strip()

                # 查询垫片标准、垫片类型、垫片名称
                cursor.execute("""
                    SELECT 参数名称, 参数值
                    FROM 产品设计活动表_元件附加参数表
                    WHERE 产品ID = %s AND 元件ID = %s
                      AND 参数名称 IN ('垫片标准', '垫片类型', '垫片型式', '垫片名称')
                """, (product_id, gasket_id))
                rows = cursor.fetchall() or []
                for r in rows:
                    pnam = (r.get("参数名称") or "").strip()
                    pval = (r.get("参数值") or "").strip()
                    if pnam == "垫片名称" and pval:
                        gasket_name_final = pval
                    elif pnam == "垫片标准" and pval:
                        gasket_standard = pval
                    elif pnam == "垫片类型" and pval:
                        gasket_type = pval
                    elif pnam == "垫片型式" and pval and not gasket_type:
                        # 如果还没有垫片类型，使用垫片型式
                        gasket_type = pval
        finally:
            conn.close()

        # 如果没有找到元件名称，使用垫片名称
        if not element_name:
            element_name = gasket_name_final

        # 2. 调用 resolve_gasket_dimensions 计算垫片尺寸
        # 传入刚计算的max_pn，确保使用正确的PN值（而不是重新计算）
        def _norm_out(v: str) -> str:
            """字段值兜底：空/None -> '程序推荐'"""
            if v is None:
                return "程序推荐"
            s = str(v).strip()
            return s if s else "程序推荐"

        try:
            spec = resolve_gasket_dimensions(
                product_id=product_id,
                gasket_name=gasket_name_final,
                gasket_standard=gasket_standard,
                gasket_type=gasket_type,
                pn=str(max_pn)  # 传入刚计算的PN值，不从数据库读取
            )
            # 打印查询结果
            print(
                f"[垫片校验][尺寸更新] 查询结果: nonstd={spec.get('nonstd')}, 外直径D={spec.get('外直径D')}, 内直径d={spec.get('内直径d')}, 环内径d1={spec.get('环内径d1')}")
        except Exception as e:
            # 任何异常均写"程序推荐"
            update_element_name_data(product_id, element_name, "垫片名义外径D2n", "程序推荐")
            update_element_name_data(product_id, element_name, "垫片名义内径D1n", "程序推荐")
            update_element_name_data(product_id, element_name, "环内径d1", "程序推荐")
            print(f"[垫片校验][尺寸更新] 计算垫片尺寸失败: {e}")
        else:
            # 3. 更新垫片尺寸到数据库
            if not spec.get("nonstd", False):
                # 命中情况下，有些字段可能仍为空 -> 单字段兜底为"程序推荐"
                outer_d = _norm_out(spec.get("外直径D"))
                inner_d = _norm_out(spec.get("内直径d"))
                ring_d1 = _norm_out(spec.get("环内径d1"))

                # 打印命中的内外径具体值
                print(f"[垫片校验][尺寸更新] 命中垫片尺寸: 外直径D={outer_d}, 内直径d={inner_d}, 环内径d1={ring_d1}")

                update_element_name_data(product_id, element_name, "垫片名义外径D2n", outer_d)
                update_element_name_data(product_id, element_name, "垫片名义内径D1n", inner_d)
                update_element_name_data(product_id, element_name, "环内径d1", ring_d1)
            else:
                # 未命中，写"程序推荐"
                print(f"[垫片校验][尺寸更新] 未命中垫片尺寸，使用程序推荐 (msg={spec.get('msg', '')})")
                update_element_name_data(product_id, element_name, "垫片名义外径D2n", "程序推荐")
                update_element_name_data(product_id, element_name, "垫片名义内径D1n", "程序推荐")
                update_element_name_data(product_id, element_name, "环内径d1", "程序推荐")

            print(f"[垫片校验][尺寸更新] 已更新产品{product_id}, 垫片名称={element_name}, PN={max_pn}, 尺寸={spec}")

    except Exception as e:
        print(f"[垫片校验][尺寸更新] 更新垫片尺寸失败: {e}")
        # 异常不影响主流程，继续执行


def check_gasket_params(self):
    product_id = getattr(self, "last_confirmed_product_id", None)
    force_recompute = getattr(self, "force_recompute_on_condition_save", False)

    # === 规则表（垫片名称 → 校验函数） ===
    GASKET_CHECK_RULES = {
        "管箱垫片": check_general_gasket,
        "头盖垫片": check_general_gasket,
        "平盖垫片": check_general_gasket,
        "管箱侧垫片": check_general_gasket,
        "浮头垫片": check_floating_head_gasket,
        "外头盖垫片": check_outer_head_gasket,
    }

    if not product_id:
        return []

    try:
        gasket_data = get_gasket_elements(product_id)
        if not gasket_data:
            return []

        all_msgs = []
        # 收集所有需要更新尺寸的垫片信息
        gaskets_to_update = []  # [(product_id, gasket_id, gasket_name, max_pn), ...]

        for i, item in enumerate(gasket_data, 1):
            gasket_name = item.get("垫片名称")
            check_func = GASKET_CHECK_RULES.get(gasket_name)
            if check_func:
                try:
                    # 校验函数现在返回 (level, msg, max_pn)
                    result = check_func(item)  # ✅ 直接传整个 item
                    if len(result) == 3:
                        level, msg, max_pn = result
                    else:
                        # 兼容旧版本：如果没有返回max_pn，默认为None
                        level, msg = result
                        max_pn = None

                    if msg:
                        all_msgs.append(f"[{level.upper()}] {msg}")

                    # 如果计算出了max_pn，收集起来用于后续更新尺寸
                    if max_pn is not None:
                        product_id = item.get("产品ID")
                        gasket_id = item.get("垫片元件ID")
                        if force_recompute:
                            # 条件输入保存：强制覆盖PN为推荐，并一定加入尺寸重算
                            try:
                                force_update_pn(product_id, gasket_id, max_pn)
                            except Exception as _e:
                                print(f"[条件输入保存] 强制PN写回失败: {_e}")
                            gaskets_to_update.append((product_id, gasket_id, gasket_name, max_pn))
                            print(f"[条件输入保存][收集] 垫片={gasket_name}, 元件ID={gasket_id}, 强制max_pn={max_pn}")
                        else:
                            # 普通场景：尊重用户输入来源，来源为用户输入则不重算尺寸
                            skip_update = False
                            try:
                                conn = get_connection(**db_config1)
                                with conn.cursor() as cursor:
                                    cursor.execute(
                                        """
                                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                                        LIMIT 1
                                        """,
                                        (product_id, gasket_id)
                                    )
                                    r = cursor.fetchone()
                                    src = (r.get("参数值") if isinstance(r, dict) else (r[0] if r else None))
                                    if str(src).strip() in {"用户输入", "manual"}:
                                        skip_update = True
                            except Exception as _e:
                                print(f"[垫片校验][收集] 读取PN来源失败: {_e}")
                            finally:
                                try:
                                    conn.close()
                                except Exception:
                                    pass

                            if not skip_update:
                                gaskets_to_update.append((product_id, gasket_id, gasket_name, max_pn))
                                print(f"[垫片校验][收集] 垫片={gasket_name}, 元件ID={gasket_id}, max_pn={max_pn}")
                            else:
                                print(f"[垫片校验][收集] 垫片={gasket_name} PN来源=用户输入 → 跳过尺寸重算收集")
                except Exception as inner_e:
                    print(f"[垫片校验][ERROR] 校验函数出错: {inner_e}, item={item}")
            else:
                print(f"[垫片校验] ⚠️ 未定义校验规则: {gasket_name}")

        if all_msgs:
            # 汇总结果
            msg_text = "；".join(all_msgs)
            print("[垫片校验][汇总] 检查结果：\n  " + "\n  ".join(all_msgs))

            # 输出到界面 line_tip
            if hasattr(self, 'line_tip') and self.line_tip:
                self.line_tip.setText(msg_text)
                self.line_tip.setToolTip(msg_text)
                self.line_tip.setStyleSheet("color: black;")
        else:
            print("[垫片校验][汇总] 所有配套法兰校验通过")
            if hasattr(self, 'line_tip') and self.line_tip:
                self.line_tip.setText("所有配套法兰校验通过")
                self.line_tip.setToolTip("所有配套法兰校验通过")
                self.line_tip.setStyleSheet("color: black;")

        # 返回所有需要更新尺寸的垫片信息
        return gaskets_to_update

    except Exception as e:
        print(f"[垫片校验] 执行出错: {e}")
        return []


# === 法兰校验函数示例 ===
def check_general_gasket(item):
    """
    校验函数：管箱垫片/头盖垫片/平盖垫片/管箱侧垫片
    """
    gasket_name = item["垫片名称"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    if not material_list:
        return "warn", f"[{gasket_name}] 未找到材料牌号，无法校验"

    material = material_list[0]
    messages = []
    pn_candidates = []

    # === 直径校验（同前，略） ===
    # ...

    # === 压力校验 ===
    course_flange = item["法兰管壳程"]
    p_val = item.get("管程设计压力") if course_flange == "管程" else item.get("壳程设计压力")
    t_val = item.get("管程设计温度") if course_flange == "管程" else item.get("壳程设计温度")

    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, item["配套法兰名称"]
    )
    if msg:
        messages.append(msg)
    if pn_val:
        pn_candidates.append(pn_val)

    # === 汇总多个法兰 → 取最大 PN ===
    max_pn = None
    if pn_candidates:
        max_pn = max(pn_candidates)
        print(f"[垫片校验][汇总] 垫片={gasket_name}, 候选PN={pn_candidates} → 取最大={max_pn}")
        # === PN写回门控：来源为“用户输入”时不更新 ===
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                # 读取当前PN与来源标志
                current_pn_val = None
                pn_source = None
                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    row0 = cursor.fetchone()
                    if row0:
                        current_pn_val = (row0.get("参数值") if isinstance(row0, dict) else row0[0])
                except Exception as _e:
                    print(f"[垫片校验][PN读取] 读取当前PN失败: {_e}")

                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    row1 = cursor.fetchone()
                    if row1:
                        pn_source = (row1.get("参数值") if isinstance(row1, dict) else row1[0])
                except Exception as _e:
                    print(f"[垫片校验][PN来源读取] 失败: {_e}")

                # 判定是否用户手动值，及比较大小
                def _to_float_safe(x):
                    try:
                        return float(str(x).strip())
                    except Exception:
                        return None

                is_user_manual = (str(pn_source).strip() in {"用户输入", "manual"})
                cur_val_f = _to_float_safe(current_pn_val)
                rec_val_f = _to_float_safe(max_pn)

                # 更新门控：只要来源是“用户输入”，无条件保留用户值，不覆盖
                # 这样即使推荐PN更大，也尊重用户在元件定义中的手动修改
                should_update = True
                if is_user_manual:
                    should_update = False
                else:
                    # 非手动来源时，如果当前值已经不小于推荐，也不更新
                    if (cur_val_f is not None) and (rec_val_f is not None) and cur_val_f >= rec_val_f:
                        should_update = False

                if should_update:
                    # 更新PN为推荐值，并将来源标志置为程序推荐
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        """,
                        (max_pn, product_id, gasket_id)
                    )
                    # 写入/更新来源标志
                    cursor.execute(
                        """
                        SELECT 1 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源' LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    exists_flag = cursor.fetchone()
                    if exists_flag:
                        cursor.execute(
                            """
                            UPDATE 产品设计活动表_元件附加参数表
                            SET 参数值=%s
                            WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                            """,
                            ("程序推荐", product_id, gasket_id)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO 产品设计活动表_元件附加参数表(产品ID, 元件ID, 参数名称, 参数值)
                            VALUES (%s, %s, '公称压力PN_来源', %s)
                            """,
                            (product_id, gasket_id, "程序推荐")
                        )
                    conn.commit()
                    print(
                        f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={max_pn} (来源=程序推荐)")
                else:
                    print(f"[垫片校验][DB] 保留当前PN={current_pn_val} (来源={pn_source})，不覆盖推荐={max_pn}")
        finally:
            conn.close()

        # ===== 更新垫片尺寸 =====
        # 注释掉：不再在这里自动更新尺寸，改为在check_gasket_params中统一调用
        # 这样可以保护用户手动修改的值，只有在用户主动修改垫片标准/类型/PN时才会触发尺寸更新
        # update_gasket_dimensions_after_pn(product_id, gasket_id, gasket_name, max_pn)

    # 返回 (level, msg, max_pn)，供check_gasket_params调用update_gasket_dimensions_after_pn使用
    if messages:
        return "warn", "；".join(messages), max_pn
    return "ok", "", max_pn


def check_floating_head_gasket(item):
    """
    校验函数：浮头垫片
    - 设计压力/温度：取 max(管程, 壳程)
    - 公称直径：同普通规则（空/程序推荐跳过）
    - 设计压力：调用 calc_pressure_limit（返回候选PN，汇总取最大）
    """
    gasket_name = item["垫片名称"]
    flange_name = item["配套法兰名称"]
    course_gasket = item["垫片管壳程"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    if not material_list:
        return "warn", f"[{gasket_name}-{flange_name}] 未找到材料牌号，无法校验"

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

    # === STEP2: 取设计压力 / 温度（最大值，允许为空）===
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
    if course_gasket == "管程":
        dn_val = item.get("管程公称直径")
    else:
        dn_val = item.get("壳程公称直径")

    if not dn_val or str(dn_val).strip() in ("", "程序推荐"):
        print(f"[直径校验][INFO] {gasket_name}-{flange_name} 公称直径为空/程序推荐 → 跳过直径校核")
    else:
        try:
            dn_val_f = float(dn_val)
            print(f"[直径校验][DEBUG] {gasket_name}-{flange_name} 公称直径={dn_val_f}, 限值=[{dn_min}, {dn_max}]")
            if not (dn_min <= dn_val_f <= dn_max):
                messages.append(f"[{gasket_name}-{flange_name}] 公称直径已超限，垫片尺寸将由程序推荐，用户可对其进行更改")
        except Exception as e:
            print(f"[直径校验][ERROR] {gasket_name}-{flange_name} 公称直径值无效: {dn_val}, 错误={e}")

    # === STEP4: 温度校验 ===
    if not t_val:
        print(f"[温度校验][INFO] {gasket_name}-{flange_name} 设计温度为空 → 跳过校核")
    else:
        if not (t_min <= t_val <= t_max):
            messages.append(f"[{gasket_name}-{flange_name}] 设计温度超限，垫片尺寸将由程序推荐，用户可对其进行更改")

    # === STEP5: 设计压力校验 ===
    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, flange_name
    )
    if msg:
        messages.append(msg)
    if pn_val:
        pn_candidates.append(pn_val)

    # === 汇总多个法兰 → 取最大 PN ===
    if pn_candidates:
        max_pn = max(pn_candidates)
        print(f"[垫片校验][汇总] 垫片={gasket_name}, 候选PN={pn_candidates} → 取最大={max_pn}")
        # === PN写回门控：仅当现值为空/非手动或小于推荐值时更新 ===
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                # 读取当前PN与来源标志
                current_pn_val = None
                pn_source = None
                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    row0 = cursor.fetchone()
                    if row0:
                        current_pn_val = (row0.get("参数值") if isinstance(row0, dict) else row0[0])
                except Exception as _e:
                    print(f"[垫片校验][PN读取] 读取当前PN失败: {_e}")

                try:
                    cursor.execute(
                        """
                        SELECT 参数值 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                        LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    row1 = cursor.fetchone()
                    if row1:
                        pn_source = (row1.get("参数值") if isinstance(row1, dict) else row1[0])
                except Exception as _e:
                    print(f"[垫片校验][PN来源读取] 失败: {_e}")

                # 判定是否用户手动值，及比较大小
                def _to_float_safe(x):
                    try:
                        return float(str(x).strip())
                    except Exception:
                        return None

                is_user_manual = (str(pn_source).strip() in {"用户输入", "manual"})
                cur_val_f = _to_float_safe(current_pn_val)
                rec_val_f = _to_float_safe(max_pn)

                # 更新门控：只要来源是“用户输入”，无条件保留用户值，不覆盖
                should_update = True
                if is_user_manual:
                    should_update = False
                else:
                    if (cur_val_f is not None) and (rec_val_f is not None) and cur_val_f >= rec_val_f:
                        should_update = False

                if should_update:
                    # 更新PN为推荐值，并将来源标志置为程序推荐
                    cursor.execute(
                        """
                        UPDATE 产品设计活动表_元件附加参数表
                        SET 参数值=%s
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                        """,
                        (max_pn, product_id, gasket_id)
                    )
                    # 写入/更新来源标志
                    cursor.execute(
                        """
                        SELECT 1 FROM 产品设计活动表_元件附加参数表
                        WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源' LIMIT 1
                        """,
                        (product_id, gasket_id)
                    )
                    exists_flag = cursor.fetchone()
                    if exists_flag:
                        cursor.execute(
                            """
                            UPDATE 产品设计活动表_元件附加参数表
                            SET 参数值=%s
                            WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN_来源'
                            """,
                            ("程序推荐", product_id, gasket_id)
                        )
                    else:
                        cursor.execute(
                            """
                            INSERT INTO 产品设计活动表_元件附加参数表(产品ID, 元件ID, 参数名称, 参数值)
                            VALUES (%s, %s, '公称压力PN_来源', %s)
                            """,
                            (product_id, gasket_id, "程序推荐")
                        )
                    conn.commit()
                    print(
                        f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={max_pn} (来源=程序推荐)")
                else:
                    print(f"[垫片校验][DB] 保留当前PN={current_pn_val} (来源={pn_source})，不覆盖推荐={max_pn}")
        finally:
            conn.close()

        # # ===== 更新垫片尺寸 =====
        # update_gasket_dimensions_after_pn(product_id, gasket_id, gasket_name, max_pn)

    # 返回 (level, msg, max_pn)，供check_gasket_params调用update_gasket_dimensions_after_pn使用
    if messages:
        return "warn", "；".join(messages), max_pn
    return "ok", "", max_pn


def check_outer_head_gasket(item):
    """
    校验函数：外头盖垫片
    - 公称直径从外头盖圆筒获取
    - 如果公称直径=="程序推荐" 或为空，则跳过直径校验
    - 温度校验：空值跳过
    - 设计压力校验：调用 calc_pressure_limit（返回候选PN，汇总取最大）
    """
    gasket_name = item["垫片名称"]
    flange_name = item["配套法兰名称"]
    course_flange = item["法兰管壳程"]
    product_id = item["产品ID"]
    gasket_id = item["垫片元件ID"]
    material_list = item.get("法兰材料牌号", [])

    if not material_list:
        return "warn", f"[{gasket_name}-{flange_name}] 未找到材料牌号，无法校验"

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
            cursor.execute("""
                SELECT 元件ID
                FROM 产品设计活动表_元件材料表
                WHERE 产品ID = %s AND 元件名称 = %s
                LIMIT 1
            """, (product_id, "外头盖圆筒"))
            row = cursor.fetchone()
            if row:
                yuanjian_id = row["元件ID"]
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
        print(f"[直径校验][INFO] {gasket_name}-{flange_name} 公称直径为空/程序推荐 → 跳过直径校核")
    else:
        try:
            dn_val_f = float(dn_val)
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

    level, msg, pn_val = calc_pressure_limit(
        material, t_val, p_val,
        product_id, gasket_id,
        gasket_name, flange_name
    )
    if msg:
        messages.append(msg)
    if pn_val:
        pn_candidates.append(pn_val)

    # === 汇总多个法兰 → 取最大 PN ===
    if pn_candidates:
        max_pn = max(pn_candidates)
        print(f"[垫片校验][汇总] 垫片={gasket_name}, 候选PN={pn_candidates} → 取最大={max_pn}")
        try:
            conn = get_connection(**db_config1)
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE 产品设计活动表_元件附加参数表
                    SET 参数值=%s
                    WHERE 产品ID=%s AND 元件ID=%s AND 参数名称='公称压力PN'
                """, (max_pn, product_id, gasket_id))
                conn.commit()
                print(f"[垫片校验][DB] 已更新产品{product_id}, 垫片ID={gasket_id}, 公称压力={max_pn}")
        finally:
            conn.close()

        # ===== 更新垫片尺寸 =====
        # 注释掉：不再在这里自动更新尺寸，改为在check_gasket_params中统一调用
        # 这样可以保护用户手动修改的值，只有在用户主动修改垫片标准/类型/PN时才会触发尺寸更新
        # update_gasket_dimensions_after_pn(product_id, gasket_id, gasket_name, max_pn)

    # 返回 (level, msg, max_pn)，供check_gasket_params调用update_gasket_dimensions_after_pn使用
    if messages:
        return "warn", "；".join(messages)
    return "ok", ""


def calc_pressure_limit(material, T, P, product_id, gasket_id, gasket_name, flange_name):
    """
    根据压力等级表计算设计压力是否超限
    返回: (level, message, pn_val)
    """
    print(f"[设计压力校验][DEBUG] 开始校验 → 材料={material}, T={T}, P={P}")

    # === 空值保护 ===
    if not T or not P or str(T).strip() == "" or str(P).strip() == "" or str(P).strip() == "程序推荐":
        print(f"[设计压力校验][INFO] {gasket_name}-{flange_name} 设计压力/温度为空或程序推荐 → 跳过校核")
        return "ok", "", None

    try:
        T = float(T)
        P = float(P)
    except Exception as e:
        print(f"[设计压力校验][ERROR] 转换失败: T={T}, P={P}, 错误={e}")
        return "warn", f"[{gasket_name}-{flange_name}] 设计压力/温度值无效", None

    # === 查库 ===
    conn = get_connection(**db_config2)
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM 压力等级表 WHERE Name=%s", (material,))
            rows = cursor.fetchall()
    finally:
        conn.close()

    if not rows:
        return "warn", f"[{gasket_name}-{flange_name}] 材料牌号 {material} 未在压力等级表中找到", None

    # 工具函数
    def get_col_value(row, temp):
        for k in row.keys():
            try:
                if float(k) == float(temp):
                    return float(row[k])
            except:
                continue
        return None

    temp_cols = [float(k) for k in rows[0].keys()
                 if k not in ("Name", "PN", "DNmin", "DNmax", "Tmin", "Tmax")]
    temp_cols.sort()
    print(f"[设计压力校验][DEBUG] 可用温度列: {temp_cols}")

    candidate = None
    candidate_row = None

    for row in rows:
        PN_val = row.get("PN")
        print(f"[设计压力校验][DEBUG] 检查行: PN={PN_val}")

        px_val = get_col_value(row, T)
        if px_val is not None:
            print(f"[设计压力校验][DEBUG] 命中温度列 T={T}℃ → px_val={px_val}")
        else:
            lower = max([x for x in temp_cols if x < T], default=None)
            upper = min([x for x in temp_cols if x > T], default=None)
            if lower is None or upper is None:
                print(f"[设计压力校验][WARN] 温度 {T} 超范围 → 跳过")
                continue
            y1 = get_col_value(row, lower)
            y2 = get_col_value(row, upper)
            if y1 is None or y2 is None:
                print(f"[设计压力校验][WARN] 行缺失: PN={PN_val}, lower={lower}, upper={upper}")
                continue
            px_val = y1 + (y2 - y1) * (T - lower) / (upper - lower)
            print(f"[设计压力校验][DEBUG] 插值: ({lower},{y1})-({upper},{y2}) → px_val={px_val}")

        print(f"[设计压力校验][DEBUG] 对比 P={P}, px_val={px_val}")
        if px_val >= P:
            if candidate is None or px_val < candidate:
                candidate = px_val
                candidate_row = row
                print(f"[设计压力校验][DEBUG] 更新候选: PN={PN_val}, px_val={px_val}")

    if candidate is None:
        return "warn", f"[{gasket_name}-{flange_name}] 设计压力已超限", None

    PN_val = candidate_row.get("PN")
    print(f"[设计压力校验][RESULT] 选中 PN={PN_val}, px_val={candidate}")
    return "ok", "", PN_val



