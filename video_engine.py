import cv2
import json
import numpy as np
import os
import torch
import cv2
import json
import numpy as np
import os
import torch
import time

from ultralytics import YOLO
from datetime import datetime

class DummyBoxes:
    def __init__(self, xyxy, ids, cls):
        self.xyxy = xyxy
        self.id = ids
        self.cls = cls

class DummyResult:
    def __init__(self, boxes):
        self.boxes = boxes

class SimpleTracker:
    """Lightweight IoU-based object tracker for persistent IDs."""
    def __init__(self, iou_threshold=0.25, max_lost=30):
        self.next_id = 1
        self.tracks = {}
        self.iou_threshold = iou_threshold
        self.max_lost = max_lost

    @staticmethod
    def _iou(b1, b2):
        x1, y1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        x2, y2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        inter = max(0, x2 - x1) * max(0, y2 - y1)
        a1 = (b1[2] - b1[0]) * (b1[3] - b1[1])
        a2 = (b2[2] - b2[0]) * (b2[3] - b2[1])
        union = a1 + a2 - inter
        return inter / union if union > 0 else 0

    def update(self, boxes, classes):
        if not boxes:
            for tid in list(self.tracks):
                self.tracks[tid]['lost'] += 1
                if self.tracks[tid]['lost'] > self.max_lost:
                    del self.tracks[tid]
            return [], [], []

        track_ids = list(self.tracks.keys())
        used = set()
        assign = {}

        for i, box in enumerate(boxes):
            best_iou, best_tid = self.iou_threshold, None
            for tid in track_ids:
                if tid in used:
                    continue
                iou = self._iou(box, self.tracks[tid]['box'])
                if iou > best_iou:
                    best_iou, best_tid = iou, tid
            if best_tid is not None:
                assign[i] = best_tid
                used.add(best_tid)

        for i, tid in assign.items():
            self.tracks[tid] = {'box': boxes[i], 'cls': classes[i], 'lost': 0}

        for i in range(len(boxes)):
            if i not in assign:
                assign[i] = self.next_id
                self.tracks[self.next_id] = {'box': boxes[i], 'cls': classes[i], 'lost': 0}
                self.next_id += 1

        for tid in track_ids:
            if tid not in used:
                self.tracks[tid]['lost'] += 1
                if self.tracks[tid]['lost'] > self.max_lost:
                    del self.tracks[tid]

        return boxes, [assign[i] for i in range(len(boxes))], classes


