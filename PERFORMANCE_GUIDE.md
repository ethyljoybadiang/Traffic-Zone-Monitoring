# Performance Monitoring Guide - ALAM Vehicle Counting System

## Overview

The `performance_monitor.py` module provides comprehensive performance measurement for your video processing pipeline, tracking **8 categories of metrics** across **40+ individual measurements**.

---

## 📋 Metrics Collected

### ⚡ 1. Core Speed Metrics
Fundamental performance indicators for frame processing.

| Metric | Unit | Description |
|--------|------|-------------|
| **Current FPS** | frames/sec | Most recent frame rate |
| **Average FPS** | frames/sec | Mean FPS over monitoring period |
| **FPS Range** | frames/sec | Min and max FPS observed |
| **FPS Stability (Stdev)** | - | Standard deviation (lower = more stable) |
| **Avg Latency** | ms/frame | Average time to process one frame |
| **Latency Range** | ms/frame | Min and max frame processing time |

**Target**: 60+ FPS with low latency variance (stdev < 5)

---

### 🧠 2. Pipeline Timing Metrics
Breakdown of time spent in each stage of processing.

| Metric | Unit | Description |
|--------|------|-------------|
| **Preprocessing Avg** | ms | Image resizing, cropping, normalization |
| **Detection Avg** | ms | YOLO model inference time |
| **Tracking Avg** | ms | Tracker update (SORT, ByteTrack, etc) |
| **Postprocessing Avg** | ms | Drawing boxes, labels, overlays |
| **Total Pipeline** | ms | Sum of all stages (should < 16.67ms for 60FPS) |

**Bottleneck Identification**: Which stage takes the most time?
- Detection > 12ms → Consider smaller model or lower confidence
- Preprocessing > 3ms → Optimize resizing algorithm
- Postprocessing > 2ms → Reduce drawing complexity

---

### 📉 3. Throughput Metrics
How much data is being processed and at what rate.

| Metric | Unit | Description |
|--------|------|-------------|
| **Effective FPS** | frames/sec | Frames processed per second (excluding skips) |
| **Total Frames Read** | count | Total frames from video file |
| **Frames Processed** | count | Frames actually analyzed |
| **Frames Skipped** | count | Frames discarded (not read) |
| **Frame Skip Rate** | percentage | Proportion of frames skipped |
| **Real-Time Factor (RTF)** | ratio | processing_time ÷ video_duration |

**Interpretation**:
- RTF = 0.5 → Runs 2x faster than video
- RTF = 1.0 → Real-time (same speed as video)
- RTF = 2.0 → Runs 2x slower than video

---

### 💻 4. Resource Usage Metrics
System resource consumption during processing.

| Metric | Unit | Description |
|--------|------|-------------|
| **CPU Usage Avg** | % | Average processor utilization |
| **CPU Usage Max** | % | Peak CPU usage observed |
| **RAM Usage Avg** | MB | Average memory consumption |
| **RAM Usage Max** | MB | Peak memory used |
| **GPU Utilization Avg** | % | Average GPU compute utilization |
| **VRAM Usage Avg** | GB | Average GPU memory consumption |
| **VRAM Usage Max** | GB | Peak GPU memory used |

**Health Indicators**:
- CPU > 90% → Risk of thermal throttling or lag spikes
- RAM > 80% of available → Risk of slowdown or crash
- GPU > 95% → Full utilization, good scaling
- VRAM > 95% of available → Risk of out-of-memory

---

### 🚗 5. Tracking-Specific Metrics
Vehicle tracking and detection statistics.

| Metric | Unit | Description |
|--------|------|-------------|
| **Objects per Frame Avg** | count | Average vehicles detected per frame |
| **Objects per Frame Max** | count | Maximum vehicles in any single frame |
| **Total Objects Detected** | count | Cumulative detections across all frames |
| **Total Objects Tracked** | count | Total tracking updates performed |

**Analysis**:
- High variance → Indicates temporal inconsistency
- Objects detected/frame > 100 → May cause latency issues

