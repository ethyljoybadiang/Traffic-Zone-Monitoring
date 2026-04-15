import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

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
