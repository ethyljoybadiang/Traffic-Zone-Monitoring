import os
import argparse
import subprocess
from ultralytics import YOLO

def export_onnx(model_path):
    """Export the YOLO model to ONNX format."""
    print(f"\n--- Exporting {model_path} to ONNX ---")
    try:
        model = YOLO(model_path)
        # dynamic=True allows for dynamic input sizes, but static is often preferred for TensorRT/Hailo
        path = model.export(format='onnx', imgsz=640)
        print(f"Successfully exported to ONNX: {path}")
        return path
    except Exception as e:
        print(f"Error exporting to ONNX: {e}")
        return None

def export_engine(model_path, workspace=4, half=True):
    """Export the YOLO model to TensorRT Engine."""
    print(f"\n--- Exporting {model_path} to TensorRT Engine ---")
    print("Note: This requires TensorRT to be installed on your system.")
    try:
        model = YOLO(model_path)
        # half=True uses FP16 for faster inference, workspace is memory in GB
        path = model.export(format='engine', imgsz=640, device=0, half=half, workspace=workspace)
        print(f"Successfully exported to TensorRT Engine: {path}")
        return path
    except Exception as e:
        print(f"Error exporting to TensorRT Engine: {e}")
        return None

def compile_hef(onnx_path):
    """
    Compile the ONNX model to Hailo Executable Format (HEF).
    This process requires the Hailo Dataflow Compiler (HDC) to be installed.
    """
    print(f"\n--- Compiling {onnx_path} to Hailo HEF ---")
    print("Note: This step requires the Hailo AI Software Suite (Hailo Dataflow Compiler) to be installed.")
    
    if not onnx_path or not os.path.exists(onnx_path):
        print(f"Error: ONNX file '{onnx_path}' not found. You must export to ONNX first.")
        return

    base_name = os.path.splitext(onnx_path)[0]
    har_path = f"{base_name}.har"
    quantized_har_path = f"{base_name}_quantized.har"
    hef_path = f"{base_name}.hef"

    # Hailo CLI Commands
    # 1. Parse the ONNX model to Hailo Archive (HAR)
    parse_cmd = [
        "hailo", "parser", "onnx", onnx_path, 
        "--hw-arch", "hailo8", 
        "--net-name", "yolov8"
    ]
    
    # 2. Optimize and Quantize (Requires a calibration dataset in real scenarios)
    # Note: For accurate quantization, you should provide an info-file and calibration dataset.
    optimize_cmd = [
        "hailo", "optimize", har_path, 
        "--hw-arch", "hailo8", 
        "--use-random-calib-set"  # Using random data for demonstration. Replace with actual dataset in production.
    ]
    
    # 3. Compile to HEF
    compile_cmd = [
        "hailo", "compiler", quantized_har_path,
        "--hw-arch", "hailo8"
    ]

    try:
        print("Running Hailo Parser...")
        subprocess.run(parse_cmd, check=True)
        
        print("Running Hailo Optimizer...")
        subprocess.run(optimize_cmd, check=True)
        
        print("Running Hailo Compiler...")
        subprocess.run(compile_cmd, check=True)
        
        print(f"Successfully compiled to HEF: {hef_path}")
    except FileNotFoundError:
        print("Error: 'hailo' command not found. Please ensure Hailo Dataflow Compiler is installed and in your PATH.")
    except subprocess.CalledProcessError as e:
        print(f"Error during Hailo compilation step: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compile YOLO model to ONNX, TensorRT (Engine), and Hailo (HEF)")
    parser.add_argument("--model", type=str, default="yolov8n.pt", help="Path to the PyTorch (.pt) model")
    parser.add_argument("--onnx", action="store_true", help="Export to ONNX")
    parser.add_argument("--engine", action="store_true", help="Export to TensorRT Engine")
    parser.add_argument("--hef", action="store_true", help="Compile to Hailo HEF (requires ONNX)")
    parser.add_argument("--all", action="store_true", help="Export/Compile to all formats")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.model):
        print(f"Error: Model file '{args.model}' not found!")
        exit(1)
        
    onnx_output_path = None
    
    if args.onnx or args.all or args.hef:
        onnx_output_path = export_onnx(args.model)
        
    if args.engine or args.all:
        export_engine(args.model)
        
    if args.hef or args.all:
        if onnx_output_path:
            compile_hef(onnx_output_path)
        else:
            # If ONNX already exists in the same directory but we didn't export it in this run
            expected_onnx = args.model.replace('.pt', '.onnx')
            if os.path.exists(expected_onnx):
                compile_hef(expected_onnx)
            else:
                print("Failed to proceed with HEF compilation because ONNX model is missing.")
