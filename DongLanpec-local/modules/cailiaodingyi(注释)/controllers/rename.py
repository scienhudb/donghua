from PyQt5.QtWidgets import QLineEdit
from PyQt5.QtCore import Qt


class RenamableLineEdit(QLineEdit):
    """可重命名的行编辑器控件"""

    def __init__(self, old_label, confirm_callback, parent=None):
        """
        初始化可重命名行编辑器

        Args:
            old_label (str): 原始标签文本
            confirm_callback (callable): 确认重命名时的回调函数
            parent: 父组件
        """
        super().__init__(old_label, parent)
        self.old_label = old_label
        self.confirm_callback = confirm_callback
        self._confirmed = False

    def keyPressEvent(self, event):
        """
        处理键盘按键事件

        Args:
            event: 键盘事件对象
        """
        if event.key() in (Qt.Key_Enter, Qt.Key_Return):
            self._confirmed = True
            self.confirm_callback(self.text().strip())
            self.deleteLater()
        elif event.key() == Qt.Key_Escape:
            self.deleteLater()
        else:
            super().keyPressEvent(event)

    def focusOutEvent(self, event):
        """
        处理失去焦点事件

        Args:
            event: 焦点事件对象
        """
        if not self._confirmed:
            self.deleteLater()
        super().focusOutEvent(event)
