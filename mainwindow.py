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
from regions import RegionsMixin

# EXECUTABLE APPLICATION
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(__file__)

APPLICATION_PATH = application_path

print("Frozen:", getattr(sys, 'frozen', False))
print("Executable:", sys.executable)
print("MEIPASS:", getattr(sys, '_MEIPASS', 'N/A'))

class MainWindow(tk.Tk,RegionsMixin):
    def __init__(self):
        super().__init__()
        # Window configuration
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


    # SELECTION & LOADING    
    def select_model(self):
        """Select and load AI model"""
        file_name = filedialog.askopenfilename(
            title="Select Model",
            filetypes=[("All Supported Models", "*.pt *.pth *.xml"), ("PyTorch Models", "*.pt *.pth"), ("OpenVINO Models", "*.xml"), ("All Files", "*.*")]
        )
        
        if not file_name:
            self.update_status("Model selection cancelled.")
            return
        
        self.update_status("Loading AI model... Please wait.")
        try:
            self.model, device_type = self.video_engine.load_model(file_name)
            
            if device_type == 'gpu':
                self.update_status("✓ Model loaded on GPU.")
                print(f"\n{'='*40}")
                print(f"NOTICE: GPU is being used! (CUDA: {torch.cuda.get_device_name(0)})")
                print(f"{'='*40}\n")
            else:
                self.update_status(f"✓ Model loaded on {device_type.upper()}.")
            
            self.file_name = file_name
            model_name = os.path.basename(file_name)
            self.model_name_var.set(model_name)
            self.ai_model_var.set(model_name)
            
            # Initialize vehicles dictionary
            self.vehicles = {value: 0 for key, value in self.model.names.items()}
            self.initialize_table()
            
            # Enable video selection
            self.select_video_btn.config(state=tk.NORMAL)
            self.update_status("✓ Model loaded. Now select a video.")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load model: {str(e)}")
            self.update_status("✗ Model loading failed.")
    
    # Link startup methods to MainWindow class
    initialize_table = startup.initialize_table

    # SELECTION & LOADING
    def select_video(self):
        """Select and load video file"""
        self.update_status("Please select a video file...")
        video_name = filedialog.askopenfilename(
            title="Select Video File",
            filetypes=[("Video Files", "*.mp4 *.avi"), ("All Files", "*.*")]
        )
        
        if not video_name:
            self.update_status("Video selection cancelled.")
            return
        
        self.video_name = video_name
        video_basename = os.path.basename(video_name)
        self.video_name_var.set(video_basename)
        
        self.update_status("Loading video...")
        
        try:
            self.video_capture = cv2.VideoCapture(self.video_name)
            
            orig_w = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            orig_h = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            # Scale proportionally so the largest dimension is 640
            scale = 640.0 / max(orig_w, orig_h)
            self.width = int(orig_w * scale)
            self.height = int(orig_h * scale)
            
            self.video_size_var.set(f"{self.width} x {self.height} (Proportional)")
            
            if not self.video_capture.isOpened():
                messagebox.showerror("Error", "Failed to open the video file.")
                self.update_status("✗ Video load failed.")
            else:
                self.update_status("✓ Video loaded. Standardized to 640x640.")
                self.refresh_video_display(reset=True)
                messagebox.showinfo(
                    "Information",
                    f"{video_basename} loaded successfully.\n\nSet polygon for vehicle counting by clicking 4 coordinates on the video."
                )
                
                self.vehicle_count = {}
                self.regions = []
                
                # Initialize Slider
                self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
                self.video_slider.config(to=self.total_frames, state=tk.NORMAL)
                self.slider_var.set(0)
                if hasattr(self, 'frame_info_var'):
                    self.frame_info_var.set(f"Frame: 0 / {self.total_frames}")
                
                self.export_btn.config(state=tk.NORMAL)
                self.update_regions_listbox()
                if hasattr(self, 'notebook'):
                    self.notebook.select(1) # Auto switch to Region Setup
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load video: {str(e)}")
            self.update_status("✗ Video load failed.")
    
    # VIDEO WINDOW
    def refresh_video_display(self, reset=False):
        """Display a frame of video for region setup without necessarily resetting to 0"""
        if not self.video_capture:
            return
            
        if reset:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        # Save current position
        curr_pos = self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)
        
        ret, frame = self.video_capture.read()
        if ret:
            # Resize proportionally to ensure the maximum dimension is 640
            frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
            rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.display_frame_on_canvas(rgb_image)
            
        # Restore position
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, curr_pos)


    def start_tracking(self):
        """Start or Pause video tracking"""
        if not self.video_capture or not self.model:
            messagebox.showerror("Error", "Load model and video first.")
            self.update_status("✗ Model or video not loaded.")
            return
        
        if not self.regions:
            messagebox.showerror("Error", "Add at least one tracking region first.")
            self.update_status("✗ No tracking regions defined.")
            return

        if self.tracking:
            # We are currently tracking, so PAUSE
            self.tracking = False
            self.status_icon_var.set("⏸ Paused")
            self.start_btn.config(text="▶ Resume Tracking")
            self.update_status("⏸ Tracking paused.")
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            return
        
        # We are starting or resuming
        current_status = self.status_icon_var.get()
        is_fresh_start = (current_status == "⚪ Idle" or current_status == "⚪ Stopped")
        
        self.update_status("▶ Tracking started...")
        self.status_icon_var.set("🟢 Tracking")
        self.tracking = True
        
        self.set_line_btn.config(state=tk.DISABLED)
        self.select_video_btn.config(state=tk.DISABLED)
        self.start_btn.config(text="⏸ Pause Tracking")
        self.stop_btn.config(state=tk.NORMAL)
        
        if is_fresh_start:
            # Ensure video_capture is available and initialized
            if not self.video_capture or not self.video_capture.isOpened():
                try:
                    self.video_capture = cv2.VideoCapture(self.video_name)
                except Exception as e:
                    messagebox.showerror("Error", f"Failed to re-initialize video: {str(e)}")
                    return

            # Reset video to start
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.frame_count = 0  # Reset frame counter
            
            if hasattr(self, 'notebook'):
                self.notebook.select(3) # Auto switch to Dashboard Tab (Index 3)

        self.prev_frame_time = time.time()
        self.fps_time = time.time()
        self.fps_counter = 0
        
        self.update_frame()
        self.update_status("▶ Tracking active.")
    
    def stop_tracking(self):
        """Stop video tracking and reset to beginning"""
        self.update_status("⏹ Stopping tracking...")
        self.tracking = False
        
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        
        self.status_icon_var.set("⚪ Stopped")
        
        self.set_line_btn.config(state=tk.NORMAL)
        self.select_video_btn.config(state=tk.NORMAL)
        self.start_btn.config(text="▶ Start Tracking", state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        
        # Reset video to first frame for preview
        if self.video_capture:
            self.refresh_video_display(reset=True)
            self.slider_var.set(0)
            
        self.update_status("✓ Tracking stopped and reset. Ready for new start.")

    def reset_session(self):
        """Completely reset the application state"""
        if not messagebox.askyesno("Confirm Reset", "Are you sure you want to reset the entire session?\nThis will clear the model, video, and all counts."):
            return
            
        self.update_status("Resetting session...")
        self.tracking = False
        
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
            
        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None
            
        # Reset variables
        self.model = None
        self.video_name = None
        self.regions = []
        self.points = []
        self.counters = {}
        self.vehicle_count = {}
        self.region_counts = {}
        
        # Reset UI Labels
        self.model_name_var.set("No model selected")
        self.ai_model_var.set("Not loaded")
        self.video_name_var.set("No video selected")
        self.video_size_var.set("Not loaded")
        self.status_icon_var.set("⚪ Idle")
        self.timestamp_var.set("00:00:00.00")
        self.update_regions_listbox()
        self.update_region_filter_combobox()
        
        # Clear Table
        for item in self.table.get_children():
            self.table.delete(item)
            
        # Clear Canvas
        self.video_canvas.delete("all")
        self.photo = None
        
        # Reset Button States
        self.select_video_btn.config(state=tk.DISABLED)
        self.set_line_btn.config(state=tk.DISABLED)
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.DISABLED)
        self.export_btn.config(state=tk.DISABLED)
        
        self.update_status("✓ Session reset complete.")
    
    def update_frame(self):
        """Update frame during tracking with delegated processing"""
        if not self.tracking or not self.video_capture:
            return
        
        try:
            # FPS and frame management
            self.frame_count += 1
            if self.frame_count % 2 == 0:
                self.video_capture.grab()
                if self.tracking:
                    self.timer_id = self.after(2, self.update_frame)
                return
            
            ret, frame = self.video_capture.read()
            if ret and frame is not None and frame.size > 0:
                # Standardize frame
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)
                
                # Delegate tracking logic to VideoEngine
                annotated_frame, self.region_counts = self.video_engine.process_frame_tracking(
                    frame, self.regions, self.model.names
                )
                
                # Update timestamp
                timestamp_ms = self.video_capture.get(cv2.CAP_PROP_POS_MSEC)
                total_seconds = timestamp_ms / 1000
                hours, remainder = divmod(int(total_seconds), 3600)
                minutes, seconds = divmod(remainder, 60)
                self.timestamp_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}.{int((total_seconds % 1) * 100):02d}")
                if hasattr(self, 'session_time_var'):
                    self.session_time_var.set(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
                
                # Calculate FPS for Dashboard
                if hasattr(self, 'fps_counter') and hasattr(self, 'fps_time'):
                    self.fps_counter += 1
                    curr_time = time.time()
                    if curr_time - self.fps_time >= 1.0:
                        fps = self.fps_counter / (curr_time - self.fps_time)
                        if hasattr(self, 'fps_var'):
                            self.fps_var.set(f"{fps:.1f}")
                        self.fps_counter = 0
                        self.fps_time = curr_time
                
                # Calculate Summary board data
                self.vehicle_count = {}
                total_inside = 0
                for region_idx, classwise_count in self.region_counts.items():
                    for v_class, count in classwise_count.items():
                        self.vehicle_count[v_class] = self.vehicle_count.get(v_class, {'IN': 0})
                        self.vehicle_count[v_class]['IN'] += int(count)
                        total_inside += int(count)
                
                # Update Dashboard variables
                if hasattr(self, 'total_count_var'):
                    self.total_count_var.set(str(total_inside))
                                
                # Display and update table
                rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
                self.display_frame_on_canvas(rgb_image)
                self.update_table_data()
                
                # Update slider position
                if hasattr(self, 'video_slider'):
                    self.is_manual_seek = True # Block feedback loop
                    self.slider_var.set(self.frame_count)
                    if hasattr(self, 'frame_info_var') and hasattr(self, 'total_frames'):
                        self.frame_info_var.set(f"Frame: {self.frame_count} / {self.total_frames}")
                    self.is_manual_seek = False
                
                if self.tracking:
                    self.timer_id = self.after(2, self.update_frame)
                    
            elif not ret:
                self.export_log()
                self.stop_tracking()
                
        except Exception as e:
            print(f"Error in update_frame: {e}")
            traceback.print_exc()
            self.stop_tracking()
    
    def update_table_data(self):
        """Update the results table with per-region counts (filtered by class and region)"""
        if not self.region_counts:
            return
        
        # Clear existing table
        for item in self.table.get_children():
            self.table.delete(item)
        
        # Get filter selection
        current_filter = self.region_filter.get()
        
        # Determine which regions to display
        if current_filter == "All Regions":
            region_indices = sorted(self.region_counts.keys())
        else:
            # Extract region number from "Region X"
            try:
                region_num = int(current_filter.split()[-1]) - 1
                region_indices = [region_num] if region_num in self.region_counts else []
            except (ValueError, IndexError):
                region_indices = sorted(self.region_counts.keys())
        
        # Populate table with per-region data (only allowed vehicle classes)
        for region_idx in region_indices:
            if region_idx not in self.region_counts:
                continue
                
            classwise_count = self.region_counts[region_idx]
            region_label = f"Region {region_idx + 1}"
            region_color = self.region_colors[region_idx % len(self.region_colors)]
            
            # Only display allowed vehicle classes
            for vehicle in self.index:
                vehicle_lower = vehicle.lower()
                if vehicle_lower not in self.allowed_vehicle_classes:
                    continue
                    
                in_count = 0
                out_count = 0
                inside_count = 0
                
                # Check if we have counts for this vehicle in this region
                if vehicle_lower in classwise_count:
                    count_value = classwise_count[vehicle_lower]
                    if isinstance(count_value, dict):
                        # Legacy support just in case
                        in_count = int(count_value.get('IN', 0))
                        out_count = int(count_value.get('OUT', 0))
                    else:
                        # NEW optimized logic provides total inside count
                        inside_count = int(count_value)
                
                iid = self.table.insert("", tk.END, values=(region_label, vehicle, in_count, out_count, inside_count))
                
                # Apply tag with region color for highlighting
                tag_name = f"region_{region_idx}"
                self.table.tag_configure(tag_name, background='white')  # Light blue, green, etc. based on region
                self.table.item(iid, tags=(tag_name,))
    
    def export_log(self):
        """Export tracking log as PDF using ExportUtils"""
        self.update_status("Exporting log...")
        
        if not self.file_name or not self.model:
            messagebox.showerror("Error", "Attributes not loaded.")
            self.update_status("✗ No tracking data to export.")
            return
        
        try:
            # Collect data from Table
            table_rows = []
            for item in self.table.get_children():
                table_rows.append(self.table.item(item)['values'])
            
            c_status = self.status_var.get() if hasattr(self, 'status_var') else "N/A"
            c_timestamp = self.timestamp_var.get() if hasattr(self, 'timestamp_var') else "00:00:00.00"
            
            log_file = export_log_to_pdf(table_rows, APPLICATION_PATH, status=c_status, timestamp=c_timestamp)
            
            if hasattr(self, 'log_file_var'):
                self.log_file_var.set(log_file)
            self.update_status("✓ Log exported successfully!")
            messagebox.showinfo("Success", f"Log exported: {log_file}")
            
        except Exception as e:
            print(f"Export Error: {e}")
            self.update_status("✗ Export failed.")
            messagebox.showerror("Error", f"Error exporting log: {str(e)}")
    
    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.update_idletasks()
    
    def on_slider_move(self, value):
        """Handle manual video seeking via slider"""
        if not self.video_capture or self.is_manual_seek:
            return
            
        # If tracking is active, pausing might be better, 
        # but let's allow seeking and see.
        frame_idx = int(float(value))
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.frame_count = frame_idx  # Keep internal counter synchronized
        self.refresh_video_display(reset=False)
        
        if hasattr(self, 'frame_info_var') and hasattr(self, 'total_frames'):
            self.frame_info_var.set(f"Frame: {frame_idx} / {self.total_frames}")
            
        self.update_status(f"Seeked to frame {frame_idx}")

    def on_mousewheel(self, event):
        """Handle mouse wheel events"""
        pass

if __name__ == "__main__":
    print('Starting ALAM Application')
    app = MainWindow()
    app.mainloop()
