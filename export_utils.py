import os
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from app_context import APPLICATION_PATH

def export_log_to_pdf(region_counts, region_names, allowed_vehicle_classes, application_path, status="N/A", timestamp="N/A"):
    """
    Handle the PDF export logic with regions as columns, vehicle classes as rows.
    region_counts: {region_idx: {class_name: count}}
    region_names: {region_idx: custom_name}
    allowed_vehicle_classes: set of class names to include
    """
    if not os.path.exists(os.path.join(application_path, 'Logs')):
        os.makedirs(os.path.join(application_path, 'Logs'))

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

    region_indices = sorted(region_counts.keys())
    col_headers = [region_names.get(i, f"Region {i + 1}") for i in region_indices]
    vehicles = sorted(allowed_vehicle_classes)

    # Build table: header row + one row per vehicle class
    header_row = ["Vehicle Class"] + col_headers
    data_rows = []
    for vehicle in vehicles:
        row = [vehicle.capitalize()]
        for idx in region_indices:
            count = region_counts.get(idx, {}).get(vehicle, 0)
            row.append(str(int(count)))
        data_rows.append(row)

    table = Table([header_row] + data_rows)
    elements.append(table)
    doc.build(elements)

    return log_file

class ExportMixin:
    def _rebuild_table_columns(self):
        """Rebuild the Treeview columns to match current regions."""
        region_indices = sorted(self.region_counts.keys()) if self.region_counts else []
        region_names = getattr(self, 'region_names', {})
        region_cols = [region_names.get(i, f"Region {i + 1}") for i in region_indices]

        columns = ("Vehicle",) + tuple(region_cols)
        self.table["columns"] = columns
        self.table["show"] = "headings"

        self.table.heading("Vehicle", text="Vehicle Class")
        self.table.column("Vehicle", width=100)
        for col in region_cols:
            self.table.heading(col, text=col)
            self.table.column(col, width=80)

        return region_indices, region_cols

    def update_table_data(self):
        """Update the results table: vehicle classes as rows, regions as columns."""
        if not self.region_counts:
            return

        # Clear existing rows
        for item in self.table.get_children():
            self.table.delete(item)

        region_indices, region_cols = self._rebuild_table_columns()
        region_names = getattr(self, 'region_names', {})

        # Apply region filter
        current_filter = self.region_filter.get()
        if current_filter != "All Regions":
            filtered = []
            for i in region_indices:
                name = region_names.get(i, f"Region {i + 1}")
                if name == current_filter:
                    filtered = [i]
                    break
            region_indices = filtered

        # Build one row per vehicle class
        for vehicle in self.index:
            vehicle_lower = vehicle.lower()
            if vehicle_lower not in self.allowed_vehicle_classes:
                continue

            row_values = [vehicle]
            has_data = False
            for idx in sorted(self.region_counts.keys()):
                if idx not in region_indices and current_filter != "All Regions":
                    continue
                count_value = self.region_counts.get(idx, {}).get(vehicle_lower, 0)
                if isinstance(count_value, dict):
                    inside = int(count_value.get('IN', 0))
                else:
                    inside = int(count_value)
                row_values.append(str(inside))
                if inside > 0:
                    has_data = True

            self.table.insert("", tk.END, values=tuple(row_values))

    def export_log(self):
        """Export tracking log as PDF using ExportUtils"""
        self.update_status("Exporting log...")
        
        if not self.file_name or not self.model:
            messagebox.showerror("Error", "Attributes not loaded.")
            self.update_status("✗ No tracking data to export.")
            return
        
        try:
            c_status = self.status_var.get() if hasattr(self, 'status_var') else "N/A"
            c_timestamp = self.timestamp_var.get() if hasattr(self, 'timestamp_var') else "00:00:00.00"
            region_names = getattr(self, 'region_names', {})

            log_file = export_log_to_pdf(
                self.region_counts,
                region_names,
                self.allowed_vehicle_classes,
                APPLICATION_PATH,
                status=c_status,
                timestamp=c_timestamp
            )
            
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
