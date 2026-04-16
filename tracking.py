import cv2
import time
import traceback

class TrackingMixin:
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