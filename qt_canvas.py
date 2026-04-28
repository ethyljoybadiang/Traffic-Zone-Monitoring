from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QImage, QPixmap, QColor, QPolygon, QPen, QBrush
from PySide6.QtCore import Qt, QPoint, Signal

class VideoCanvas(QWidget):
    """Custom widget for high-performance video rendering and region plotting."""
    clicked = Signal(QPoint)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.image = None
        self.regions = []
        self.points = []
        self.hover_point = None
        self.region_colors = [
            QColor(255, 0, 0, 100),   # Red
            QColor(0, 255, 0, 100),   # Green
            QColor(0, 0, 255, 100),   # Blue
            QColor(255, 255, 0, 100), # Yellow
            QColor(255, 0, 255, 100), # Magenta
            QColor(0, 255, 255, 100)  # Cyan
        ]
        self.setMouseTracking(True)
        self.setCursor(Qt.CrossCursor)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_frame(self, frame_data):
        """Update the current video frame."""
        if frame_data is None:
            return
            
        h, w, c = frame_data.shape
        bytes_per_line = c * w
        self.image = QImage(frame_data.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.update()

    def set_regions(self, regions):
        self.regions = regions
        self.update()

    def set_points(self, points):
        self.points = points
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 1. Draw Video Frame (scaled to fit)
        if self.image:
            scaled_pixmap = QPixmap.fromImage(self.image).scaled(
                self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            
            # Center the pixmap
            self.offset_x = (self.width() - scaled_pixmap.width()) // 2
            self.offset_y = (self.height() - scaled_pixmap.height()) // 2
            painter.drawPixmap(self.offset_x, self.offset_y, scaled_pixmap)
            
            # Store scaling factors for coordinate mapping
            self.scale_x = scaled_pixmap.width() / self.image.width()
            self.scale_y = scaled_pixmap.height() / self.image.height()
        else:
            painter.fillRect(self.rect(), Qt.black)
            return

        # 2. Draw Confirmed Regions
        for i, region_obj in enumerate(self.regions):
            points = region_obj['points']
            name = region_obj['name']
            
            color = self.region_colors[i % len(self.region_colors)]
            pen = QPen(color.lighter(), 2)
            brush = QBrush(color)
            painter.setPen(pen)
            painter.setBrush(brush)
            
            polygon = QPolygon([
                QPoint(int(p[0] * self.scale_x + self.offset_x), 
                       int(p[1] * self.scale_y + self.offset_y))
                for p in points
            ])
            painter.drawPolygon(polygon)
            
            # Label
            if len(points) > 0:
                painter.setPen(Qt.white)
                painter.drawText(polygon[0] + QPoint(0, -10), name)

        # 3. Draw Active Plotted Points
        if self.points:
            painter.setPen(QPen(Qt.red, 2))
            painter.setBrush(QBrush(Qt.red))
            for pt in self.points:
                px = int(pt[0] * self.scale_x + self.offset_x)
                py = int(pt[1] * self.scale_y + self.offset_y)
                painter.drawEllipse(QPoint(px, py), 4, 4)

        # 4. Draw Hover Point / Preview Line
        if self.hover_point and self.points:
            painter.setPen(QPen(Qt.yellow, 1, Qt.DashLine))
            last_pt = self.points[-1]
            p1 = QPoint(int(last_pt[0] * self.scale_x + self.offset_x), 
                        int(last_pt[1] * self.scale_y + self.offset_y))
            p2 = QPoint(int(self.hover_point[0] * self.scale_x + self.offset_x), 
                        int(self.hover_point[1] * self.scale_y + self.offset_y))
            painter.drawLine(p1, p2)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Map back to original video coordinates
            if hasattr(self, 'scale_x'):
                vx = (event.x() - self.offset_x) / self.scale_x
                vy = (event.y() - self.offset_y) / self.scale_y
                if 0 <= vx <= self.image.width() and 0 <= vy <= self.image.height():
                    self.clicked.emit(QPoint(int(vx), int(vy)))

    def mouseMoveEvent(self, event):
        if hasattr(self, 'scale_x'):
            vx = (event.x() - self.offset_x) / self.scale_x
            vy = (event.y() - self.offset_y) / self.scale_y
            self.hover_point = (vx, vy)
            self.update()

