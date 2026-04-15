# Performance Monitoring Script for ALAM Vehicle Counting System
# Measures: FPS, latency, pipeline timing, resource usage, tracking metrics, and more

import psutil
import torch
import time
import statistics
from collections import defaultdict, deque
from datetime import datetime
import json
import csv
import os

class PerformanceMonitor:
    """Comprehensive performance monitoring for video processing pipeline"""
    
    def __init__(self, max_history=300, save_dir="performance_logs"):
        """
        Initialize performance monitor
        
        Args:
            max_history: Number of frames to keep in history for averaging
            save_dir: Directory to save performance reports
        """
        self.max_history = max_history
        self.save_dir = save_dir
        self.start_time = time.time()
        
        # Create logs directory if it doesn't exist
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        # ⚡ 1. Core Speed Metrics
        self.fps_history = deque(maxlen=max_history)
        self.frame_times = deque(maxlen=max_history)  # Time per frame (ms)
        self.frame_count = 0
        
        # 🧠 2. Pipeline Timing Metrics (per frame)
        self.preprocess_times = deque(maxlen=max_history)  # ms
        self.detection_times = deque(maxlen=max_history)   # ms
        self.tracking_times = deque(maxlen=max_history)    # ms
        self.postprocess_times = deque(maxlen=max_history) # ms
        
        # 📉 3. Throughput Metrics
        self.frame_skip_count = 0
        self.total_frames_read = 0
        self.video_start_time = None
        self.video_end_time = None
        
        # 💻 4. Resource Usage Metrics
        self.cpu_usage_history = deque(maxlen=max_history)
        self.gpu_usage_history = deque(maxlen=max_history)
        self.ram_usage_history = deque(maxlen=max_history)
        self.vram_usage_history = deque(maxlen=max_history)
        
        self.process = psutil.Process(os.getpid())
        
        # 🚗 5. Tracking-Specific Metrics
        self.objects_per_frame = deque(maxlen=max_history)
        self.detected_objects_total = 0
        self.tracked_objects_total = 0
        
        # ⏱️ 6. Advanced Timing Metrics
        self.detection_frequency = 0  # How many frames between detections
        self.tracking_update_count = 0
        self.frame_skip_rate = 0
        
        # 📊 7. Input/Configuration Metrics
        self.input_config = {
            'resolution': None,
            'model_name': None,
            'model_size': None,
            'batch_size': 1,
            'roi_count': 0
        }
        
        # 🧪 8. System-Level Metrics
        self.end_to_end_times = deque(maxlen=max_history)
        self.power_consumption = 0
        
        # Summary statistics
        self.summary_stats = {}
        self.last_stat_print_time = time.time()
        self.stat_print_interval = 5  # Print stats every 5 seconds
    
    # ⚡ CORE SPEED METRICS
    def start_frame_timer(self):
        """Start timing a frame"""
        self.frame_start_time = time.time()
    
    def end_frame_timer(self):
        """End timing a frame and record FPS"""
        if hasattr(self, 'frame_start_time'):
            elapsed = (time.time() - self.frame_start_time) * 1000  # Convert to ms
            self.frame_times.append(elapsed)
            self.frame_count += 1
            self.total_frames_read += 1
            
            if elapsed > 0:
                fps = 1000 / elapsed
                self.fps_history.append(fps)
    
    # 🧠 PIPELINE TIMING METRICS
    def timing_block(self, block_name):
        """Context manager for timing pipeline blocks"""
        return TimingBlock(self, block_name)
    
    def record_timing(self, block_name, duration_ms):
        """Record timing for a pipeline block (in milliseconds)"""
        if block_name == "preprocessing":
            self.preprocess_times.append(duration_ms)
        elif block_name == "detection":
            self.detection_times.append(duration_ms)
        elif block_name == "tracking":
            self.tracking_times.append(duration_ms)
        elif block_name == "postprocessing":
            self.postprocess_times.append(duration_ms)
    
    # 📉 THROUGHPUT METRICS
    def record_frame_skip(self):
        """Record a skipped frame"""
        self.frame_skip_count += 1
        self.total_frames_read += 1
    
    def start_video(self, total_duration_seconds=None):
        """Mark video processing start"""
        self.video_start_time = time.time()
        self.video_duration = total_duration_seconds
    
    def end_video(self):
        """Mark video processing end"""
        self.video_end_time = time.time()
    
    def get_effective_fps(self):
        """Calculate effective FPS after frame skipping"""
        if self.total_frames_read == 0:
            return 0
        processed_frames = self.frame_count
        elapsed_time = time.time() - self.start_time
        return processed_frames / elapsed_time if elapsed_time > 0 else 0
    
    def get_rtf(self):
        """Calculate Real-Time Factor (processing time / video duration)"""
        if not self.video_duration or not self.video_start_time:
            return None
        processing_time = (self.video_end_time or time.time()) - self.video_start_time
        return processing_time / self.video_duration
    
    # 💻 RESOURCE USAGE METRICS
    def record_resource_usage(self):
        """Record current CPU, GPU, RAM, VRAM usage"""
        # CPU Usage
        cpu_percent = self.process.cpu_percent(interval=0.1)
        self.cpu_usage_history.append(cpu_percent)
        
        # RAM Usage (MB)
        ram_mb = self.process.memory_info().rss / (1024 * 1024)
        self.ram_usage_history.append(ram_mb)
        
        # GPU/VRAM Usage
        try:
            if torch.cuda.is_available():
                gpu_usage = torch.cuda.memory_allocated() / (1024 ** 3)  # GB
                self.vram_usage_history.append(gpu_usage)
                
                # GPU utilization percentage (requires nvidia-ml-py)
                try:
                    import pynvml
                    pynvml.nvmlInit()
                    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                    gpu_util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    self.gpu_usage_history.append(gpu_util)
                except:
                    self.gpu_usage_history.append(0)
            else:
                self.gpu_usage_history.append(0)
                self.vram_usage_history.append(0)
        except:
            self.gpu_usage_history.append(0)
            self.vram_usage_history.append(0)
    
    # 🚗 TRACKING-SPECIFIC METRICS
    def record_detected_objects(self, count, region_idx=None):
        """Record number of objects detected in current frame"""
        self.detected_objects_total += count
        if not hasattr(self, '_current_frame_objects'):
            self._current_frame_objects = 0
        self._current_frame_objects += count
    
    def record_tracked_objects(self, count):
        """Record number of objects currently tracked"""
        self.tracked_objects_total += count
    
    def finalize_frame_objects(self):
        """Finalize object count for current frame"""
        if hasattr(self, '_current_frame_objects'):
            self.objects_per_frame.append(self._current_frame_objects)
            self._current_frame_objects = 0
    
    # ⏱️ ADVANCED TIMING METRICS
    def set_detection_frequency(self, every_n_frames):
        """Set how often detection runs (e.g., every 10 frames)"""
        self.detection_frequency = every_n_frames
    
    def record_tracking_update(self):
        """Record a tracking update"""
        self.tracking_update_count += 1
    
    def update_skip_rate(self):
        """Update frame skip rate"""
        if self.total_frames_read > 0:
            self.frame_skip_rate = self.frame_skip_count / self.total_frames_read
    
    # 📊 INPUT/CONFIGURATION METRICS
    def set_input_config(self, resolution=None, model_name=None, model_size=None, 
                        batch_size=1, roi_count=0):
        """Set input configuration"""
        self.input_config = {
            'resolution': resolution,
            'model_name': model_name,
            'model_size': model_size,
            'batch_size': batch_size,
            'roi_count': roi_count
        }
    
    # 🧪 SYSTEM-LEVEL METRICS
    def record_end_to_end_time(self, duration_ms):
        """Record end-to-end processing time for a frame"""
        self.end_to_end_times.append(duration_ms)
    
    # ==== STATISTICS & REPORTING ====
    
    def get_stats_summary(self):
        """Generate comprehensive statistics summary"""
        stats = {}
        
        # ⚡ 1. Core Speed Metrics
        if self.fps_history:
            stats['fps_current'] = self.fps_history[-1] if self.fps_history else 0
            stats['fps_avg'] = statistics.mean(self.fps_history)
            stats['fps_max'] = max(self.fps_history)
            stats['fps_min'] = min(self.fps_history)
            stats['fps_stdev'] = statistics.stdev(self.fps_history) if len(self.fps_history) > 1 else 0
        
        if self.frame_times:
            stats['latency_ms_avg'] = statistics.mean(self.frame_times)
            stats['latency_ms_max'] = max(self.frame_times)
            stats['latency_ms_min'] = min(self.frame_times)
        
        # 🧠 2. Pipeline Timing Metrics
        stats['preprocess_ms_avg'] = statistics.mean(self.preprocess_times) if self.preprocess_times else 0
        stats['detection_ms_avg'] = statistics.mean(self.detection_times) if self.detection_times else 0
        stats['tracking_ms_avg'] = statistics.mean(self.tracking_times) if self.tracking_times else 0
        stats['postprocess_ms_avg'] = statistics.mean(self.postprocess_times) if self.postprocess_times else 0
        stats['pipeline_total_ms_avg'] = sum([
            stats['preprocess_ms_avg'],
            stats['detection_ms_avg'],
            stats['tracking_ms_avg'],
            stats['postprocess_ms_avg']
        ])
        
        # 📉 3. Throughput Metrics
        stats['effective_fps'] = self.get_effective_fps()
        stats['rtf'] = self.get_rtf()
        stats['frames_read_total'] = self.total_frames_read
        stats['frames_processed'] = self.frame_count
        stats['frames_skipped'] = self.frame_skip_count
        
        # 💻 4. Resource Usage Metrics
        stats['cpu_usage_avg'] = statistics.mean(self.cpu_usage_history) if self.cpu_usage_history else 0
        stats['cpu_usage_max'] = max(self.cpu_usage_history) if self.cpu_usage_history else 0
        stats['ram_usage_avg_mb'] = statistics.mean(self.ram_usage_history) if self.ram_usage_history else 0
        stats['ram_usage_max_mb'] = max(self.ram_usage_history) if self.ram_usage_history else 0
        stats['gpu_usage_avg'] = statistics.mean(self.gpu_usage_history) if self.gpu_usage_history else 0
        stats['vram_usage_avg_gb'] = statistics.mean(self.vram_usage_history) if self.vram_usage_history else 0
        stats['vram_usage_max_gb'] = max(self.vram_usage_history) if self.vram_usage_history else 0
        
        # 🚗 5. Tracking-Specific Metrics
        stats['objects_per_frame_avg'] = statistics.mean(self.objects_per_frame) if self.objects_per_frame else 0
        stats['objects_per_frame_max'] = max(self.objects_per_frame) if self.objects_per_frame else 0
        stats['objects_processed_total'] = self.detected_objects_total
        stats['objects_tracked_total'] = self.tracked_objects_total
        
        # ⏱️ 6. Advanced Timing Metrics
        stats['detection_frequency'] = self.detection_frequency
        stats['tracking_updates_total'] = self.tracking_update_count
        stats['frame_skip_rate'] = self.frame_skip_rate
        
        # 📊 7. Input/Configuration Metrics
        stats.update({f'config_{k}': v for k, v in self.input_config.items()})
        
        # 🧪 8. System-Level Metrics
        stats['end_to_end_ms_avg'] = statistics.mean(self.end_to_end_times) if self.end_to_end_times else 0
        stats['processing_time_total_seconds'] = time.time() - self.start_time
        
        self.summary_stats = stats
        return stats
    
    def print_stats(self, detailed=False):
        """Print performance statistics"""
        stats = self.get_stats_summary()
        
        print("\n" + "="*70)
        print("⚡ PERFORMANCE MONITORING REPORT")
        print("="*70)
        
        print("\n⚡ 1. CORE SPEED METRICS")
        print(f"  Current FPS: {stats.get('fps_current', 0):.1f}")
        print(f"  Average FPS: {stats.get('fps_avg', 0):.1f}")
        print(f"  FPS Range: {stats.get('fps_min', 0):.1f} - {stats.get('fps_max', 0):.1f}")
        print(f"  FPS Stability (Stdev): {stats.get('fps_stdev', 0):.2f}")
        print(f"  Avg Latency: {stats.get('latency_ms_avg', 0):.2f} ms/frame")
        print(f"  Latency Range: {stats.get('latency_ms_min', 0):.2f} - {stats.get('latency_ms_max', 0):.2f} ms")
        
        print("\n🧠 2. PIPELINE TIMING METRICS")
        print(f"  Preprocessing Avg: {stats.get('preprocess_ms_avg', 0):.2f} ms")
        print(f"  Detection Avg: {stats.get('detection_ms_avg', 0):.2f} ms")
        print(f"  Tracking Avg: {stats.get('tracking_ms_avg', 0):.2f} ms")
        print(f"  Postprocessing Avg: {stats.get('postprocess_ms_avg', 0):.2f} ms")
        print(f"  Total Pipeline: {stats.get('pipeline_total_ms_avg', 0):.2f} ms")
        
        print("\n📉 3. THROUGHPUT METRICS")
        print(f"  Effective FPS: {stats.get('effective_fps', 0):.1f}")
        print(f"  Total Frames Read: {stats.get('frames_read_total', 0)}")
        print(f"  Frames Processed: {stats.get('frames_processed', 0)}")
        print(f"  Frames Skipped: {stats.get('frames_skipped', 0)}")
        print(f"  Frame Skip Rate: {stats.get('frame_skip_rate', 0):.1%}")
        if stats.get('rtf'):
            print(f"  Real-Time Factor (RTF): {stats.get('rtf', 0):.2f}x")
        
        print("\n💻 4. RESOURCE USAGE METRICS")
        print(f"  CPU Usage Avg: {stats.get('cpu_usage_avg', 0):.1f}%")
        print(f"  CPU Usage Max: {stats.get('cpu_usage_max', 0):.1f}%")
        print(f"  RAM Usage Avg: {stats.get('ram_usage_avg_mb', 0):.1f} MB")
        print(f"  RAM Usage Max: {stats.get('ram_usage_max_mb', 0):.1f} MB")
        print(f"  GPU Utilization Avg: {stats.get('gpu_usage_avg', 0):.1f}%")
        print(f"  VRAM Usage Avg: {stats.get('vram_usage_avg_gb', 0):.2f} GB")
        print(f"  VRAM Usage Max: {stats.get('vram_usage_max_gb', 0):.2f} GB")
        
        print("\n🚗 5. TRACKING-SPECIFIC METRICS")
        print(f"  Objects per Frame Avg: {stats.get('objects_per_frame_avg', 0):.1f}")
        print(f"  Objects per Frame Max: {stats.get('objects_per_frame_max', 0)}")
        print(f"  Total Objects Detected: {stats.get('objects_processed_total', 0)}")
        print(f"  Total Objects Tracked: {stats.get('objects_tracked_total', 0)}")
        
        print("\n⏱️ 6. ADVANCED TIMING METRICS")
        print(f"  Detection Frequency: Every {stats.get('detection_frequency', 0)} frames")
        print(f"  Tracking Updates Total: {stats.get('tracking_updates_total', 0)}")
        
        print("\n📊 7. INPUT/CONFIGURATION METRICS")
        print(f"  Input Resolution: {stats.get('config_resolution', 'N/A')}")
        print(f"  Model: {stats.get('config_model_name', 'N/A')}")
        print(f"  Model Size: {stats.get('config_model_size', 'N/A')}")
        print(f"  ROI Count: {stats.get('config_roi_count', 0)}")
        
        print("\n🧪 8. SYSTEM-LEVEL METRICS")
        print(f"  End-to-End Processing: {stats.get('end_to_end_ms_avg', 0):.2f} ms/frame")
        print(f"  Total Processing Time: {stats.get('processing_time_total_seconds', 0):.1f} seconds")
        
        print("\n" + "="*70)
    
    def save_stats(self, filename=None):
        """Save statistics to JSON and CSV files"""
        if not filename:
            filename = f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        stats = self.get_stats_summary()
        
        # Save as JSON
        json_path = os.path.join(self.save_dir, f"{filename}.json")
        with open(json_path, 'w') as f:
            json.dump(stats, f, indent=2)
        print(f"\n✅ Saved JSON report: {json_path}")
        
        # Save as CSV
        csv_path = os.path.join(self.save_dir, f"{filename}.csv")
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Metric', 'Value'])
            for key, value in stats.items():
                writer.writerow([key, value])
        print(f"✅ Saved CSV report: {csv_path}")
        
        return json_path, csv_path
    
    def save_detailed_timings(self, filename=None):
        """Save detailed timing histories to CSV"""
        if not filename:
            filename = f"timings_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        csv_path = os.path.join(self.save_dir, f"{filename}.csv")
        
        max_len = max(len(self.fps_history), len(self.preprocess_times), 
                     len(self.detection_times), len(self.tracking_times),
                     len(self.postprocess_times), len(self.frame_times))
        
        with open(csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Frame', 'FPS', 'Frame_Time_ms', 'Preprocess_ms', 
                           'Detection_ms', 'Tracking_ms', 'Postprocess_ms', 
                           'CPU%', 'RAM_MB', 'GPU%', 'VRAM_GB', 'Objects_Count'])
            
            for i in range(max_len):
                row = [
                    i,
                    self.fps_history[i] if i < len(self.fps_history) else '',
                    self.frame_times[i] if i < len(self.frame_times) else '',
                    self.preprocess_times[i] if i < len(self.preprocess_times) else '',
                    self.detection_times[i] if i < len(self.detection_times) else '',
                    self.tracking_times[i] if i < len(self.tracking_times) else '',
                    self.postprocess_times[i] if i < len(self.postprocess_times) else '',
                    self.cpu_usage_history[i] if i < len(self.cpu_usage_history) else '',
                    self.ram_usage_history[i] if i < len(self.ram_usage_history) else '',
                    self.gpu_usage_history[i] if i < len(self.gpu_usage_history) else '',
                    self.vram_usage_history[i] if i < len(self.vram_usage_history) else '',
                    self.objects_per_frame[i] if i < len(self.objects_per_frame) else '',
                ]
                writer.writerow(row)
        
        print(f"✅ Saved detailed timings: {csv_path}")
        return csv_path


class TimingBlock:
    """Context manager for timing code blocks"""
    
    def __init__(self, monitor, block_name):
        self.monitor = monitor
        self.block_name = block_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        self.monitor.record_timing(self.block_name, duration_ms)


# Example usage
if __name__ == "__main__":
    print("Performance Monitor Module")
    print("Import this module and create a PerformanceMonitor instance to track performance")
    print("\nExample:")
    print("  from performance_monitor import PerformanceMonitor")
    print("  pm = PerformanceMonitor()")
    print("  pm.set_input_config(resolution='1920x1080', model_name='YOLOv8n', roi_count=3)")
    print("  pm.start_frame_timer()")
    print("  # ... do processing ...")
    print("  with pm.timing_block('detection'):")
    print("      # detection code here")
    print("  pm.end_frame_timer()")
    print("  pm.print_stats()")
    print("  pm.save_stats()")
