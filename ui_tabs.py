import tkinter as tk
from tkinter import ttk

def setup_attributes_tab(app, parent):
    """Setup model and video selection tab"""
    frame = ttk.LabelFrame(parent, text="Attributes", padding=10)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Model selection
    ttk.Label(frame, text="AI Model:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.model_name_var = tk.StringVar(value="No model selected")
    ttk.Label(frame, textvariable=app.model_name_var, foreground="blue").pack(anchor=tk.W, padx=20)
    
    model_btn = ttk.Button(
        frame, 
        text="Select Model (.pt, .xml, .onnx, .engine, .hef)", 
        command=app.select_model
    )
    model_btn.pack(fill=tk.X, pady=5)
    
    # Video selection
    ttk.Label(frame, text="Video File:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.video_name_var = tk.StringVar(value="No video selected")
    ttk.Label(frame, textvariable=app.video_name_var, foreground="blue").pack(anchor=tk.W, padx=20)
    
    video_btn = ttk.Button(
        frame, 
        text="Select Video (.mp4, .avi)", 
        command=app.select_video,
        state=tk.DISABLED
    )
    video_btn.pack(fill=tk.X, pady=5)
    app.select_video_btn = video_btn
    
    # Video info
    ttk.Label(frame, text="Video Size:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.video_size_var = tk.StringVar(value="Not loaded")
    ttk.Label(frame, textvariable=app.video_size_var, foreground="green").pack(anchor=tk.W, padx=20)
    
    ttk.Label(frame, text="Model Name:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.ai_model_var = tk.StringVar(value="Not loaded")
    ttk.Label(frame, textvariable=app.ai_model_var, foreground="green").pack(anchor=tk.W, padx=20)
    
    # Reset Session Button
    ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=15)
    reset_btn = ttk.Button(
        frame, 
        text="🔄 Reset All Session", 
        command=app.reset_session
    )
    reset_btn.pack(fill=tk.X, pady=5)

def setup_region_tab(app, parent):
    """Setup region/line setting tab"""
    frame = ttk.LabelFrame(parent, text="Region Setup", padding=10)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    ttk.Label(frame, text="Enter 4 coordinates (x,y):", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=5)
    
    # Points
    app.x1_var = tk.StringVar()
    ttk.Label(frame, text="Point 1 (x, y):").pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=app.x1_var).pack(fill=tk.X, padx=20, pady=(0, 5))
    
    app.x2_var = tk.StringVar()
    ttk.Label(frame, text="Point 2 (x, y):").pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=app.x2_var).pack(fill=tk.X, padx=20, pady=(0, 5))
    
    app.x3_var = tk.StringVar()
    ttk.Label(frame, text="Point 3 (x, y):").pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=app.x3_var).pack(fill=tk.X, padx=20, pady=(0, 5))
    
    app.x4_var = tk.StringVar()
    ttk.Label(frame, text="Point 4 (x, y):").pack(anchor=tk.W)
    ttk.Entry(frame, textvariable=app.x4_var).pack(fill=tk.X, padx=20, pady=(0, 5))
    
    app.set_line_btn = ttk.Button(
        frame, 
        text="Set Tracking Area", 
        command=app.set_line,
        state=tk.DISABLED
    )
    app.set_line_btn.pack(fill=tk.X, pady=10)
    
    # Button row for region management
    btn_frame = ttk.Frame(frame)
    btn_frame.pack(fill=tk.X, pady=10)
    
    ttk.Button(btn_frame, text="Add Region", command=app.add_new_region).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Undo Last", command=app.remove_last_region).pack(side=tk.LEFT, padx=5)
    ttk.Button(btn_frame, text="Clear All", command=app.clear_all_regions).pack(side=tk.LEFT, padx=5)
    
    # Display coordinates
    ttk.Label(frame, text="Active Regions:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    
    # Listbox to show regions
    list_frame = ttk.Frame(frame)
    list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    app.regions_listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, height=6)
    app.regions_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.config(command=app.regions_listbox.yview)
    
    # Context menu for regions
    app.region_menu = tk.Menu(app, tearoff=0)
    app.region_menu.add_command(label="Edit Region", command=app.edit_selected_region)
    app.region_menu.add_command(label="Delete Region", command=app.delete_selected_region)
    app.regions_listbox.bind("<ButtonRelease-3>", app.show_region_context_menu)
    
    ttk.Label(
        frame, 
        text="Click multiple points on video to plot a region\nPress ENTER to close region | ESC to cancel",
        font=("Arial", 8, "italic"),
        foreground="blue"
    ).pack(anchor=tk.W, pady=(5, 0))

