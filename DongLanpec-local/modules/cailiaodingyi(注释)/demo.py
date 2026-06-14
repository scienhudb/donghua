from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QComboBox

class NoWheelComboBoxFilter(QObject):
    """禁用下拉框滚轮切换功能"""
    
    def eventFilter(self, obj, event):
        """
        过滤事件：拦截鼠标滚轮
        
        参数:
            obj: 触发事件的控件
            event: 事件对象
        返回:
            True = 阻止滚轮，False = 正常处理
        """
        if event.type() == QEvent.Wheel:
            return True  # 阻止滚轮事件
        return super().eventFilter(obj, event)
