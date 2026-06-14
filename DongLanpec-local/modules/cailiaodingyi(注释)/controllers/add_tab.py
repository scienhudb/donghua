"""页签管理器模块 - 实现智能'+'按钮（页签模式/corner模式自动切换）"""
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, QEvent, QObject, QTimer
from PyQt5.QtWidgets import QWidget, QToolButton, QTabWidget, QAbstractButton, QTabBar


# 标签栏左对齐样式表
_TAB_BAR_LEFT_ALIGN_QSS = "QTabWidget::tab-bar { alignment: left; }"

# 统一阈值：need > avail + 此值 → corner模式
_TO_CORNER_OVERFLOW = 12
# 最小标签栏宽度
_MIN_BAR_WIDTH = 48
# 更新防抖延迟（毫秒）
_UPDATE_DEBOUNCE_MS = 80


class PlusTabManager(QObject):
    """
    '+' 管理：
      - 空间够：作为最后一个页签
      - 空间不够：右上角 corner 按钮
    关键修复：
      1) 首帧/大窗口启动时强制同步状态，避免角落 '+' 残留
      2) 任何时刻只保留一个 '+'
      3) corner 形态为 QTabBar 右侧预留 margin，防止重叠 & 点不动
      4) 扣除滚动箭头宽度参与判定
    """
    def __init__(self, tw: QTabWidget, on_add_from_src):
        """
        初始化 '+' 页签管理器。
        
        Args:
            tw: QTabWidget 实例
            on_add_from_src: 从源页签创建新页签的回调函数
        """
        super().__init__(tw)
        self.tw = tw
        self.on_add_from_src = on_add_from_src

        # 状态标志
        self._plus_as_tab = True  # '+' 是否作为页签显示
        self._plus_tab_index = -1  # '+' 页签索引
        self._adding = False  # 是否正在添加页签
        self._ready = False  # 布局是否已准备好
        self._reserved_margin = False  # 是否已预留 corner 空间
        self._switching = False  # 是否正在切换模式
        self._orig_tabbar_stylesheet = tw.tabBar().styleSheet()  # 原始标签栏样式

        # 创建防抖定时器
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(_UPDATE_DEBOUNCE_MS)
        self._update_timer.timeout.connect(self._update_mode_impl)

        # 配置标签栏
        self._configure_tab_bar()

        # 断开旧连接并清理 '+' 页签
        bar = self.tw.tabBar()

        # 先断开旧连接 & 清理历史 '+'
        try:
            bar.tabBarClicked.disconnect(self._on_tabbar_clicked)
        except Exception:
            pass
        self._remove_all_plus_tabs()

        # 添加初始的 '+' 页签
        self._plus_tab_index = self.tw.addTab(QWidget(), "+")
        bar.tabBarClicked.connect(self._on_tabbar_clicked)

        # 创建 corner 按钮（右上角 '+' 按钮）
        self._btn = QToolButton(self.tw)
        self._btn.setText("+")
        self._btn.setAutoRaise(True)
        self._btn.setCursor(Qt.PointingHandCursor)
        self._btn.clicked.connect(self._on_corner_plus_clicked)
        self.tw.setCornerWidget(self._btn, Qt.TopRightCorner)
        self._btn.hide()

        # 安装事件过滤器
        self.tw.installEventFilter(self)
        bar.installEventFilter(self)

        # 多次延迟同步以确保初始化完成
        for t in (0, 50, 150, 300):
            QTimer.singleShot(t, lambda: self._force_sync(prefer_tab=True))

    def _configure_tab_bar(self):
        """配置标签栏的基本样式和对齐方式。"""
        tw = self.tw
        bar = tw.tabBar()
        # 禁止扩展和省略
        bar.setExpanding(False)
        bar.setElideMode(Qt.ElideNone)
        if self._plus_as_tab:
            bar.setUsesScrollButtons(False)

        # 应用左对齐样式
        ss = tw.styleSheet() or ""
        if _TAB_BAR_LEFT_ALIGN_QSS.strip() not in ss:
            tw.setStyleSheet((ss + "\n" + _TAB_BAR_LEFT_ALIGN_QSS).strip())

    def _layout_ready(self, bar) -> bool:
        """
        判断布局是否已准备好（控件可见且宽度足够）。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            bool: 布局是否就绪
        """
        if not (self.tw.isVisible() and bar.isVisible()):
            return False
        return max(bar.width(), self.tw.width(), 0) >= _MIN_BAR_WIDTH

    def _corner_reserve_width(self) -> int:
        """
        计算 corner 按钮需要预留的宽度。
        
        Returns:
            int: 需要预留的像素宽度
        """
        if not self._reserved_margin:
            return 0
        return max(self._btn.width(), self._plus_tab_width()) + 6

    def _remove_all_plus_tabs(self):
        """移除所有 '+' 页签（包括中英文加号）。"""
        for i in range(self.tw.count() - 1, -1, -1):
            if self.tw.tabText(i).strip() in {"+", "＋"}:
                self.tw.removeTab(i)

    def _ensure_single_plus(self):
        """确保只有一个 '+' 元素（页签或 corner 按钮），根据当前模式切换。"""
        if self._plus_as_tab:
            # 页签模式：隐藏 corner 按钮，添加 '+' 页签
            try:
                self.tw.setCornerWidget(None, Qt.TopRightCorner)
            except Exception:
                pass
            self._btn.hide()
            self.tw.tabBar().setUsesScrollButtons(False)
            has_plus = any(self.tw.tabText(i).strip() in {"+", "＋"} for i in range(self.tw.count()))
            if not has_plus:
                self._plus_tab_index = self.tw.addTab(QWidget(), "+")
        else:
            # Corner 模式：移除所有 '+' 页签，显示 corner 按钮
            self._remove_all_plus_tabs()
            try:
                self.tw.setCornerWidget(self._btn, Qt.TopRightCorner)
            except Exception:
                pass
            self._btn.show()
            self._btn.raise_()
            self.tw.tabBar().setUsesScrollButtons(True)

    def _plus_tab_width(self):
        """
        计算 '+' 页签所需的宽度。
        
        Returns:
            int: '+' 页签宽度（像素）
        """
        fm = self.tw.tabBar().fontMetrics()
        return fm.horizontalAdvance("+") + 28

    def _text_tab_width(self, bar, index: int) -> int:
        """
        计算指定文本页签的宽度（含左右按钮）。
        
        Args:
            bar: 标签栏对象
            index: 页签索引
            
        Returns:
            int: 页签总宽度（像素）
        """
        text = (self.tw.tabText(index) or "").strip()
        if text in {"+", "＋"}:
            return 0
        fm = bar.fontMetrics()
        w = fm.horizontalAdvance(text) + 28
        # 累加左右侧按钮宽度（如关闭按钮）
        for side in (QTabBar.LeftSide, QTabBar.RightSide):
            btn = bar.tabButton(index, side)
            if btn and btn.isVisible():
                w += btn.width()
        return w

    def _need_width_for_plus_tab(self, bar) -> int:
        """
        计算容纳所有页签和 '+' 页签所需的总宽度。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            int: 所需总宽度（像素）
        """
        total = 0
        for i in range(bar.count()):
            t = self.tw.tabText(i).strip()
            if t in {"+", "＋"}:
                continue
            total += self._text_tab_width(bar, i)
        if total <= 0:
            return self._plus_tab_width()
        return total + self._plus_tab_width() + 12

    def _avail_for_decision(self, bar) -> int:
        """
        判断可用宽度。
        不扣滚动条：滚动条是 corner 形态的结果，扣掉会导致删 tab 后仍误判放不下。
        corner 时已预留的 margin-right 要扣除。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            int: 可用宽度（像素）
        """
        w = max(bar.width(), self.tw.width(), _MIN_BAR_WIDTH)
        w -= self._corner_reserve_width()
        return max(_MIN_BAR_WIDTH, w)

    def _last_real_tab_index(self, bar) -> int:
        """
        获取最后一个非 '+' 页签的索引。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            int: 最后一个真实页签的索引，未找到返回 -1
        """
        last = -1
        for i in range(bar.count()):
            if self.tw.tabText(i).strip() not in {"+", "＋"}:
                last = i
        return last

    def _geom_fits_plus_tab(self, bar) -> bool:
        """
        按末 tab 实际右边界判断：能否在后方再接 '+' 页签。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            bool: 是否能放下 '+' 页签
        """
        last = self._last_real_tab_index(bar)
        if last < 0:
            return True
        rect = bar.tabRect(last)
        if not rect.isValid() or rect.width() <= 0:
            return False
        avail = self._avail_for_decision(bar)
        return rect.right() + self._plus_tab_width() + 8 <= avail

    def _want_corner_mode(self, bar) -> bool:
        """
        判断是否应该使用 corner 模式。
        
        Args:
            bar: 标签栏对象
            
        Returns:
            bool: 是否应切换到 corner 模式
        """
        if not self._layout_ready(bar):
            return False

        # 几何上能放下 → 一定回到/保持页签形态（解决 7→6 删 tab 后仍卡 corner）
        if self._geom_fits_plus_tab(bar):
            return False

        avail = self._avail_for_decision(bar)
        need = self._need_width_for_plus_tab(bar)
        return need > avail + _TO_CORNER_OVERFLOW

    def _reserve_corner_space(self, enable: bool):
        """
        在标签栏右侧预留或取消预留 corner 按钮空间。
        
        Args:
            enable: True 为预留空间，False 为取消预留
        """
        bar = self.tw.tabBar()
        if enable and not self._reserved_margin:
            pad = self._corner_reserve_width() or (self._plus_tab_width() + 6)
            bar.setStyleSheet(self._orig_tabbar_stylesheet + f" QTabBar{{margin-right:{pad}px;}}")
            self._reserved_margin = True
        elif not enable and self._reserved_margin:
            bar.setStyleSheet(self._orig_tabbar_stylesheet)
            self._reserved_margin = False

    def eventFilter(self, obj, ev):
        """
        事件过滤器：监听显示、调整大小等事件以更新模式。
        
        Args:
            obj: 事件对象
            ev: 事件类型
            
        Returns:
            bool: 是否拦截事件
        """
        if self._switching:
            return False
        if ev.type() in (QEvent.Show, QEvent.ShowToParent, QEvent.Resize, QEvent.LayoutRequest, QEvent.Polish):
            self.update_mode()
        return False

    def update_mode(self):
        """触发模式更新（防抖处理）。"""
        self._update_timer.start()

    def _force_sync(self, prefer_tab: bool = False):
        """
        强制同步模式，可选优先使用页签模式。
        
        Args:
            prefer_tab: 是否优先使用页签模式
        """
        bar = self.tw.tabBar()
        if not self.tw.isVisible():
            return

        if prefer_tab:
            self._plus_as_tab = True
            self._reserve_corner_space(False)
            self._btn.hide()
            self._ensure_single_plus()

        if not self._layout_ready(bar):
            return

        self._ready = True
        self._update_mode_impl()

    def _apply_mode(self, want_corner: bool):
        """
        应用 corner 或页签模式切换。
        
        Args:
            want_corner: True 为 corner 模式，False 为页签模式
        """
        if want_corner == (not self._plus_as_tab):
            return

        self._switching = True
        try:
            if want_corner:
                # 切换到 corner 模式
                self._plus_as_tab = False
                self._reserve_corner_space(True)
                self._ensure_single_plus()
            else:
                # 切换到页签模式
                self._plus_as_tab = True
                self._reserve_corner_space(False)
                self._ensure_single_plus()
        finally:
            self._switching = False

        if not self._plus_as_tab:
            bar = self.tw.tabBar()
            self._btn.setFixedHeight(bar.sizeHint().height())
            self._btn.raise_()

    def _update_mode_impl(self):
        """实际执行模式更新的实现。"""
        if self._switching or self._adding:
            return

        bar = self.tw.tabBar()
        if not self._layout_ready(bar):
            return

        if not self._ready:
            self._ready = True

        self._apply_mode(self._want_corner_mode(bar))

    def _on_tabbar_clicked(self, index: int):
        """
        处理标签栏点击事件，点击 '+' 页签时创建新页签。
        
        Args:
            index: 被点击的页签索引
        """
        if not self._plus_as_tab:
            return
        if index < 0 or self.tw.tabText(index).strip() not in {"+", "＋"}:
            return
        self._create_from_current()

    def _on_corner_plus_clicked(self):
        """处理 corner '+' 按钮点击事件。"""
        self._create_from_current()

    def _create_from_current(self):
        """从当前页签创建新页签（复制当前页签）。"""
        if self._adding:
            return
        self._adding = True
        try:
            tw = self.tw
            if tw.count() == 0:
                return
            cur = tw.currentIndex()
            if cur < 0:
                cur = 0
            # 如果当前在 '+' 页签上，选择前一个页签作为源
            if self._plus_as_tab and tw.tabText(cur).strip() in {"+", "＋"}:
                cur = max(0, tw.count() - 2)
            src_idx = cur
            src_name = tw.tabText(src_idx)

            # 调用回调创建新页签
            self.on_add_from_src(src_idx, src_name)

            # 重新添加 '+' 页签
            if self._plus_as_tab:
                self._remove_all_plus_tabs()
                self._plus_tab_index = tw.addTab(QWidget(), "+")
        finally:
            self._adding = False
            QTimer.singleShot(0, self.update_mode)

    def refresh_after_model_change(self):
        """数据模型变化后刷新页签模式（如删除页签后）。"""
        self._ready = False
        self._configure_tab_bar()
        # 统计真实页签数量（排除 '+' 页签）
        n_real = sum(
            1 for i in range(self.tw.count())
            if self.tw.tabText(i).strip() not in {"+", "＋"}
        )
        self._force_sync(prefer_tab=(n_real <= 2))
        # 删 tab 后布局需一帧稳定（尤其从 corner 回到页签形态）
        QTimer.singleShot(100, self.update_mode)

    def ensure_plus_tab_mode(self):
        """确保 '+' 页签模式正确（外部调用接口）。"""
        self.update_mode()