---

### ⏱️ 6. Advanced Timing Metrics
Specialized timing indicators for optimization analysis.

| Metric | Unit | Description |
|--------|------|-------------|
| **Detection Frequency** | frames | How often detection runs (e.g., every 10 frames) |
| **Tracking Updates Total** | count | Total tracker updates |
| **Frame Skip Rate** | % | Percentage of frames not processed (skipped) |

**Optimization Insights**:
- Detection every 10 frames → 10% detection overhead
- High skip rate → More aggressive frame skipping
- Low skip rate → Processing most frames

---

### 📊 7. Input/Configuration Metrics
System configuration parameters affecting performance.

| Metric | Unit | Description |
|--------|------|-------------|
| **Input Resolution** | pixels | Video resolution (e.g., 1920×1080) |
| **Model Name** | - | YOLO model file (e.g., yolov8n.pt) |
| **Model Size** | - | Model variant (nano, small, medium, large, xlarge) |
| **ROI Count** | count | Number of regions of interest tracked |
| **Batch Size** | count | Frames processed together |

**Performance Impact**:
- 1920×1080 → ~2-3x slower than 640×360
- YOLOv8n → Fastest but less accurate
- YOLOv8s → Good balance
- YOLOv8m/l → Most accurate but slower
- ROI Count × 5ms → Additional latency per region

---

### 🧪 8. System-Level Metrics
Overall system performance indicators.

| Metric | Unit | Description |
|--------|------|-------------|
| **End-to-End Avg** | ms/frame | Total time from input frame to output |
| **Total Processing Time** | seconds | Cumulative time in processing loop |
| **Power Consumption** | watts | (Optional) System power draw |

---

## 🚀 Quick Start

### Installation

```bash
pip install psutil torch
# Optional (for GPU monitoring):
pip install nvidia-ml-py
```

### Basic Usage

```python
from performance_monitor import PerformanceMonitor

# Create monitor
pm = PerformanceMonitor()

# Configure
pm.set_input_config(
    resolution='1920x1080',
    model_name='yolov8n.pt',
    model_size='nano',
    roi_count=3
)

# Process frames
for frame in video:
    pm.start_frame_timer()
    
    with pm.timing_block('preprocessing'):
        # Your preprocessing code
        pass
    
    with pm.timing_block('detection'):
        # Your detection code
        pass
    
    with pm.timing_block('tracking'):
        # Your tracking code
        pass
    
    pm.record_detected_objects(object_count)
    pm.record_resource_usage()
    pm.end_frame_timer()

# Get results
pm.print_stats()
pm.save_stats()
```

---

## 📊 Output Files

### 1. **performance_YYYYMMDD_HHMMSS.json**
Summary statistics in JSON format.

```json
{
  "fps_current": 45.2,
  "fps_avg": 43.8,
  "fps_stdev": 2.1,
  "detection_ms_avg": 12.5,
  "cpu_usage_avg": 65.3,
  "vram_usage_avg_gb": 2.1,
  "effective_fps": 43.8,
  "rtf": 0.73,
  ...
}
```

### 2. **performance_YYYYMMDD_HHMMSS.csv**
Same statistics in CSV format for Excel/spreadsheet analysis.

### 3. **timings_YYYYMMDD_HHMMSS.csv**
Frame-by-frame detailed timings for in-depth analysis.

```csv
Frame,FPS,Frame_Time_ms,Preprocess_ms,Detection_ms,Tracking_ms,Postprocess_ms,CPU%,RAM_MB,GPU%,VRAM_GB,Objects_Count
0,42.5,23.5,1.2,15.3,2.1,0.8,62.1,1024.5,85.2,1.5,12
1,44.1,22.7,1.1,14.9,2.0,0.7,61.8,1024.3,84.9,1.5,11
...
```

---

## 🔍 Analysis Examples

### Example 1: Identify Bottleneck

