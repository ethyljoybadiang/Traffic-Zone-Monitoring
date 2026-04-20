import cv2
import numpy as np
import os
import torch
import tkinter as tk
import time

from ultralytics import YOLO
from tkinter import ttk, filedialog, messagebox
from datetime import datetime

class VideoEngine:
    def __init__(self):
        self.model = None
        self.allowed_vehicle_classes = {'car', 'bicycle', 'motorcycle', 'jeepney', 'train', 'truck'}
        self.region_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def load_model(self, file_name):
        """Load and return the YOLO model"""
        is_openvino_xml = file_name.lower().endswith('.xml')
        model_path = os.path.dirname(file_name) if is_openvino_xml else file_name
        
        model = YOLO(model_path, task="detect")
        
        # Check if model is PyTorch format
        is_pytorch_model = file_name.lower().endswith('.pt') or file_name.lower().endswith('.pth')
        
        device = 'cpu'
        if torch.cuda.is_available() and is_pytorch_model:
            model.to('cuda:0')
            device = 'gpu'
            
        self.model = model
        return model, device

    def sort_points_clockwise(self, pts):
        """Sort points in clockwise order"""
        import math
        if not pts: return []
        cx = sum(p[0] for p in pts) / len(pts)
        cy = sum(p[1] for p in pts) / len(pts)
        return sorted(pts, key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

    def process_frame_tracking(self, frame, regions, model_names):
        """
        Run tracking on a frame and return annotated frame and region counts
        """
        if self.model is None:
            return frame, {}

        # Run tracking on the FULL frame once
        results = self.model.track(frame, persist=True, conf=0.25, verbose=False)
        
        annotated_frame = frame.copy()
        region_counts = {}
        
        if results[0].boxes.id is not None:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            track_ids = results[0].boxes.id.int().cpu().tolist()
            clss = results[0].boxes.cls.int().cpu().tolist()
            
            # Track which boxes have already been drawn (if they fall in multiple regions)
            drawn_indices = set()
            
            for region_idx, region in enumerate(regions):
                region_poly = np.array(region, dtype=np.int32)
                current_region_counts = {}
                color = self.region_colors[region_idx % len(self.region_colors)]
                
                for i, (box, track_id, cls) in enumerate(zip(boxes, track_ids, clss)):
                    class_name = model_names[cls].lower()
                    if class_name not in self.allowed_vehicle_classes:
                        continue
                    
                    # Center point for region check
                    cx = int((box[0] + box[2]) / 2)
                    cy = int((box[1] + box[3]) / 2)
                    
                    # Check if inside region
                    if cv2.pointPolygonTest(region_poly, (cx, cy), False) >= 0:
                        # Count it
                        current_region_counts[class_name] = current_region_counts.get(class_name, 0) + 1
                        
                        # Draw it (once per box, using the color of the first region it falls in)
                        if i not in drawn_indices:
                            x1, y1, x2, y2 = map(int, box)
                            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                            drawn_indices.add(i)
                
                region_counts[region_idx] = current_region_counts
        
        # Draw regions on the annotated frame
        for idx, region in enumerate(regions):
            color = self.region_colors[idx % len(self.region_colors)]
            pts = np.array([[int(p[0]), int(p[1])] for p in region], np.int32)
            cv2.polylines(annotated_frame, [pts], True, color, 2)
            cv2.putText(annotated_frame, f"Region {idx + 1}", (int(region[0][0]), int(region[0][1]) - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        
        return annotated_frame, region_counts

    def letterbox_frame(self, img, new_shape=(640, 640), color=(0, 0, 0)):
        """Helper to resize and pad image for standardized 640x640 processing"""
        shape = img.shape[:2] # current shape [height, width]
        
        # Scale ratio (new / old)
        r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])

        # Compute padding
        new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
        dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]

        dw /= 2 # divide padding into 2 sides
        dh /= 2

        if shape[::-1] != new_unpad: # resize
            img = cv2.resize(img, new_unpad, interpolation=cv2.INTER_LINEAR)
        
        top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
        left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
        
        img = cv2.copyMakeBorder(img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
        return img


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
