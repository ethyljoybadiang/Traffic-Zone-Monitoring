import os
import tkinter as tk
import torch
from tkinter import filedialog, messagebox
import cv2

class SelectionMixin:
    """Mixin class for handling model and video selection."""
    def select_model(self):
        """Select and load AI model."""
        file_name = filedialog.askopenfilename(
            title="Select Model",
            filetypes=[
                ("All Supported Models", "*.pt *.pth *.xml"),
                ("PyTorch Models", "*.pt *.pth"),
                ("OpenVINO Models", "*.xml"),
                ("All Files", "*.*"),
            ],
        )

        if not file_name:
            self.update_status("Model selection cancelled.")
            return

        self.update_status("Loading AI model... Please wait.")
        try:
            self.model, device_type = self.video_engine.load_model(file_name)

            if device_type == "gpu":
                self.update_status("✓ Model loaded on GPU.")
                print(f"\n{'=' * 40}")
                print(f"NOTICE: GPU is being used! (CUDA: {torch.cuda.get_device_name(0)})")
                print(f"{'=' * 40}\n")
            else:
                self.update_status(f"✓ Model loaded on {device_type.upper()}.")

            self.file_name = file_name
            model_name = os.path.basename(file_name)
            self.model_name_var.set(model_name)
            self.ai_model_var.set(model_name)

            self.vehicles = {value: 0 for key, value in self.model.names.items()}
            self.initialize_table()

            self.select_video_btn.config(state="normal")
            self.update_status("✓ Model loaded. Now select a video.")

        except Exception as exc:
            messagebox.showerror("Error", f"Failed to load model: {exc}")
            self.update_status("✗ Model loading failed.")

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
