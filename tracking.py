import cv2
import time
import traceback

class TrackingMixin:
    def _format_timestamp(self, total_seconds):
        hours, remainder = divmod(int(total_seconds), 3600)
        minutes, seconds = divmod(remainder, 60)
        hundredths = int((total_seconds % 1) * 100)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{hundredths:02d}", f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def _sync_slider_from_capture(self):
        """Update slider UI from current VideoCapture position (guarded)."""
        if not hasattr(self, "video_slider") or not hasattr(self, "slider_var"):
            return

        if not self.video_capture:
            return

        try:
            # After a successful read(), POS_FRAMES is typically the NEXT frame index.
            current_pos = int(self.video_capture.get(cv2.CAP_PROP_POS_FRAMES)) - 1
        except Exception:
            return

        if current_pos < 0:
            current_pos = 0

        self.frame_count = current_pos

        self.is_manual_seek = True  # prevent feedback loop into on_slider_move
        try:
            self.slider_var.set(current_pos)
            if hasattr(self, "frame_info_var") and hasattr(self, "total_frames"):
                self.frame_info_var.set(f"Frame: {current_pos} / {self.total_frames}")
        finally:
            self.is_manual_seek = False

    def on_slider_move(self, value):
        """Seek the video when the slider is moved manually."""
        if not self.video_capture or getattr(self, "is_manual_seek", False):
            return

        try:
            frame_idx = int(float(value))
        except Exception:
            return

        total_frames = getattr(self, "total_frames", None)
        if isinstance(total_frames, int) and total_frames > 0:
            frame_idx = max(0, min(frame_idx, total_frames - 1))

        try:
            # Force next tracking tick to read (not just grab) after a manual seek.
            self._tracking_tick = 0

            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            ret, frame = self.video_capture.read()
            if not ret or frame is None or frame.size == 0:
                return

            # Standardize frame size used by the rest of the app.
            if getattr(self, "width", None) and getattr(self, "height", None):
                frame = cv2.resize(frame, (self.width, self.height), interpolation=cv2.INTER_LINEAR)

            # If tracking context exists, show the annotated frame; otherwise show raw preview.
            if getattr(self, "tracking", False) and getattr(self, "model", None) and getattr(self, "regions", None):
                annotated_frame, _ = self.video_engine.process_frame_tracking(frame, self.regions, self.model.names)
                rgb_image = cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)
            else:
                rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            self.display_frame_on_canvas(rgb_image)

            # Update timestamp using FPS for stable mapping from slider -> time.
            fps = float(self.video_capture.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps > 0:
                total_seconds = frame_idx / fps
            else:
                total_seconds = float(self.video_capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0) / 1000.0

            ts_full, ts_hms = self._format_timestamp(total_seconds)
            if hasattr(self, "timestamp_var"):
                self.timestamp_var.set(ts_full)
            if hasattr(self, "session_time_var"):
                self.session_time_var.set(ts_hms)

        finally:
            # Keep capture position aligned with the slider's selected frame.
            try:
                self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            except Exception:
                pass

        # Reflect the seek in the slider UI text (frame label), without re-triggering seek.
        self._sync_slider_from_capture()

    def update_frame(self):
        """Update frame during tracking with delegated processing"""
        if not self.tracking or not self.video_capture:
            return
        
        try:
            # FPS and frame management
            self._tracking_tick = getattr(self, "_tracking_tick", 0) + 1
            if self._tracking_tick % 2 == 0:
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
                timestamp_ms = float(self.video_capture.get(cv2.CAP_PROP_POS_MSEC) or 0.0)
                total_seconds = timestamp_ms / 1000.0
                ts_full, ts_hms = self._format_timestamp(total_seconds)
                if hasattr(self, "timestamp_var"):
                    self.timestamp_var.set(ts_full)
                if hasattr(self, "session_time_var"):
                    self.session_time_var.set(ts_hms)
                
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
                
                # Update slider position from the actual capture position
                self._sync_slider_from_capture()
                
                if self.tracking:
                    self.timer_id = self.after(2, self.update_frame)
                    
            elif not ret:
                self.export_log()
                self.stop_tracking()
                
        except Exception as e:
            print(f"Error in update_frame: {e}")
            traceback.print_exc()
            self.stop_tracking()