```
Detection Avg: 14.2 ms  ← BOTTLENECK (60% of budget)
Preprocessing: 1.5 ms   ← OK
Tracking: 2.1 ms        ← OK
Postprocessing: 0.8 ms  ← OK
Total: 18.6 ms          ← EXCEEDS 16.67ms budget

Action: Use smaller YOLO model (nano vs small)
```

### Example 2: Frame Skip Effectiveness

```
Before (no skip):
FPS: 12 | Latency: 83ms | Total Frames: 300

After (every 10th):
FPS: 85 | Latency: 11.7ms | Total Frames: 300, Processed: 30

Improvement: 7x faster display, similar detection coverage
```

### Example 3: Resource Constraints

```
CPU: 98%  ← Near limit
GPU: 15%  ← Underutilized
RAM: 75%  ← Acceptable
VRAM: 8%  ← Plenty available

Action: Offload more work to GPU (increase batch size or model complexity)
```

---

## 📈 Performance Benchmarks

### High Performance (Target)
- FPS: 60+
- Latency: < 16.67 ms
- RTF: < 0.5
- CPU: 50-80%
- VRAM: < 4GB

### Good Performance
- FPS: 30-60
- Latency: 16.67 - 33 ms
- RTF: 0.5 - 1.0
- CPU: 60-90%
- VRAM: 2-6GB

### Acceptable Performance
- FPS: 15-30
- Latency: 33 - 67 ms
- RTF: 1.0 - 2.0
- CPU: 80-95%
- VRAM: 4-8GB

### Poor Performance (Needs Optimization)
- FPS: < 15
- Latency: > 67 ms
- RTF: > 2.0
- CPU: > 95%
- VRAM: > 90% of available

---

## 🛠️ Optimization Tips

### If Detection is too slow:
1. Use smaller YOLO model (nano instead of small)
2. Lower confidence threshold
3. Reduce input resolution
4. Skip frames more aggressively

### If Preprocessing is too slow:
1. Reduce input resolution earlier
2. Use GPU-accelerated resize (CUDA)
3. Cache resized frames

### If Tracking is too slow:
1. Reduce number of regions
2. Use simpler tracking algorithm
3. Process fewer frames

### If Memory usage is high:
1. Reduce frame cache size
2. Process frames one at a time (no batching)
3. Use smaller model

### If GPU is underutilized:
1. Increase batch processing
2. Use larger model with GPU acceleration
3. Enable GPU preprocessing

---

## 📝 Integration with mainwindow.py

See `integration_example.py` for detailed code examples showing exactly where to add monitoring calls in the main application.

Key integration points:
1. `__init__` - Create monitor
2. `select_model()` - Record model config
3. `select_video()` - Record video resolution
4. `start_tracking()` - Start monitoring
5. `update_frame()` - Wrap pipeline blocks with timing
6. `stop_tracking()` - Print and save reports

---

## 🔧 Advanced Features

### Custom Timing Blocks
```python
with pm.timing_block('my_custom_step'):
    # Your code here
    pass
```

### Intermediate Reporting
```python
# Print stats after every 100 frames
if frame_count % 100 == 0:
    pm.print_stats()
```

### CSV Export for Analysis
```python
csv_path = pm.save_detailed_timings(filename='run_2024')
# Import into Excel/Python/Pandas for analysis
```

---

## 📞 Troubleshooting

**Problem: VRAM shows 0**
- Solution: Install `nvidia-ml-py` or use CUDA without monitoring

**Problem: CPU shows 0%**
- Solution: Interval=0.1 may be too fast; try interval=0.5

**Problem: FPS spikes (high variance)**
- Solution: Normal with frame skipping; check individual frame timings CSV

**Problem: Files not saving**
- Solution: Ensure `performance_logs/` directory is writable

---

## 📚 References

- YOLO Performance: https://docs.ultralytics.com/
- Real-Time Factor: https://en.wikipedia.org/wiki/Real-time_processing
- GPU Memory Profiling: https://pytorch.org/docs/stable/cuda.html

---

## License

Same as ALAM project

---

**Last Updated**: March 31, 2026
**Version**: 1.0
