import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from app_context import APPLICATION_PATH

def export_log_to_pdf(table_data, application_path, status="N/A", timestamp="N/A"):
    """
    Handle the PDF export logic
    table_data: list of rows from the UI treeview
    application_path: base path of the app
    """
    if not os.path.exists(os.path.join(application_path, 'Logs')):
        os.makedirs(os.path.join(application_path, 'Logs'))
    
    # Filter for relevant classes (just in case)
    allowed_classes = {'person', 'bicycle', 'car', 'motorcycle', 'bus', 'truck'}
    log_data = []
    
    for row in table_data:
        if len(row) > 1:
            vehicle_class = row[1]
            if vehicle_class.lower() in allowed_classes:
                log_data.append(list(row))
    
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
    
    table = Table([["Region", "Vehicle", "In", "Out", "Inside"]] + log_data)
    elements.append(table)
    doc.build(elements)
    
    return log_file

class ExportMixin:
    def update_table_data(self):
        """Update the results table with per-region counts (filtered by class and region)"""
        if not self.region_counts:
            return
        
        # Clear existing table
        for item in self.table.get_children():
            self.table.delete(item)
        
        # Get filter selection
        current_filter = self.region_filter.get()
        
        # Determine which regions to display
        if current_filter == "All Regions":
            region_indices = sorted(self.region_counts.keys())
        else:
            # Extract region number from "Region X"
            try:
                region_num = int(current_filter.split()[-1]) - 1
                region_indices = [region_num] if region_num in self.region_counts else []
            except (ValueError, IndexError):
                region_indices = sorted(self.region_counts.keys())
        
        # Populate table with per-region data (only allowed vehicle classes)
        for region_idx in region_indices:
            if region_idx not in self.region_counts:
                continue
                
            classwise_count = self.region_counts[region_idx]
            region_label = f"Region {region_idx + 1}"
            region_color = self.region_colors[region_idx % len(self.region_colors)]
            
            # Only display allowed vehicle classes
            for vehicle in self.index:
                vehicle_lower = vehicle.lower()
                if vehicle_lower not in self.allowed_vehicle_classes:
                    continue
                    
                in_count = 0
                out_count = 0
                inside_count = 0
                
                # Check if we have counts for this vehicle in this region
                if vehicle_lower in classwise_count:
                    count_value = classwise_count[vehicle_lower]
                    if isinstance(count_value, dict):
                        # Legacy support just in case
                        in_count = int(count_value.get('IN', 0))
                        out_count = int(count_value.get('OUT', 0))
                    else:
                        # NEW optimized logic provides total inside count
                        inside_count = int(count_value)
                
                iid = self.table.insert("", tk.END, values=(region_label, vehicle, in_count, out_count, inside_count))
                
                # Apply tag with region color for highlighting
                tag_name = f"region_{region_idx}"
                self.table.tag_configure(tag_name, background='white')  # Light blue, green, etc. based on region
                self.table.item(iid, tags=(tag_name,))

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
            
            log_file = export_log_to_pdf(table_rows, APPLICATION_PATH, status=c_status, timestamp=c_timestamp)
            
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
