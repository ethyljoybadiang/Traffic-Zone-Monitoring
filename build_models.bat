@echo off
echo ========================================================
echo Model Compilation Script for ONNX, TensorRT, and Hailo
echo ========================================================

REM Check if Python is installed
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in PATH.
    pause
    exit /b
)

echo.
echo Please select an option:
echo 1. Export to ONNX only
echo 2. Export to TensorRT Engine only
echo 3. Compile to Hailo HEF only (Requires ONNX model)
echo 4. Compile ALL (ONNX, Engine, HEF)
echo 5. Exit
echo.

set /p choice="Enter choice (1-5): "

REM Assume model name is yolov8n.pt by default, user can change this
set MODEL_NAME=yolov8n.pt

IF "%choice%"=="1" (
    python build_models.py --onnx --model %MODEL_NAME%
) ELSE IF "%choice%"=="2" (
    python build_models.py --engine --model %MODEL_NAME%
) ELSE IF "%choice%"=="3" (
    python build_models.py --hef --model %MODEL_NAME%
) ELSE IF "%choice%"=="4" (
    python build_models.py --all --model %MODEL_NAME%
) ELSE IF "%choice%"=="5" (
    exit /b
) ELSE (
    echo Invalid choice.
)

echo.
pause
