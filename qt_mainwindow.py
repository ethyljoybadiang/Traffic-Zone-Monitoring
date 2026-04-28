import sys
import os
import cv2
import torch
import time
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QStatusBar, QFileDialog, QMessageBox, QSlider, QLabel, QTableWidgetItem)
from PySide6.QtCore import Qt, QTimer, QPoint
from PySide6.QtGui import QIcon

from video_engine import VideoEngine
from qt_canvas import VideoCanvas
from qt_tabs import AttributesTab, RegionSetupTab, TrackingTab, DashboardTab, ResultsTab
from export_utils import export_log_to_pdf
from app_context import APPLICATION_PATH

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ALAM - Vehicle Counting System (Qt Version)")
        self.resize(1280, 800)
        
        # Initialize Core Engine
        self.video_engine = VideoEngine()
        
        # State Variables
        self.model = None
        self.video_capture = None
        self.regions = []
        self.points = []
        self.tracking = False
        self.frame_count = 0
        self.fps_time = time.time()
        self.fps_counter = 0
        self.video_name = ""
        self.width = 640
        self.height = 640
        self.allowed_vehicle_classes = self.video_engine.allowed_vehicle_classes
        self.region_counts = {}
        self.index = []
        
        self.setup_ui()
        
        # Timer for tracking loop
        self.tracking_timer = QTimer()
        self.tracking_timer.timeout.connect(self.update_frame)

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        
        # Left Side: Video Preview & Slider
        left_layout = QVBoxLayout()
        self.canvas = VideoCanvas()
        self.canvas.clicked.connect(self.handle_canvas_click)
        left_layout.addWidget(self.canvas, stretch=1)
        
        # Slider & Frame Info
        slider_layout = QHBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setEnabled(False)
        self.slider.valueChanged.connect(self.handle_slider_move)
        slider_layout.addWidget(self.slider)
        
        self.frame_info_label = QLabel("Frame: 0 / 0")
        slider_layout.addWidget(self.frame_info_label)
        left_layout.addLayout(slider_layout)
        
        main_layout.addLayout(left_layout, stretch=2)
        
        # Right Side: Tabs
        self.tabs = QTabWidget()
        self.tab_attributes = AttributesTab()
        self.tab_region = RegionSetupTab()
        self.tab_tracking = TrackingTab()
        self.tab_dashboard = DashboardTab()
        self.tab_results = ResultsTab()
        
        self.tabs.addTab(self.tab_attributes, "Attributes")
        self.tabs.addTab(self.tab_region, "Region Setup")
        self.tabs.addTab(self.tab_tracking, "Tracking")
        self.tabs.addTab(self.tab_dashboard, "Dashboard")
        self.tabs.addTab(self.tab_results, "Results")
        
        main_layout.addWidget(self.tabs, stretch=1)
        
        # Connect Signals
        self.tab_attributes.select_model_btn.clicked.connect(self.select_model)
        self.tab_attributes.select_video_btn.clicked.connect(self.select_video)
        self.tab_attributes.reset_btn.clicked.connect(self.reset_session)
        
        self.tab_region.add_btn.clicked.connect(self.confirm_plotted_points)
        self.tab_region.undo_btn.clicked.connect(self.undo_last_region)
        self.tab_region.clear_btn.clicked.connect(self.clear_all_regions)
        
        # Region List Context Menu
        self.tab_region.regions_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tab_region.regions_list.customContextMenuRequested.connect(self.show_region_context_menu)
        
        self.tab_tracking.start_btn.clicked.connect(self.start_tracking)
        self.tab_tracking.stop_btn.clicked.connect(self.stop_tracking)
        
        self.tab_results.export_btn.clicked.connect(self.export_log)
        self.tab_results.region_combo.currentIndexChanged.connect(self.update_results_table)
        
        # Status Bar
        self.statusBar().showMessage("Ready. Select a model to begin.")

    # --- Logic Methods (To be refined) ---
    
    def update_status(self, message):
        self.statusBar().showMessage(message)

    def select_model(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Model", "", 
            "All Supported Models (*.pt *.pth *.xml *.onnx *.engine *.hef);;PyTorch Models (*.pt *.pth);;OpenVINO Models (*.xml);;All Files (*.*)"
        )
        if not file_name: return
        
        self.update_status("Loading AI model... Please wait.")
        try:
            self.model, device_type = self.video_engine.load_model(file_name)
            self.index = list(self.model.names.values())
            
            model_name = os.path.basename(file_name)
            self.tab_attributes.model_name_label.setText(model_name)
            self.tab_attributes.select_video_btn.setEnabled(True)
            self.update_status(f"✓ Model loaded on {device_type.upper()}.")
            
            self.update_results_table()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load model: {str(e)}")
            self.update_status("✗ Model loading failed.")

    def select_video(self):
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Video File", "", "Video Files (*.mp4 *.avi);;All Files (*.*)"
        )
        if not file_name: return
        
        self.video_name = file_name
        self.video_capture = cv2.VideoCapture(file_name)
        
        if not self.video_capture.isOpened():
            QMessageBox.critical(self, "Error", "Failed to open video file.")
            return
            
        orig_w = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
        orig_h = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
        scale = 640.0 / max(orig_w, orig_h)
        self.width, self.height = int(orig_w * scale), int(orig_h * scale)
        
        self.tab_attributes.video_name_label.setText(os.path.basename(file_name))
        self.tab_attributes.video_size_label.setText(f"{self.width} x {self.height}")
        
        self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
        self.slider.setMaximum(self.total_frames)
        self.slider.setEnabled(True)
        
        self.tab_tracking.start_btn.setEnabled(True)
        self.tab_results.export_btn.setEnabled(True)
        
        self.refresh_preview()
        self.update_status("✓ Video loaded. Ready to set regions.")

    def refresh_preview(self):
        if not self.video_capture: return
        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.resize(frame, (self.width, self.height))
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.canvas.set_frame(frame)
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

    def handle_canvas_click(self, pos):
        self.points.append((pos.x(), pos.y()))
        self.canvas.set_points(self.points)
        self.update_status(f"Point {len(self.points)} added. ENTER to confirm.")

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts"""
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            # Only trigger if we are in the Region Setup tab and have points
            if self.tabs.currentIndex() == 1 and self.points:
                self.confirm_plotted_points()
        elif event.key() == Qt.Key_Escape:
            if self.points:
                self.points.clear()
                self.canvas.set_points([])
                self.update_status("Points cleared.")
        else:
            super().keyPressEvent(event)

    def confirm_plotted_points(self):
        if len(self.points) >= 3:
            self.regions.append(list(self.points))
            self.points.clear()
            self.canvas.set_points([])
            self.canvas.set_regions(self.regions)
            self.update_region_list()
            self.update_status(f"✓ Region {len(self.regions)} added.")
        else:
            QMessageBox.warning(self, "Incomplete", "Please plot at least 3 points.")

    def show_region_context_menu(self, pos):
        from PySide6.QtWidgets import QMenu
        item = self.tab_region.regions_list.itemAt(pos)
        if item:
            menu = QMenu()
            delete_action = menu.addAction("Delete Region")
            delete_action.triggered.connect(self.delete_selected_region)
            menu.exec(self.tab_region.regions_list.mapToGlobal(pos))

    def delete_selected_region(self):
        row = self.tab_region.regions_list.currentRow()
        if row >= 0:
            if QMessageBox.question(self, "Confirm", f"Delete Region {row+1}?") == QMessageBox.Yes:
                self.regions.pop(row)
                self.canvas.set_regions(self.regions)
                self.update_region_list()
                self.update_status(f"✓ Region {row+1} removed.")

    def update_region_list(self):
        self.tab_region.regions_list.clear()
        self.tab_results.region_combo.clear()
        self.tab_results.region_combo.addItem("All Regions")
        for i in range(len(self.regions)):
            self.tab_region.regions_list.addItem(f"Region {i+1}")
            self.tab_results.region_combo.addItem(f"Region {i+1}")

    def undo_last_region(self):
        if self.regions:
            self.regions.pop()
            self.canvas.set_regions(self.regions)
            self.update_region_list()

    def clear_all_regions(self):
        self.regions.clear()
        self.canvas.set_regions([])
        self.update_region_list()

    def start_tracking(self):
        if not self.regions:
            QMessageBox.warning(self, "No Regions", "Add at least one region first.")
            return
            
        if self.tracking:
            self.tracking = False
            self.tracking_timer.stop()
            self.tab_tracking.start_btn.setText("▶ Resume Tracking")
            self.tab_tracking.status_label.setText("⏸ Paused")
        else:
            self.tracking = True
            self.tracking_timer.start(2)
            self.tab_tracking.start_btn.setText("⏸ Pause Tracking")
            self.tab_tracking.status_label.setText("🟢 Tracking")
            self.tab_tracking.stop_btn.setEnabled(True)

    def stop_tracking(self):
        self.tracking = False
        self.tracking_timer.stop()
        self.tab_tracking.start_btn.setText("▶ Start Tracking")
        self.tab_tracking.status_label.setText("⚪ Stopped")
        if self.video_capture:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.refresh_preview()

    def update_frame(self):
        if not self.tracking or not self.video_capture: return
        
        ret, frame = self.video_capture.read()
        if ret:
            frame = cv2.resize(frame, (self.width, self.height))
            
            # Tracking logic
            annotated_frame, self.region_counts = self.video_engine.process_frame_tracking(
                frame, self.regions, self.model.names
            )
            
            # Dashboard Updates
            self.fps_counter += 1
            curr_time = time.time()
            if curr_time - self.fps_time >= 1.0:
                fps = self.fps_counter / (curr_time - self.fps_time)
                self.tab_dashboard.fps_label.setText(f"{fps:.1f}")
                self.fps_counter = 0
                self.fps_time = curr_time
            
            total_inside = sum(sum(c.values()) for c in self.region_counts.values())
            self.tab_dashboard.total_count_label.setText(str(total_inside))
            
            timestamp_ms = self.video_capture.get(cv2.CAP_PROP_POS_MSEC)
            total_seconds = timestamp_ms / 1000.0
            h, m = divmod(int(total_seconds), 3600)
            m, s = divmod(m, 60)
            self.tab_tracking.timestamp_label.setText(f"{h:02d}:{m:02d}:{s:02d}.{int((total_seconds % 1) * 100):02d}")
            self.tab_dashboard.session_time_label.setText(f"{h:02d}:{m:02d}:{s:02d}")
            
            # Display
            rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            self.canvas.set_frame(rgb_image)
            self.update_results_table()
            
            # Slider
            curr_frame = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES))
            self.slider.setValue(curr_frame)
            self.frame_info_label.setText(f"Frame: {curr_frame} / {self.total_frames}")
        else:
            self.stop_tracking()

    def update_results_table(self):
        """Update pivot table: Vehicles vs Regions"""
        if not self.index: return
        
        current_filter = self.tab_results.region_combo.currentText()
        if current_filter == "All Regions":
            active_indices = list(range(len(self.regions)))
        else:
            try:
                idx = int(current_filter.split()[-1]) - 1
                active_indices = [idx]
            except:
                active_indices = list(range(len(self.regions)))
                
        # Update Columns
        headers = ["Vehicle"] + [f"Region {i+1}" for i in active_indices]
        self.tab_results.table.setColumnCount(len(headers))
        self.tab_results.table.setHorizontalHeaderLabels(headers)
        
        # Populate
        self.tab_results.table.setRowCount(0)
        for vehicle in self.index:
            row = self.tab_results.table.rowCount()
            self.tab_results.table.insertRow(row)
            self.tab_results.table.setItem(row, 0, QTableWidgetItem(vehicle))
            
            for col_idx, region_idx in enumerate(active_indices, 1):
                count = 0
                if region_idx in self.region_counts:
                    count = self.region_counts[region_idx].get(vehicle.lower(), 0)
                self.tab_results.table.setItem(row, col_idx, QTableWidgetItem(str(count)))

    def handle_slider_move(self, value):
        if not self.tracking and self.video_capture:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, value)
            self.refresh_preview()

    def export_log(self):
        """Export tracking log as PDF using export_utils"""
        if not self.video_name or not self.model:
            QMessageBox.warning(self, "Error", "Model or Video not loaded.")
            return
            
        try:
            # Collect data from Table
            table_data = []
            for row in range(self.tab_results.table.rowCount()):
                row_values = []
                for col in range(self.tab_results.table.columnCount()):
                    item = self.tab_results.table.item(row, col)
                    row_values.append(item.text() if item else "")
                table_data.append(row_values)
                
            # Get current headers
            headers = [self.tab_results.table.horizontalHeaderItem(i).text() for i in range(self.tab_results.table.columnCount())]
            
            c_status = self.tab_tracking.status_label.text()
            c_timestamp = self.tab_tracking.timestamp_label.text()
            
            log_file = export_log_to_pdf(table_data, APPLICATION_PATH, headers=headers, status=c_status, timestamp=c_timestamp)
            
            self.tab_results.log_file_label.setText(log_file)
            self.update_status("✓ Log exported successfully!")
            QMessageBox.information(self, "Success", f"Log exported: {log_file}")
            
        except Exception as e:
            print(f"Export Error: {e}")
            self.update_status("✗ Export failed.")
            QMessageBox.critical(self, "Error", f"Error exporting log: {str(e)}")

    def reset_session(self):
        self.stop_tracking()
        self.model = None
        self.video_capture = None
        self.regions = []
        self.points = []
        self.canvas.set_frame(None)
        self.canvas.set_regions([])
        self.update_region_list()
        self.tab_attributes.model_name_label.setText("No model selected")
        self.tab_attributes.video_name_label.setText("No video selected")
        self.update_status("Session reset.")

if __name__ == "__main__":
    from PySide6.QtWidgets import QLabel # Fix for the missing QLabel import in setup_ui
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
