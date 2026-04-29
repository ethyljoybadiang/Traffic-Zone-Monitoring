from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QLineEdit, QListWidget, 
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QGridLayout)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont

class DonutChartWidget(QWidget):
    """Custom widget to display vehicle distribution as a donut chart."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = {} # {VehicleName: Count}
        self.colors = {
            'car': QColor('#0984e3'),
            'motorcycle': QColor('#74b9ff'),
            'truck': QColor('#00a8ff'),
            'bus': QColor('#487eb0'),
            'bicycle': QColor('#40739e'),
            'person': QColor('#192a56')
        }
        self.default_color = QColor('#dcdde1')
        self.setMinimumSize(180, 180) # Reduced size

    def set_data(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Adjust rect for thinner ring and smaller widget
        thickness = 18
        margin = 15
        rect = QRectF(margin, margin, self.width() - 2*margin, self.height() - 2*margin)
        
        total = sum(self.data.values())
        
        # Draw Background Ring
        pen = QPen(QColor('#f0f0f0'), thickness)
        painter.setPen(pen)
        painter.drawEllipse(rect)
        
        if total == 0:
            painter.setPen(QColor('#999999'))
            painter.setFont(QFont("Arial", 10))
            painter.drawText(rect, Qt.AlignCenter, "No Data")
            return
            
        start_angle = 90 * 16
        
        for vehicle, count in self.data.items():
            if count == 0: continue
            
            span_angle = -int((count / total) * 360 * 16)
            
            color = self.colors.get(vehicle.lower(), self.default_color)
            pen = QPen(color, thickness)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            
            painter.drawArc(rect, start_angle, span_angle)
            start_angle += span_angle
            
        # Draw Center Text
        painter.setPen(QColor('#333333'))
        painter.setFont(QFont("Arial", 22, QFont.Bold))
        painter.drawText(QRectF(rect.x(), rect.y() - 8, rect.width(), rect.height()), 
                         Qt.AlignCenter, f"{total}")
        
        painter.setFont(QFont("Arial", 8))
        painter.setPen(QColor('#888888'))
        painter.drawText(QRectF(rect.x(), rect.y() + 20, rect.width(), rect.height()), 
                         Qt.AlignCenter, "Total Objects")


class SetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # --- Model & Video Section ---
        group_style = "font-weight: bold; color: #333;"
        
        layout.addWidget(QLabel("<b>AI Model Selection</b>"))
        self.model_name_label = QLabel("No model selected")
        self.model_name_label.setStyleSheet("color: blue; padding: 5px;")
        layout.addWidget(self.model_name_label)
        
        self.select_model_btn = QPushButton("Select Model (.pt / .xml)")
        layout.addWidget(self.select_model_btn)
        
        layout.addWidget(QLabel("<b>Video File Selection</b>"))
        self.video_name_label = QLabel("No video selected")
        self.video_name_label.setStyleSheet("color: blue; padding: 5px;")
        layout.addWidget(self.video_name_label)
        
        self.select_video_btn = QPushButton("Select Video (.mp4, .avi)")
        self.select_video_btn.setEnabled(False)
        layout.addWidget(self.select_video_btn)
        
        self.video_size_label = QLabel("Not loaded")
        self.video_size_label.setStyleSheet("color: green; font-size: 10px;")
        layout.addWidget(self.video_size_label)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # --- Region Management Section ---
        layout.addWidget(QLabel("<b>Region Management</b>"))
        
        # Management Buttons
        btn_layout = QHBoxLayout()
        self.undo_btn = QPushButton("Undo Last")
        self.clear_btn = QPushButton("Clear All")
        btn_layout.addWidget(self.undo_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        self.regions_list = QListWidget()
        layout.addWidget(self.regions_list)
        
        help_text = QLabel("Click on video to plot | ENTER to confirm | CTRL+Z to undo")
        help_text.setStyleSheet("color: blue; font-style: italic; font-size: 10px;")
        layout.addWidget(help_text)
        
        layout.addStretch()
        
        self.reset_btn = QPushButton("🔄 Reset All Session")
        layout.addWidget(self.reset_btn)

class TrackingTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        self.start_btn = QPushButton("▶ Start Tracking")
        self.start_btn.setEnabled(False)
        self.start_btn.setMinimumHeight(40)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ Stop Tracking")
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        
        layout.addWidget(QLabel("<b>Tracking Status:</b>"))
        self.status_label = QLabel("⚪ Idle")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.status_label)
        
        layout.addWidget(QLabel("<b>Timestamp:</b>"))
        self.timestamp_label = QLabel("00:00:00.00")
        self.timestamp_label.setStyleSheet("color: blue; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.timestamp_label)
        
        layout.addStretch()

class DashboardTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        
        # 1. Top Section: Stats & Donut Chart
        main_layout.addWidget(QLabel("<b>Real-time Performance</b>"))
        
        stats_layout = QHBoxLayout()
        
        # Left side of top: FPS and global info
        info_layout = QVBoxLayout()
        
        fps_frame = QFrame()
        fps_frame.setStyleSheet("background: #f8f9fa; border-radius: 10px; padding: 10px;")
        fps_vbox = QVBoxLayout(fps_frame)
        fps_vbox.addWidget(QLabel("Current FPS"))
        self.fps_label = QLabel("0.0")
        self.fps_label.setStyleSheet("color: #6c5ce7; font-weight: bold; font-size: 24px;")
        fps_vbox.addWidget(self.fps_label)
        info_layout.addWidget(fps_frame)
        
        time_frame = QFrame()
        time_frame.setStyleSheet("background: #f8f9fa; border-radius: 10px; padding: 10px;")
        time_vbox = QVBoxLayout(time_frame)
        time_vbox.addWidget(QLabel("Session Time"))
        self.session_time_label = QLabel("00:00:00")
        self.session_time_label.setStyleSheet("color: #00b894; font-weight: bold; font-size: 24px;")
        time_vbox.addWidget(self.session_time_label)
        info_layout.addWidget(time_frame)
        
        stats_layout.addLayout(info_layout)
        
        # Right side of top: Donut Chart & Legend
        self.chart_container = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_container)
        self.chart_layout.setContentsMargins(0, 0, 0, 0)
        self.chart_layout.setSpacing(0)
        
        self.chart = DonutChartWidget()
        self.chart_layout.addWidget(self.chart, alignment=Qt.AlignCenter)
        
        # Legend Section (Vertical list)
        self.legend_widget = QWidget()
        self.legend_vbox = QVBoxLayout(self.legend_widget)
        self.legend_vbox.setContentsMargins(0, 5, 0, 0)
        self.legend_vbox.setSpacing(2)
        self.legend_vbox.setAlignment(Qt.AlignCenter)
        self.chart_layout.addWidget(self.legend_widget)
        
        stats_layout.addWidget(self.chart_container)
        main_layout.addLayout(stats_layout)
        
        main_layout.addWidget(QLabel("<b>Region Breakdown</b>"))
        
        # 2. Bottom Section: Region Tiles (Scrollable)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background: transparent;")
        
        self.tiles_container = QWidget()
        self.tiles_layout = QVBoxLayout(self.tiles_container)
        self.tiles_layout.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(self.tiles_container)
        
        main_layout.addWidget(self.scroll)
        
        self.total_count_label = QLabel("0") # Keep reference for compatibility

    def update_legend(self, data):
        """Update the chart legend with colors and percentages."""
        # Clear legend
        while self.legend_vbox.count():
            item = self.legend_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        total = sum(data.values())
        if total == 0: return
        
        for vehicle, count in data.items():
            if count == 0: continue
            
            perc = (count / total) * 100
            color = self.chart.colors.get(vehicle.lower(), self.chart.default_color)
            
            # Row container to keep dot and text together
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            row_layout.setAlignment(Qt.AlignCenter)
            
            # Color indicator
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color.name()}; font-size: 14px;")
            row_layout.addWidget(dot)
            
            # Label
            label = QLabel(f"{vehicle.capitalize()}: {count} ({perc:.1f}%)")
            label.setStyleSheet("font-size: 10px; color: #555;")
            row_layout.addWidget(label)
            
            self.legend_vbox.addWidget(row)

class RegionTile(QFrame):
    """Small card showing stats for a specific region."""
    def __init__(self, region_name, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            RegionTile {
                background-color: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                padding: 10px;
                margin-bottom: 5px;
            }
        """)
        layout = QHBoxLayout(self)
        
        # Left: Region Name & Total
        left_layout = QVBoxLayout()
        self.name_label = QLabel(f"<b>{region_name}</b>")
        self.name_label.setStyleSheet("font-size: 14px; color: #2d3436;")
        left_layout.addWidget(self.name_label)
        
        self.total_label = QLabel("Total: 0")
        self.total_label.setStyleSheet("color: #636e72;")
        left_layout.addWidget(self.total_label)
        layout.addLayout(left_layout)
        
        layout.addStretch()
        
        # Right: Vehicle Breakdown (Mini Grid)
        self.breakdown_label = QLabel("")
        self.breakdown_label.setStyleSheet("color: #0984e3; font-size: 11px;")
        layout.addWidget(self.breakdown_label)

    def update_stats(self, total, breakdown):
        self.total_label.setText(f"Total: {total}")
        # breakdown is {vehicle: count}
        items = [f"{v.capitalize()}: {c}" for v, c in breakdown.items() if c > 0]
        self.breakdown_label.setText(" | ".join(items) if items else "No objects")


class ResultsTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Filter Section
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Region:"))
        self.region_combo = QComboBox()
        self.region_combo.addItem("All Regions")
        filter_layout.addWidget(self.region_combo)
        layout.addLayout(filter_layout)
        
        # Results Table (Pivot View)
        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Vehicle"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)
        
        # Export Section
        export_layout = QHBoxLayout()
        self.export_btn = QPushButton("📄 Export Log (PDF)")
        self.export_btn.setEnabled(False)
        export_layout.addWidget(self.export_btn)
        
        self.log_file_label = QLabel("Not exported")
        self.log_file_label.setStyleSheet("color: green;")
        export_layout.addWidget(self.log_file_label)
        layout.addLayout(export_layout)
