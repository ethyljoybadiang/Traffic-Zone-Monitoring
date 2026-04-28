import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from app_context import APPLICATION_PATH

def export_log_to_pdf(table_data, application_path, headers=None, status="N/A", timestamp="N/A"):
    """
    Handle the PDF export logic
    table_data: list of rows from the UI treeview
    application_path: base path of the app
    headers: list of column names
    """
    if not os.path.exists(os.path.join(application_path, 'Logs')):
        os.makedirs(os.path.join(application_path, 'Logs'))
    
    # We use the provided headers or fall back to a default
    if headers is None:
        num_cols = len(table_data[0]) if table_data else 1
        headers = ["Vehicle"] + [f"Region {i+1}" for i in range(num_cols - 1)]

    export_time_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f"Logs/Vehicle_Count_Log_{export_time_str}.pdf"
    file_path = os.path.join(application_path, log_file)
    
    doc = SimpleDocTemplate(file_path, pagesize=letter)
    styles = getSampleStyleSheet()
    
    export_time_formatted = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    elements = [
        Paragraph("Vehicle Count Log", styles['Title']),
        Paragraph(f"<b>Exported Date/Time:</b> {export_time_formatted}", styles['Normal']),
        Paragraph(f"<b>Video Timestamp:</b> {timestamp}", styles['Normal']),
        Paragraph(f"<b>System Status:</b> {status}", styles['Normal']),
        Paragraph("<br/><br/>", styles['Normal'])
    ]
    
    table = Table([headers] + table_data)
    elements.append(table)
    doc.build(elements)
    
    return log_file

class ExportMixin:
    def update_table_data(self):
        """Update the results table with a pivot view: Vehicles as rows, Regions as columns"""
        if not hasattr(self, 'region_counts'):
            return
            
        # Determine which regions to display as columns
        current_filter = self.region_filter.get()
        if current_filter == "All Regions":
            active_region_indices = list(range(len(self.regions)))
        else:
            try:
                region_num = int(current_filter.split()[-1]) - 1
                active_region_indices = [region_num] if 0 <= region_num < len(self.regions) else []
            except (ValueError, IndexError):
                active_region_indices = list(range(len(self.regions)))

        # 1. Update Columns dynamically
        column_names = ["Vehicle"] + [f"Region {i+1}" for i in active_region_indices]
        
        # We must re-configure columns if they don't match
        if list(self.table["columns"]) != column_names:
            self.table["columns"] = column_names
            for col in column_names:
                self.table.heading(col, text=col)
                self.table.column(col, width=120 if col == "Vehicle" else 90, anchor=tk.CENTER)

        # 2. Clear existing table
        for item in self.table.get_children():
            self.table.delete(item)

        # 3. Populate rows (Vehicles)
        if not hasattr(self, 'index') or not self.index:
            return

        for vehicle in self.index:
            vehicle_lower = vehicle.lower()
            if vehicle_lower not in self.allowed_vehicle_classes:
                continue
            
            row_values = [vehicle]
            for region_idx in active_region_indices:
                count = 0
                if region_idx in self.region_counts:
                    classwise = self.region_counts[region_idx]
                    if vehicle_lower in classwise:
                        val = classwise[vehicle_lower]
                        # NEW logic provides total inside count directly
                        count = int(val) if not isinstance(val, dict) else int(val.get('IN', 0))
                row_values.append(count)
            
            self.table.insert("", tk.END, values=row_values)

    def export_log(self):
        """Export tracking log as PDF using ExportUtils"""
        self.update_status("Exporting log...")
        
        if not self.file_name or not self.model:
            messagebox.showerror("Error", "Attributes not loaded.")
            self.update_status("✗ No tracking data to export.")
            return
        
        try:
            # Collect data from Table
            table_rows = []
            for item in self.table.get_children():
                table_rows.append(self.table.item(item)['values'])
            
            c_status = self.status_var.get() if hasattr(self, 'status_var') else "N/A"
            c_timestamp = self.timestamp_var.get() if hasattr(self, 'timestamp_var') else "00:00:00.00"
            
            # Get current headers from the table columns
            headers = [self.table.heading(col)["text"] for col in self.table["columns"]]
            
            log_file = export_log_to_pdf(table_rows, APPLICATION_PATH, headers=headers, status=c_status, timestamp=c_timestamp)
            
            if hasattr(self, 'log_file_var'):
                self.log_file_var.set(log_file)
            self.update_status("✓ Log exported successfully!")
            messagebox.showinfo("Success", f"Log exported: {log_file}")
            
        except Exception as e:
            print(f"Export Error: {e}")
            self.update_status("✗ Export failed.")
            messagebox.showerror("Error", f"Error exporting log: {str(e)}")

    def update_status(self, message):
        """Update status bar message"""
        self.status_var.set(message)
        self.update_idletasks()

    def on_slider_move(self, value):
        """Handle manual video seeking via slider"""
        if not self.video_capture or self.is_manual_seek:
            return
            
        # If tracking is active, pausing might be better, 
        # but let's allow seeking and see.
        frame_idx = int(float(value))
        self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        self.frame_count = frame_idx  # Keep internal counter synchronized
        self.refresh_video_display(reset=False)
        
        if hasattr(self, 'frame_info_var') and hasattr(self, 'total_frames'):
            self.frame_info_var.set(f"Frame: {frame_idx} / {self.total_frames}")
            
        self.update_status(f"Seeked to frame {frame_idx}")

    def on_mousewheel(self, event):
        """Handle mouse wheel events"""
        pass
