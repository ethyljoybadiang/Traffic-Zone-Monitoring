# This Python file uses the following encoding: utf-8
print(">>> ALAM Application Starting...")
import sys
import os

# specifically to avoid the "matplotlib caching" hang during bundling.
try:
    import logging
    logging.getLogger('matplotlib.font_manager').disabled = True
    # Pre-emptively set markers to avoid some scans
    import matplotlib
    matplotlib.use('Agg') 
    print(">>> Matplotlib initialized (Agg backend)")
except Exception as e:
    print(f">>> Matplotlib patch failed: {e}")

print(">>> Importing core libraries...")
import cv2
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
from datetime import datetime
import torch
import schedule
import traceback
from PIL import Image, ImageTk, ImageDraw
import numpy as np

from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

from video_engine import VideoEngine
from ui_tabs import setup_attributes_tab, setup_region_tab, setup_tracking_tab, setup_results_tab
from export_utils import export_log_to_pdf
import initial_startup as startup
from app_context import APPLICATION_PATH
from regions import RegionsMixin
from selection import SelectionMixin
from tracking import TrackingMixin
from export_utils import ExportMixin

print("Frozen:", getattr(sys, 'frozen', False))
print("Executable:", sys.executable)
print("MEIPASS:", getattr(sys, '_MEIPASS', 'N/A'))

class MainWindow(tk.Tk,RegionsMixin,VideoEngine,SelectionMixin,TrackingMixin,ExportMixin):
    def __init__(self):
        super().__init__()        # Window configuration
        self.title("ALAM - Vehicle Counting System (Tkinter Version)")
        self.geometry("1280x800")
        self.resizable(True, True)
        self.configure(bg="#dcdcdc")
        
        # Initialize core engine
        self.video_engine = VideoEngine()
        
        # Initialize state variables
        self.model = None
        self.video_capture = None
        self.regions = []
        self.points = []
        self.tracking = False
        self.timer_id = None
        self.width = 640
        self.height = 640
        self.canvas_width = None
        self.canvas_height = None
        self.allowed_vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']
        self.region_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        
        # Setup UI components from startup module
        startup.setup_ui(self)
        
        # Global Hotkeys (Must be placed after UI setup so events are caught gracefully)
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Return>", lambda e: self.set_line())
        self.bind_all("<Escape>", lambda e: self.cancel_plotting())
        
        # Initial state setup
        self.initialize_table()
    
    # Link startup methods to MainWindow class
    initialize_table = startup.initialize_table

    
    
    
    # def update_table_data(self):
    #     """Update the results table with per-region counts (filtered by class and region)"""
    #     if not self.region_counts:
    #         return
        
    #     # Clear existing table
    #     for item in self.table.get_children():
    #         self.table.delete(item)
        
    #     # Get filter selection
    #     current_filter = self.region_filter.get()
        
    #     # Determine which regions to display
    #     if current_filter == "All Regions":
    #         region_indices = sorted(self.region_counts.keys())
    #     else:
    #         # Extract region number from "Region X"
    #         try:
    #             region_num = int(current_filter.split()[-1]) - 1
    #             region_indices = [region_num] if region_num in self.region_counts else []
    #         except (ValueError, IndexError):
    #             region_indices = sorted(self.region_counts.keys())
        
    #     # Populate table with per-region data (only allowed vehicle classes)
    #     for region_idx in region_indices:
    #         if region_idx not in self.region_counts:
    #             continue
                
    #         classwise_count = self.region_counts[region_idx]
    #         region_label = f"Region {region_idx + 1}"
    #         region_color = self.region_colors[region_idx % len(self.region_colors)]
            
    #         # Only display allowed vehicle classes
    #         for vehicle in self.index:
    #             vehicle_lower = vehicle.lower()
    #             if vehicle_lower not in self.allowed_vehicle_classes:
    #                 continue
                    
    #             in_count = 0
    #             out_count = 0
    #             inside_count = 0
                
    #             # Check if we have counts for this vehicle in this region
    #             if vehicle_lower in classwise_count:
    #                 count_value = classwise_count[vehicle_lower]
    #                 if isinstance(count_value, dict):
    #                     # Legacy support just in case
    #                     in_count = int(count_value.get('IN', 0))
    #                     out_count = int(count_value.get('OUT', 0))
    #                 else:
    #                     # NEW optimized logic provides total inside count
    #                     inside_count = int(count_value)
                
    #             iid = self.table.insert("", tk.END, values=(region_label, vehicle, in_count, out_count, inside_count))
                
    #             # Apply tag with region color for highlighting
    #             tag_name = f"region_{region_idx}"
    #             self.table.tag_configure(tag_name, background='white')  # Light blue, green, etc. based on region
    #             self.table.item(iid, tags=(tag_name,))
    
    # def export_log(self):
    #     """Export tracking log as PDF using ExportUtils"""
    #     self.update_status("Exporting log...")
        
    #     if not self.file_name or not self.model:
    #         messagebox.showerror("Error", "Attributes not loaded.")
    #         self.update_status("✗ No tracking data to export.")
    #         return
        
    #     try:
    #         # Collect data from Table
    #         table_rows = []
    #         for item in self.table.get_children():
    #             table_rows.append(self.table.item(item)['values'])
            
    #         c_status = self.status_var.get() if hasattr(self, 'status_var') else "N/A"
    #         c_timestamp = self.timestamp_var.get() if hasattr(self, 'timestamp_var') else "00:00:00.00"
            
    #         log_file = export_log_to_pdf(table_rows, APPLICATION_PATH, status=c_status, timestamp=c_timestamp)
            
    #         if hasattr(self, 'log_file_var'):
    #             self.log_file_var.set(log_file)
    #         self.update_status("✓ Log exported successfully!")
    #         messagebox.showinfo("Success", f"Log exported:\n{log_file}")
            
    #     except Exception as e:
    #         print(f"Export Error: {e}")
    #         self.update_status("✗ Export failed.")
    #         messagebox.showerror("Error", f"Error exporting log: {str(e)}")
    
    # def update_status(self, message):
    #     """Update status bar message"""
    #     self.status_var.set(message)
    #     self.update_idletasks()
    
    # def on_slider_move(self, value):
    #     """Handle manual video seeking via slider"""
    #     if not self.video_capture or self.is_manual_seek:
    #         return
            
    #     # If tracking is active, pausing might be better, 
    #     # but let's allow seeking and see.
    #     frame_idx = int(float(value))
    #     self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    #     self.frame_count = frame_idx  # Keep internal counter synchronized
    #     self.refresh_video_display(reset=False)
        
    #     if hasattr(self, 'frame_info_var') and hasattr(self, 'total_frames'):
    #         self.frame_info_var.set(f"Frame: {frame_idx} / {self.total_frames}")
            
    #     self.update_status(f"Seeked to frame {frame_idx}")

    # def on_mousewheel(self, event):
    #     """Handle mouse wheel events"""
    #     pass

if __name__ == "__main__":
    print('Starting ALAM Application')
    app = MainWindow()
    app.mainloop()