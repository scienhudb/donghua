from PyQt5.QtCore import QEvent, QObject, Qt


class ReturnKeyJumpFilter(QObject):
    """表格回车键跳转过滤器，用于在表格中按回车或方向键时自动跳转到下一行"""

    def __init__(self, table, after_jump_callback=None):
        """
        初始化跳转过滤器

        Args:
            table: 需要添加跳转功能的表格组件
            after_jump_callback (callable, optional): 跳转完成后执行的回调函数，接收行号和列号参数
        """
        super().__init__(table)
        self.table = table
        self.after_jump_callback = after_jump_callback

    def eventFilter(self, obj, event):
        """
        拦截键盘事件，实现按回车或方向键时在表格行间循环跳转

        Args:
            obj: 触发事件的组件对象
            event: 发生的事件

        Returns:
            bool: 返回True表示拦截事件不再传递，False表示继续传递事件
        """
        # 如果单元格正在编辑状态，不拦截事件，让用户正常输入
        if self.table.state() == self.table.EditingState:
            return False

        # 只处理键盘按下事件
        if event.type() == QEvent.KeyPress:
            key = event.key()
            current = self.table.currentIndex()
            # 如果没有选中任何单元格，不处理
            if not current.isValid():
                return False

            row = current.row()
            col = current.column()
            row_count = self.table.rowCount()

            # ⏎ Enter 或 Return
            if key in (Qt.Key_Return, Qt.Key_Enter):
                next_row = (row + 1) % row_count
                self.table.setCurrentCell(next_row, col)
                # 如果有回调函数，执行它
                if self.after_jump_callback:
                    self.after_jump_callback(next_row, col)
                return True

            # 按向上箭头时，跳转到上一行（到第一行后跳到最后一行）
            elif key == Qt.Key_Up:
                prev_row = (row - 1 + row_count) % row_count
                self.table.setCurrentCell(prev_row, col)
                if self.after_jump_callback:
                    self.after_jump_callback(prev_row, col)
                return True

            # 按向下箭头时，跳转到下一行（到最后一行后回到第一行）
            elif key == Qt.Key_Down:
                next_row = (row + 1) % row_count
                self.table.setCurrentCell(next_row, col)
                if self.after_jump_callback:
                    self.after_jump_callback(next_row, col)
                return True

        # 其他情况交给父类处理
        return super().eventFilter(obj, event)
