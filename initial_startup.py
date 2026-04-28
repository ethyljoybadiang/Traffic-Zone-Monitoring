import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui_tabs import setup_attributes_tab, setup_region_tab, setup_tracking_tab, setup_results_tab, setup_dashboard_tab
from video_engine import VideoEngine
import torch
import time
import os
from app_context import APPLICATION_PATH

def initial_ui(self):
    self.title("ALAM - Vehicle Counting System (Tkinter Version)")
    self.geometry("1280x800")
    self.resizable(True, True)
    
    # Initialize Core Engine
    self.video_engine = VideoEngine()

    # Configure colors
    self.bg_color = "#dcdcdc"
    self.configure(bg=self.bg_color)
    
    # Initialize variables
    self.points = []
    self.regions = []  # List of confirmed regions
    self.region_names = {}  # {region_idx: custom_name}
    self.dragging_point = None
    self.endpoint_radius = 10
    self.hover_point = None
    self.is_hovering_video = False
    
    # Video and model variables
    self.width = None
    self.height = None
    self.video_capture = None
    self.video_name = None
    self.first_frame = None
    self.model = None
    self.vehicles = None
    self.file_name = None
    self.interval = None
    self.vehicle_count = {}
    self.region_counts = {}  # Track counts per region: {region_idx: classwise_count}
    self.index = None
    
    # Vehicle class filtering
    self.allowed_vehicle_classes = self.video_engine.allowed_vehicle_classes
    self.region_colors = self.video_engine.region_colors
    self.region_filter = tk.StringVar(value="All Regions")
    
    # Tracking state
    self.tracking = False
    self.timer_id = None
    self.prev_frame_time = None
    self.photo = None
    self.canvas_width = None
    self.canvas_height = None
    self.frame_count = 0  # Frame counter for optimization
    self.fps_counter = 0
    self.fps_time = time.time()  # FPS tracking
    
    # Setup UI
    self.setup_ui()
    self.bind("<MouseWheel>", self.on_mousewheel)
    self.bind_all("<Return>", lambda e: self.set_line())
    self.bind_all("<Escape>", lambda e: self.cancel_plotting())

def setup_ui(self):
        """Setup the main user interface"""
        # Create main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Left panel - Video display
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        video_label = ttk.Label(left_frame, text="Video Preview", font=("Arial", 10, "bold"))
        video_label.pack(anchor=tk.W)
        
        # Canvas for video display
        self.video_canvas = tk.Canvas(
            left_frame, 
            bg="black", 
            width=800, 
            height=600,
            cursor="crosshair"
        )
        self.video_canvas.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        # Redraw last frame on resize (keeps aspect ratio via display_frame_on_canvas)
        self.video_canvas.bind("<Configure>", self.on_video_canvas_resize)
        self.video_canvas.bind("<Button-1>", self.on_video_click)
        self.video_canvas.bind("<Motion>", self.on_video_motion)
        self.video_canvas.bind("<ButtonRelease-1>", self.on_video_release)
        self.video_canvas.bind("<Enter>", self.on_video_enter)
        self.video_canvas.bind("<Leave>", self.on_video_leave)
        
        # Video Seek Slider Frame
        seek_frame = ttk.Frame(left_frame)
        seek_frame.pack(fill=tk.X, padx=5, pady=(5, 5))
        
        self.slider_var = tk.DoubleVar(value=0)
        self.is_manual_seek = False
        self.video_slider = ttk.Scale(
            seek_frame, 
            from_=0, 
            to=100, 
            orient=tk.HORIZONTAL, 
            variable=self.slider_var,
            command=self.on_slider_move,
            state=tk.DISABLED
        )
        self.video_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        
        self.frame_info_var = tk.StringVar(value="Frame: 0 / 0")
        ttk.Label(seek_frame, textvariable=self.frame_info_var, font=("Arial", 9, "bold"), foreground="blue").pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready. Select a model to begin.")
        status_bar = ttk.Label(
            left_frame, 
            textvariable=self.status_var, 
            relief=tk.SUNKEN,
            anchor=tk.W
        )
        status_bar.pack(fill=tk.X, padx=5, pady=5)
        
        # Right panel - Controls
        right_frame = ttk.Frame(main_frame, width=350)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, padx=5)
        right_frame.pack_propagate(False)
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Model & Video Selection
        tab1 = ttk.Frame(self.notebook)
        self.notebook.add(tab1, text="Attributes")
        setup_attributes_tab(self, tab1)
        
        # Tab 2: Line/Region Setting
        tab2 = ttk.Frame(self.notebook)
        self.notebook.add(tab2, text="Region Setup")
        setup_region_tab(self, tab2)

        # Tab 3: Tracking Control
        tab3 = ttk.Frame(self.notebook)
        self.notebook.add(tab3, text="Tracking")
        setup_tracking_tab(self, tab3)
        
        # Tab 4: Dashboard
        tab5 = ttk.Frame(self.notebook)
        self.notebook.add(tab5, text="Dashboard")
        setup_dashboard_tab(self, tab5)

        # Tab 5: Status & Results
        tab4 = ttk.Frame(self.notebook)
        self.notebook.add(tab4, text="Results")
        setup_results_tab(self, tab4)
        

def initialize_table(self):
    """Initialize counts and table for all regions"""
    if self.model:
        try:
            self.update_status("Initializing results table...")
            
            self.vehicles = {value: 0 for key, value in self.model.names.items()}
            self.index = list(self.vehicles.keys())
            
            # Initialize region counts storage
            self.region_counts = {}
            
            # Clear and populate table
            for item in self.table.get_children():
                self.table.delete(item)
            
            self.update_status("✓ Ready. Select a video and add tracking regions.")
            self.set_line_btn.config(state=tk.NORMAL)
            self.start_btn.config(state=tk.NORMAL)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to initialize: {str(e)}")
            self.update_status("✗ Initialization failed.")

        # SELECTION & LOADING    
    def select_model(self):
        """Select and load AI model"""
        file_name = filedialog.askopenfilename(
            title="Select Model",
            filetypes=[("All Supported Models", "*.pt *.pth *.xml *.onnx *.engine *.hef"), ("PyTorch Models", "*.pt *.pth"), ("OpenVINO Models", "*.xml"), ("ONNX Models", "*.onnx"), ("TensorRT Engine", "*.engine"), ("Hailo HEF", "*.hef"), ("All Files", "*.*")]
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