def setup_tracking_tab(app, parent):
    """Setup tracking control tab"""
    frame = ttk.LabelFrame(parent, text="Tracking Control", padding=5)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Start tracking button
    app.start_btn = ttk.Button(
        frame, 
        text="▶ Start Tracking", 
        command=app.start_tracking,
        state=tk.DISABLED
    )
    app.start_btn.pack(fill=tk.X, pady=5)
    
    # Stop tracking button
    app.stop_btn = ttk.Button(
        frame, 
        text="⏹ Stop Tracking", 
        command=app.stop_tracking,
        state=tk.DISABLED
    )
    app.stop_btn.pack(fill=tk.X, pady=5)
    
    # Status display
    ttk.Label(frame, text="Tracking Status:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.status_icon_var = tk.StringVar(value="⚪ Idle")
    ttk.Label(frame, textvariable=app.status_icon_var, foreground="red", font=("Arial", 10, "bold")).pack(anchor=tk.W, padx=20)
    
    # Timestamp
    ttk.Label(frame, text="Timestamp:", font=("Arial", 9, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.timestamp_var = tk.StringVar(value="00:00:00.00")
    ttk.Label(frame, textvariable=app.timestamp_var, font=("Arial", 10, "bold"), foreground="blue").pack(anchor=tk.W, padx=20)

def setup_results_tab(app, parent):
    """Setup results table tab with per-region tracking and filtering"""
    # Initialize variables used in this tab
    app.region_filter = tk.StringVar(value="All Regions")
    
    filter_frame = ttk.Frame(parent)
    filter_frame.pack(fill=tk.X, padx=5, pady=5)
    
    ttk.Label(filter_frame, text="Filter by Region:").pack(side=tk.LEFT, padx=5)
    app.region_combo = ttk.Combobox(
        filter_frame,
        textvariable=app.region_filter,
        values=["All Regions"],
        state="readonly",
        width=20
    )
    app.region_combo.pack(side=tk.LEFT, padx=5)
    app.region_combo.bind("<<ComboboxSelected>>", lambda e: app.update_table_data())
    
    frame = ttk.LabelFrame(parent, text="Vehicle Count Results (By Region)", padding=10)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    columns = ("Region", "Vehicle", "In", "Out", "Inside")
    app.table = ttk.Treeview(frame, columns=columns, height=15, show="headings", selectmode="browse")
    
    # Define columns
    col_widths = {"Region": 60, "Vehicle": 80, "In": 50, "Out": 50, "Inside": 50}
    for col, width in col_widths.items():
        app.table.column(col, width=width)
        app.table.heading(col, text=col)
    
    # Scrollbars
    v_scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=app.table.yview)
    h_scrollbar = ttk.Scrollbar(frame, orient=tk.HORIZONTAL, command=app.table.xview)
    app.table.configure(yscroll=v_scrollbar.set, xscroll=h_scrollbar.set)
    
    app.table.grid(row=0, column=0, sticky="nsew")
    v_scrollbar.grid(row=0, column=1, sticky="ns")
    h_scrollbar.grid(row=1, column=0, sticky="ew")
    
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)

    # Export controls at the bottom
    action_frame = ttk.Frame(parent)
    action_frame.pack(fill=tk.X, padx=5, pady=5)
    
    app.export_btn = ttk.Button(
        action_frame, 
        text="📄 Export Log (PDF)", 
        command=app.export_log,
        state=tk.DISABLED
    )
    app.export_btn.pack(side=tk.LEFT, padx=5)

    app.log_file_var = tk.StringVar(value="Not exported")
    ttk.Label(action_frame, text="Log File:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=(10, 5))
    ttk.Label(action_frame, textvariable=app.log_file_var, foreground="green").pack(side=tk.LEFT, padx=5)

def setup_dashboard_tab(app, parent):
    """Setup dashboard tab for system performance"""
    frame = ttk.LabelFrame(parent, text="System Performance Dashboard", padding=20)
    frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # FPS
    ttk.Label(frame, text="Current FPS:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(10, 5))
    app.fps_var = tk.StringVar(value="0.0")
    ttk.Label(frame, textvariable=app.fps_var, font=("Arial", 24, "bold"), foreground="purple").pack(anchor=tk.W, padx=20)

    # Total Count
    ttk.Label(frame, text="Total Vehicles Inside:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(20, 5))
    app.total_count_var = tk.StringVar(value="0")
    ttk.Label(frame, textvariable=app.total_count_var, font=("Arial", 28, "bold"), foreground="darkorange").pack(anchor=tk.W, padx=20)
    
    # Session Time
    ttk.Label(frame, text="Video Timestamp:", font=("Arial", 12, "bold")).pack(anchor=tk.W, pady=(20, 5))
    app.session_time_var = tk.StringVar(value="00:00:00")
    ttk.Label(frame, textvariable=app.session_time_var, font=("Arial", 16, "bold"), foreground="green").pack(anchor=tk.W, padx=20)