class HailoWrapper:
    def __init__(self, model_path, labels_path=None):
        try:
            from hailo_platform import HEF, VDevice, ConfigureParams, InputVStreamParams, OutputVStreamParams, FormatType, HailoStreamInterface  # type: ignore
            self.target = VDevice()
            self.hef = HEF(model_path)
            self.configure_params = ConfigureParams.create_from_hef(self.hef, interface=HailoStreamInterface.PCIe)
            self.network_group = self.target.configure(self.hef, self.configure_params)[0]
            self.input_vstreams_params = InputVStreamParams.make_from_network_group(self.network_group, format_type=FormatType.UINT8)
            self.output_vstreams_params = OutputVStreamParams.make_from_network_group(self.network_group, format_type=FormatType.FLOAT32)
            
            # Activate the network group — REQUIRED before any inference
            # activate() returns a context manager; we must __enter__ it
            # to actually hold the activation open persistently
            self.network_group_params = self.network_group.create_params()
            self._activation_ctx = self.network_group.activate(self.network_group_params)
            self._activation_ctx.__enter__()
            print(f"[Hailo] Network group activated successfully")
            
            # Cache input stream info so we don't query it every frame
            self._input_vstream_info = self.network_group.get_input_vstream_infos()[0]
            expected_shape = self._input_vstream_info.shape
            if len(expected_shape) == 4:
                self._input_h, self._input_w, self._input_c = expected_shape[1], expected_shape[2], expected_shape[3]
            else:
                self._input_h, self._input_w, self._input_c = expected_shape[0], expected_shape[1], expected_shape[2]
            print(f"[Hailo] Model input: {self._input_w}x{self._input_h}x{self._input_c} ({expected_shape})")
            
            self.mock_mode = False
        except ImportError:
            print("Warning: hailo_platform not found. Running HailoWrapper in MOCK mode for UI testing.")
            self.mock_mode = True
        
        # Load class names: labels_path > auto-detect > COCO fallback
        self.names = self._load_labels(model_path, labels_path)
        self.is_hailo = True
        self._tracker = SimpleTracker()
        self._output_logged = False

    def _load_labels(self, model_path, labels_path=None):
        """Load class names from labels.json (optional).
        
        Search order:
        1. Explicit labels_path argument
        2. labels.json in the same directory as the .hef file
        3. COCO fallback defaults
        
        Supported labels.json formats:
        - Dict:  {"0": "car", "1": "truck", ...}
        - List:  ["car", "truck", ...]
        """
        coco_fallback = {0: 'person', 1: 'bicycle', 2: 'car', 3: 'motorcycle', 5: 'bus', 7: 'truck'}
        
        # Determine file to load
        json_path = labels_path
        if json_path is None:
            # Auto-detect: look for labels.json next to the model
            model_dir = os.path.dirname(os.path.abspath(model_path))
            auto_path = os.path.join(model_dir, 'labels.json')
            if os.path.isfile(auto_path):
                json_path = auto_path
        
        if json_path is None or not os.path.isfile(json_path):
            print(f"[Hailo] No labels.json found. Using COCO fallback names.")
            return coco_fallback
        
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                # {"0": "car", "1": "truck"} → {0: "car", 1: "truck"}
                names = {int(k): str(v) for k, v in data.items()}
            elif isinstance(data, list):
                # ["car", "truck"] → {0: "car", 1: "truck"}
                names = {i: str(v) for i, v in enumerate(data)}
            else:
                print(f"[Hailo] WARNING: labels.json has unexpected format. Using COCO fallback.")
                return coco_fallback
            
            print(f"[Hailo] Loaded {len(names)} class names from {os.path.basename(json_path)}: {names}")
            return names
        except Exception as e:
            print(f"[Hailo] WARNING: Failed to load labels.json: {e}. Using COCO fallback.")
            return coco_fallback

    def release(self):
        """Deactivate the network group and release Hailo resources."""
        if hasattr(self, '_activation_ctx') and self._activation_ctx is not None:
            try:
                self._activation_ctx.__exit__(None, None, None)
                print("[Hailo] Network group deactivated")
            except Exception as e:
                print(f"[Hailo] Warning during deactivation: {e}")
            self._activation_ctx = None

    def __del__(self):
        self.release()

    def _parse_hailo_detections(self, infer_results, frame_h, frame_w, conf=0.25):
        """Parse Hailo NMS inference output into boxes, scores, and class IDs."""
        output_names = list(infer_results.keys())
        boxes, scores, classes = [], [], []

        for name in output_names:
            data = infer_results[name]

            # Debug: log output structure on first call
            if not self._output_logged:
                self._output_logged = True
                print(f"[Hailo] Model has {len(output_names)} output layer(s):")

            # --- NMS by-class list format ---
            # Hailo NMS output is typically: [batch_0] where batch_0 = [class_0_dets, class_1_dets, ...]
            # Each class_N_dets is an ndarray of shape (num_detections, 5): [ymin, xmin, ymax, xmax, score]
            if isinstance(data, list):
                class_arrays = data

                # Unwrap batch dimension: if data = [[class0_dets, class1_dets, ...]]
                if len(data) >= 1 and isinstance(data[0], (list, np.ndarray)):
                    # Check if first element is itself a list of arrays (batch wrapper)
                    first = data[0]
                    if isinstance(first, list) and len(first) > 0:
                        # data[0] is the per-class list for batch 0
                        class_arrays = first

                if not self._output_logged:
                    pass  # already printed header above
                # Log class structure
                if not hasattr(self, '_classes_logged'):
                    self._classes_logged = True
                    print(f"  '{name}': {len(class_arrays)} classes (NMS by-class format)")
                    for i, cls_arr in enumerate(class_arrays):
                        try:
                            arr = np.array(cls_arr, dtype=np.float32) if not isinstance(cls_arr, np.ndarray) else cls_arr
                            if arr.size > 0:
                                print(f"    class {i} ({self.names.get(i, '?')}): shape={arr.shape}")
                            else:
                                print(f"    class {i} ({self.names.get(i, '?')}): empty")
                        except Exception:
                            print(f"    class {i} ({self.names.get(i, '?')}): (variable-length detections)")

                # Parse each class's detections
                for class_id, cls_dets in enumerate(class_arrays):
                    if not isinstance(cls_dets, np.ndarray):
                        try:
                            cls_dets = np.array(cls_dets, dtype=np.float32)
                        except ValueError:
                            continue  # skip jagged / empty arrays
                    if cls_dets.ndim < 2 or cls_dets.size == 0:
                        continue
                    for det in cls_dets:
                        if len(det) >= 5:
                            ymin, xmin, ymax, xmax, score = det[0], det[1], det[2], det[3], det[4]
                            if score > conf:
                                boxes.append([
                                    xmin * frame_w, ymin * frame_h,
                                    xmax * frame_w, ymax * frame_h
                                ])
                                scores.append(float(score))
                                classes.append(class_id)
                return boxes, scores, classes

            # --- NMS 4D ndarray (batch, num_classes, max_det, 5) ---
            if isinstance(data, np.ndarray) and len(data.shape) == 4 and data.shape[-1] == 5:
                batch = data[0]
                for class_id in range(batch.shape[0]):
                    for det in batch[class_id]:
                        ymin, xmin, ymax, xmax, score = det
                        if score > conf:
                            boxes.append([xmin * frame_w, ymin * frame_h, xmax * frame_w, ymax * frame_h])
                            scores.append(float(score))
                            classes.append(class_id)
                return boxes, scores, classes

            # --- NMS 3D ndarray (batch, total_det, 6) ---
            if isinstance(data, np.ndarray) and len(data.shape) == 3 and data.shape[-1] == 6:
                batch = data[0]
                for det in batch:
                    xmin, ymin, xmax, ymax, score, cls = det
                    if score > conf:
                        boxes.append([xmin * frame_w, ymin * frame_h, xmax * frame_w, ymax * frame_h])
                        scores.append(float(score))
                        classes.append(int(cls))
                return boxes, scores, classes

        if not hasattr(self, '_raw_warned'):
            self._raw_warned = True
            print("[Hailo] WARNING: Output format not recognized. Run: hailortcli parse-hef <model.hef>")

        return boxes, scores, classes

    def track(self, frame, persist=True, conf=0.25, verbose=False):
        """Run Hailo inference + post-processing + tracking on a frame."""
        frame_h, frame_w = frame.shape[:2]
        det_boxes, det_ids, det_cls = [], [], []

        if not getattr(self, 'mock_mode', False):
            from hailo_platform import InferVStreams  # type: ignore
            
            # Preprocess: resize and convert color
            resized_frame = cv2.resize(frame, (self._input_w, self._input_h))
            if self._input_c == 3:
                resized_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
            
            # Add batch dimension (N, H, W, C) and ensure contiguous uint8
            input_data_array = np.expand_dims(resized_frame, axis=0).astype(np.uint8)
            input_data_array = np.ascontiguousarray(input_data_array)
            input_data = {self._input_vstream_info.name: input_data_array}
            
            # Run inference (network group is persistently activated from __init__)
            with InferVStreams(self.network_group, self.input_vstreams_params, self.output_vstreams_params) as infer_pipeline:
                infer_results = infer_pipeline.infer(input_data)

            # Parse detections from the Hailo output
            boxes, scores, classes = self._parse_hailo_detections(
                infer_results, frame_h, frame_w, conf
            )

            # Run simple IoU tracker for persistent IDs
            if boxes:
                det_boxes, det_ids, det_cls = self._tracker.update(boxes, classes)
            else:
                self._tracker.update([], [])

        # Build result in the format expected by process_frame_tracking
        if det_boxes:
            result_boxes = DummyBoxes(
                xyxy=torch.tensor(det_boxes, dtype=torch.float32),
                ids=torch.tensor(det_ids, dtype=torch.int32),
                cls=torch.tensor(det_cls, dtype=torch.int32)
            )
        else:
            result_boxes = DummyBoxes(
                xyxy=torch.tensor([]).reshape(0, 4),
                ids=None,
                cls=torch.tensor([])
            )
        return [DummyResult(result_boxes)]

class VideoEngine:
    def __init__(self):
        self.model = None
        self.allowed_vehicle_classes = {
            'car', 'bicycle', 'motorcycle', 'jeepney', 'train', 'truck',
            'bus', 'person', 'ambulance', 'firetruck', 'motor'
        }
        self.region_colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def load_model(self, file_name, labels_path=None):
        """Load and return the YOLO model"""
        is_openvino_xml = file_name.lower().endswith('.xml')
        model_path = os.path.dirname(file_name) if is_openvino_xml else file_name
        
        # Bypass Ultralytics YOLO if file is Hailo .hef
        if file_name.lower().endswith('.hef'):
            self.model = HailoWrapper(model_path, labels_path=labels_path)
            # Auto-allow all classes from the model's labels
            for name in self.model.names.values():
                self.allowed_vehicle_classes.add(name.lower())
            print(f"[Hailo] Allowed vehicle classes: {self.allowed_vehicle_classes}")
            return self.model, 'npu'
            
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
