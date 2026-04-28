from PIL import Image, ImageTk, ImageDraw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class RegionsMixin:
    def display_frame_on_canvas(self, frame):
        """Display a frame on the canvas"""
        # Keep a reference to the last rendered frame so we can redraw on canvas resize.
        self._last_display_frame = frame
        
        # Convert to PIL Image
        pil_image = Image.fromarray(frame)
        
        # Scale to fit canvas
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width = 1024
            canvas_height = 768
            
        # Dynamically calculate ratio to allow both UP-scaling and DOWN-scaling to canvas edges
        img_w, img_h = pil_image.width, pil_image.height
        if img_w > 0 and img_h > 0:
            ratio = min(canvas_width / img_w, canvas_height / img_h)
            new_w, new_h = int(img_w * ratio), int(img_h * ratio)
            pil_image = pil_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        
        # Draw all confirmed regions
        if self.regions:
            draw = ImageDraw.Draw(pil_image, "RGBA")
            colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]
            for region_idx, region in enumerate(self.regions):
                if len(region) >= 3:
                    color = colors[region_idx % len(colors)]
                    points = [(int(p[0] * pil_image.width / self.width), int(p[1] * pil_image.height / self.height)) 
                                for p in region] if self.width and self.height else region
                    draw.polygon(points, fill=(*color, 50), outline=color)
        
        # Draw plotted points
        if self.points:
            draw = ImageDraw.Draw(pil_image)
            for pt in self.points:
                x = int(pt[0] * pil_image.width / self.width) if self.width else pt[0]
                y = int(pt[1] * pil_image.height / self.height) if self.height else pt[1]
                draw.ellipse([x-3, y-3, x+3, y+3], fill="red")
        
        # Convert to PhotoImage and display
        self.photo = ImageTk.PhotoImage(pil_image)
        
        # Calculate canvas offsets to center the image
        canvas_width = self.video_canvas.winfo_width()
        canvas_height = self.video_canvas.winfo_height()
        if canvas_width <= 1 or canvas_height <= 1:
            canvas_width, canvas_height = 1024, 768
            
        self.img_offset_x = (canvas_width - pil_image.width) // 2
        self.img_offset_y = (canvas_height - pil_image.height) // 2
        
        self.video_canvas.delete("all")
        self.video_canvas.create_image(self.img_offset_x, self.img_offset_y, anchor=tk.NW, image=self.photo)
        
        # Store scaled dimensions
        self.canvas_width = pil_image.width
        self.canvas_height = pil_image.height
        pass

    def on_video_canvas_resize(self, event):
        """Redraw the last frame when the canvas resizes (throttled)."""
        # During active tracking, frames are being redrawn continuously anyway.
        if getattr(self, "tracking", False):
            return

        if event.width <= 1 or event.height <= 1:
            return

        last_size = getattr(self, "_last_canvas_size", None)
        new_size = (event.width, event.height)
        if last_size == new_size:
            return
        self._last_canvas_size = new_size

        pending = getattr(self, "_canvas_resize_after_id", None)
        if pending is not None:
            try:
                self.after_cancel(pending)
            except Exception:
                pass

        self._canvas_resize_after_id = self.after(50, self._redraw_last_frame)

    def _redraw_last_frame(self):
        """Internal: redraw using the most recently displayed frame."""
        self._canvas_resize_after_id = None
        frame = getattr(self, "_last_display_frame", None)
        if frame is None:
            return
        self.display_frame_on_canvas(frame)

    def on_video_click(self, event):
        """Handle mouse click on video canvas"""
        self.video_canvas.focus_set()
        if True: # Removed hardcoded 4-point limit
            # Map canvas coordinates to original video coordinates
            if self.canvas_width and self.canvas_height:
                offset_x = getattr(self, 'img_offset_x', 0)
                offset_y = getattr(self, 'img_offset_y', 0)
                
                rel_x = event.x - offset_x
                rel_y = event.y - offset_y
                
                if 0 <= rel_x <= self.canvas_width and 0 <= rel_y <= self.canvas_height:
                    x = int(rel_x * self.width / self.canvas_width)
                    y = int(rel_y * self.height / self.canvas_height)
                else:
                    return # Ignore outside clicks
            else:
                x, y = event.x, event.y
            
            self.points.append((x, y))
            self.update_status(f"Point {len(self.points)} added. Click more points or press ENTER to close.")
            self.refresh_video_display()
        else:
            self.update_status("Region complete. Start plotting a new region by clicking 4 more points...")
        pass

    def on_video_motion(self, event):
        """Handle mouse motion on video canvas"""
        if True:
            if self.canvas_width and self.canvas_height:
                offset_x = getattr(self, 'img_offset_x', 0)
                offset_y = getattr(self, 'img_offset_y', 0)
                
                rel_x = event.x - offset_x
                rel_y = event.y - offset_y
                
                # Clamp coordinates to edge of image
                rel_x = max(0, min(rel_x, self.canvas_width))
                rel_y = max(0, min(rel_y, self.canvas_height))
                
                x = int(rel_x * self.width / self.canvas_width)
                y = int(rel_y * self.height / self.canvas_height)
            else:
                x, y = event.x, event.y
            
            self.hover_point = (x, y)
            regions_count = len(self.regions)
            self.update_status(f"Hover: ({x}, {y}) | Point {len(self.points) + 1} | Region {regions_count + 1} | ENTER to close")

    def on_video_enter(self, event):
        """Handle mouse entering video area"""
        self.is_hovering_video = True

    def on_video_leave(self, event):
        """Handle mouse leaving video area"""
        self.is_hovering_video = False
        self.hover_point = None

    def on_video_release(self, event):
        """Handle mouse release on video"""
        pass

    def sort_points_clockwise(self, pts):
        """Sort points in clockwise order using VideoEngine"""
        return self.video_engine.sort_points_clockwise(pts)

    def set_line(self):
        """Set tracking line/region from coordinates"""
        self.update_status("Validating coordinates...")
        
        if not self.video_capture and not self.model:
            messagebox.showerror("Error", "Load attributes first.")
            self.update_status("✗ Attributes not loaded.")
            return
            
        # Check if text variables are completely empty
        if not all([self.x1_var.get().strip(), self.x2_var.get().strip(), self.x3_var.get().strip(), self.x4_var.get().strip()]):
            if len(self.points) >= 3:
                self.confirm_plotted_points()
                return
            elif len(self.points) > 0:
                messagebox.showwarning("Incomplete", f"Please plot at least 3 points. You currently have {len(self.points)}.")
                return
            else:
                self.update_status("✗ Missing coordinates.")
                messagebox.showwarning("Notice", "Please either click 4 points directly on the video, or enter coordinates in the text boxes.")
                return
        
        try:
            def parse_point(text):
                parts = text.split(',')
                if len(parts) != 2:
                    raise ValueError("Invalid format")
                return int(parts[0].strip()), int(parts[1].strip())
            
            p1 = parse_point(self.x1_var.get())
            p2 = parse_point(self.x2_var.get())
            p3 = parse_point(self.x3_var.get())
            p4 = parse_point(self.x4_var.get())
            
            raw_points = [p1, p2, p3, p4]
            region = self.sort_points_clockwise(raw_points)
            
            # Add region to list
            self.regions.append(region)
            self.update_regions_listbox()
            
            self.update_status("✓ Region added successfully!")
            messagebox.showinfo("Success", f"Region {len(self.regions)} added.")
            
            if hasattr(self, 'notebook'):
                self.notebook.select(2)
            
            # Clear inputs
            self.x1_var.set("")
            self.x2_var.set("")
            self.x3_var.set("")
            self.x4_var.set("")
            
            if self.video_capture:
                self.refresh_video_display()
            
        except (ValueError, IndexError):
            self.update_status("✗ Invalid coordinate format.")
            messagebox.showerror("Error", "Please enter valid coordinates in 'x, y' format (e.g. 100, 200).")
        pass

    def confirm_plotted_points(self):
        """Confirm plotted points and add as new region"""
        if len(self.points) >= 3:
            region = self.points.copy() # Anti-bowtie: keeping order as clicked
            self.regions.append(region)
            self.update_regions_listbox()
            self.update_region_filter_combobox()
            self.points.clear()
            self.update_status(f"✓ Region {len(self.regions)} confirmed with {len(region)} points!")
            
            if hasattr(self, 'notebook'):
                self.notebook.select(2)
                
            self.refresh_video_display()
        elif len(self.points) > 0:
            messagebox.showwarning("Incomplete", f"Please plot at least 3 points. You have {len(self.points)}.")
        else:
            messagebox.showwarning("No Points", "Click points on the video first to plot a region.")
        pass

    def cancel_plotting(self):
        """Clear current points and cancel plotting"""
        if self.points:
            self.points.clear()
            self.update_status("Plotted points cleared.")
            self.refresh_video_display()
        else:
            self.update_status("Nothing to clear.")
        pass

    def add_new_region(self):
        """Explicitly add a new region from text input"""
        self.set_line()
        pass

    def remove_last_region(self):
        """Remove the last added region"""
        if self.regions:
            self.regions.pop()
            self.update_regions_listbox()
            self.update_region_filter_combobox()
            self.update_status(f"✓ Region removed. {len(self.regions)} region(s) remaining.")
            self.refresh_video_display()
        else:
            messagebox.showinfo("Info", "No regions to remove.")
        pass

    def clear_all_regions(self):
        """Clear all regions"""
        if self.regions:
            if messagebox.askyesno("Confirm", f"Clear all {len(self.regions)} region(s)?"):
                self.regions.clear()
                self.update_regions_listbox()
                self.update_region_filter_combobox()
                self.points.clear()
                self.update_status("✓ All regions cleared.")
                self.refresh_video_display()
        else:
            messagebox.showinfo("Info", "No regions to clear.")
        pass

    def show_region_context_menu(self, event):
        """Show right-click context menu in regions listbox"""
        try:
            self.regions_listbox.selection_clear(0, tk.END)
            self.regions_listbox.selection_set(self.regions_listbox.nearest(event.y))
            self.regions_listbox.activate(self.regions_listbox.nearest(event.y))
            self.region_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.region_menu.grab_release()
        pass

    def edit_selected_region(self):
        """Load selected region into the UI for modification"""
        selection = self.regions_listbox.curselection()
        if not selection: return
        index = selection[0]
        region = self.regions[index]
        
        # Auto-populate the active plotting points so users can edit visually
        self.points = list(region)
        
        # Populate the first 4 UI textboxes as courtesy, clearing others
        if len(region) >= 1: self.x1_var.set(f"{int(region[0][0])}, {int(region[0][1])}")
        else: self.x1_var.set("")
        if len(region) >= 2: self.x2_var.set(f"{int(region[1][0])}, {int(region[1][1])}")
        else: self.x2_var.set("")
        if len(region) >= 3: self.x3_var.set(f"{int(region[2][0])}, {int(region[2][1])}")
        else: self.x3_var.set("")
        if len(region) >= 4: self.x4_var.set(f"{int(region[3][0])}, {int(region[3][1])}")
        else: self.x4_var.set("")
            
        # Remove it from active lists while editing
        self.regions.pop(index)
        self.update_regions_listbox()
        self.update_region_filter_combobox()
        self.update_status(f"Region {index + 1} loaded for editing. Adjust points on canvas and press ENTER to close.")
        if self.video_capture:
            self.refresh_video_display()
        pass

    def delete_selected_region(self):
        """Delete the specifically targeted region with confirmation"""
        selection = self.regions_listbox.curselection()
        if not selection: return
        
        if not messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this region?"):
            return
            
        index = selection[0]
        self.regions.pop(index)
        self.update_regions_listbox()
        self.update_region_filter_combobox()
        self.update_status(f"✓ Region removed. {len(self.regions)} region(s) remaining.")
        if self.video_capture:
            self.refresh_video_display()
        pass

    def update_regions_listbox(self):
        """Update the regions listbox display"""
        self.regions_listbox.delete(0, tk.END)
        for i, region in enumerate(self.regions, 1):
            self.regions_listbox.insert(tk.END, f"Region {i}: {region}")
        pass

    def update_region_filter_combobox(self):
        """Update region filter combobox options"""
        if not hasattr(self, 'region_combo'):
            return  # Combobox not yet created
        region_options = ["All Regions"] + [f"Region {i + 1}" for i in range(len(self.regions))]
        self.region_combo['values'] = region_options
        self.region_combo.current(0)  # Reset to "All Regions"
        pass