import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Qt, QPoint

class LineDrawer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mouse Click Line Drawer")
        self.setGeometry(100, 100, 800, 600)
        self.points = []  # Stores clicked points
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.points.append(event.pos())
            print(f"Clicked at: ({event.pos().x()}, {event.pos().y()})")
            if len(self.points) > 2:
                self.points.pop(0)  # Keep only the last two points
            self.update()
    
    def paintEvent(self, event):
        if len(self.points) == 2:
            painter = QPainter(self)
            painter.setPen(QPen(Qt.black, 2, Qt.SolidLine))
            painter.drawLine(self.points[0], self.points[1])

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LineDrawer()
    window.show()
    sys.exit(app.exec())
