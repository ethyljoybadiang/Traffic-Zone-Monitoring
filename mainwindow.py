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
        self.region_names = {}  # {region_idx: custom_name}
        self.points = []
        self.tracking = False
        self.timer_id = None
        self.width = 640
        self.height = 640
        self.canvas_width = None
        self.canvas_height = None
        self.allowed_vehicle_classes = ['car', 'truck', 'bus', 'motorcycle', 'bicycle']
        self.region_colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
        self.region_counts = {}
        self.vehicle_count = {}
        self.file_name = None
        self.video_name = None
        self.index = None
        self.vehicles = None
        self.hover_point = None
        self.is_hovering_video = False
        self.frame_count = 0
        self.fps_counter = 0
        self.fps_time = time.time()
        self.photo = None
        self.is_manual_seek = False
        self.region_filter = tk.StringVar(value="All Regions")
        
        # Setup UI components from startup module
        startup.setup_ui(self)
        
        # Global Hotkeys (Must be placed after UI setup so events are caught gracefully)
        self.bind("<MouseWheel>", self.on_mousewheel)
        self.bind_all("<Return>", lambda e: self.set_line())
        self.bind_all("<Escape>", lambda e: self.cancel_plotting())
        
        # Initial state setup
        self.initialize_table()
    
    initialize_table = startup.initialize_table

if __name__ == "__main__":
    print('Starting ALAM Application')
    app = MainWindow()
    app.mainloop()