from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QPushButton, QFrame, QLineEdit, QListWidget, 
                             QComboBox, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt

class AttributesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        # Model Section
        layout.addWidget(QLabel("<b>AI Model:</b>"))
        self.model_name_label = QLabel("No model selected")
        self.model_name_label.setStyleSheet("color: blue;")
        layout.addWidget(self.model_name_label)
        
        self.select_model_btn = QPushButton("Select Model (.pt / .xml)")
        layout.addWidget(self.select_model_btn)
        
        # Video Section
        layout.addWidget(QLabel("<b>Video File:</b>"))
        self.video_name_label = QLabel("No video selected")
        self.video_name_label.setStyleSheet("color: blue;")
        layout.addWidget(self.video_name_label)
        
        self.select_video_btn = QPushButton("Select Video (.mp4, .avi)")
        self.select_video_btn.setEnabled(False)
        layout.addWidget(self.select_video_btn)
        
        # Info Section
        layout.addWidget(QLabel("<b>Video Size:</b>"))
        self.video_size_label = QLabel("Not loaded")
        self.video_size_label.setStyleSheet("color: green;")
        layout.addWidget(self.video_size_label)
        
        layout.addStretch()
        
        self.reset_btn = QPushButton("🔄 Reset All Session")
        layout.addWidget(self.reset_btn)

class RegionSetupTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Enter 4 coordinates (x,y) or click on video:</b>"))
        
        self.coord_inputs = []
        for i in range(4):
            input_field = QLineEdit()
            input_field.setPlaceholderText(f"Point {i+1} (x, y)")
            layout.addWidget(input_field)
            self.coord_inputs.append(input_field)
            
        self.set_area_btn = QPushButton("Set Tracking Area")
        self.set_area_btn.setEnabled(False)
        layout.addWidget(self.set_area_btn)
        
        # Management Buttons
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("Add Region")
        self.undo_btn = QPushButton("Undo Last")
        self.clear_btn = QPushButton("Clear All")
        btn_layout.addWidget(self.add_btn)
        btn_layout.addWidget(self.undo_btn)
        btn_layout.addWidget(self.clear_btn)
        layout.addLayout(btn_layout)
        
        layout.addWidget(QLabel("<b>Active Regions:</b>"))
        self.regions_list = QListWidget()
        layout.addWidget(self.regions_list)
        
        help_text = QLabel("Click points on video to plot | ENTER to confirm | ESC to cancel")
        help_text.setStyleSheet("color: blue; font-style: italic; font-size: 10px;")
        layout.addWidget(help_text)

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
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Current FPS:</b>"))
        self.fps_label = QLabel("0.0")
        self.fps_label.setStyleSheet("color: purple; font-weight: bold; font-size: 32px;")
        layout.addWidget(self.fps_label)
        
        layout.addWidget(QLabel("<b>Total Vehicles Inside:</b>"))
        self.total_count_label = QLabel("0")
        self.total_count_label.setStyleSheet("color: darkorange; font-weight: bold; font-size: 36px;")
        layout.addWidget(self.total_count_label)
        
        layout.addWidget(QLabel("<b>Video Timestamp:</b>"))
        self.session_time_label = QLabel("00:00:00")
        self.session_time_label.setStyleSheet("color: green; font-weight: bold; font-size: 24px;")
        layout.addWidget(self.session_time_label)
        
        layout.addStretch()

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
