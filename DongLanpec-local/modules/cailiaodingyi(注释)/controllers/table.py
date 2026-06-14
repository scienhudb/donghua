from PyQt5 import QtWidgets, QtCore, QtGui


class CustomHeaderView(QtWidgets.QHeaderView):
    """自定义表格表头视图，用于美化表头样式"""

    def __init__(self, orientation, parent=None):
        """
        初始化自定义表头

        Args:
            orientation: 表头方向（水平或垂直）
            parent: 父组件
        """
        super().__init__(orientation, parent)
        self.setDefaultAlignment(QtCore.Qt.AlignCenter)

    def paintSection(self, painter, rect, logicalIndex):
        """
        绘制表头的每个单元格（节）

        Args:
            painter: 绘图工具对象
            rect: 单元格的矩形区域
            logicalIndex: 单元格的逻辑索引（行号或列号）
        """
        painter.save()

        # 用浅灰色填充背景
        painter.fillRect(rect, QtGui.QColor("#F2F2F2"))

        # 获取并绘制表头文字
        text = self.model().headerData(logicalIndex, self.orientation(), QtCore.Qt.DisplayRole)
        painter.setPen(QtGui.QPen(QtCore.Qt.black))

        # 设置字体为加粗（统一界面需求）
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)

        # 在单元格中央绘制文字
        painter.drawText(rect, QtCore.Qt.AlignCenter, str(text))

        # 绘制底部分隔线
        pen = QtGui.QPen(QtGui.QColor("#CCCCCC"))
        pen.setWidth(1)
        painter.setPen(pen)
        painter.drawLine(rect.bottomLeft(), rect.bottomRight())

        # 绘制列之间的竖线分隔符（最后一列不画右边框）
        if logicalIndex != self.model().columnCount() - 1:
            painter.drawLine(rect.topRight(), rect.bottomRight())

        painter.restore()