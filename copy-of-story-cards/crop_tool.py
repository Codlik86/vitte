#!/usr/bin/env python3
"""
Interactive Image Cropper
Crop images to 736x414 with manual positioning
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from pathlib import Path

class ImageCropper:
    def __init__(self, root, image_files, output_dir):
        self.root = root
        self.root.title("Story Card Cropper - 736x414")

        self.image_files = image_files
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.current_index = 0
        self.crop_x = 0
        self.crop_y = 0
        self.target_width = 736
        self.target_height = 414

        # Setup UI
        self.setup_ui()

        # Load first image
        self.load_current_image()

    def setup_ui(self):
        # Top info bar
        info_frame = tk.Frame(self.root)
        info_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)

        self.info_label = tk.Label(info_frame, text="", font=("Arial", 12))
        self.info_label.pack(side=tk.LEFT)

        self.progress_label = tk.Label(info_frame, text="", font=("Arial", 10))
        self.progress_label.pack(side=tk.RIGHT)

        # Canvas for image display
        self.canvas = tk.Canvas(self.root, bg='gray', cursor='crosshair')
        self.canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Bind mouse events for dragging
        self.canvas.bind('<Button-1>', self.on_mouse_down)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_mouse_up)

        # Bind arrow keys for fine adjustment
        self.root.bind('<Up>', lambda e: self.adjust_crop(0, -10))
        self.root.bind('<Down>', lambda e: self.adjust_crop(0, 10))
        self.root.bind('<Left>', lambda e: self.adjust_crop(-10, 0))
        self.root.bind('<Right>', lambda e: self.adjust_crop(10, 0))

        # Bottom control buttons
        button_frame = tk.Frame(self.root)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=10)

        tk.Button(button_frame, text="◀ Previous", command=self.prev_image,
                 font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="✓ Save & Next", command=self.save_and_next,
                 font=("Arial", 11, "bold"), width=15, bg='lightgreen').pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="Skip ▶", command=self.next_image,
                 font=("Arial", 11), width=12).pack(side=tk.LEFT, padx=5)

        tk.Button(button_frame, text="✕ Cancel", command=self.root.quit,
                 font=("Arial", 11), width=12, bg='lightcoral').pack(side=tk.RIGHT, padx=5)

        # Instructions
        help_text = "📌 Click and drag to move crop area | Arrow keys for fine adjustment"
        tk.Label(self.root, text=help_text, font=("Arial", 9), fg="blue").pack(side=tk.BOTTOM, pady=5)

    def load_current_image(self):
        if self.current_index >= len(self.image_files):
            messagebox.showinfo("Done", "All images processed!")
            self.root.quit()
            return

        self.current_file = self.image_files[self.current_index]
        self.original_image = Image.open(self.current_file)

        # Update info
        filename = os.path.basename(self.current_file)
        self.info_label.config(text=f"📷 {filename}")
        self.progress_label.config(text=f"{self.current_index + 1} / {len(self.image_files)}")

        # Calculate display size (fit to screen)
        screen_width = self.root.winfo_screenwidth() - 100
        screen_height = self.root.winfo_screenheight() - 300

        img_width, img_height = self.original_image.size
        scale = min(screen_width / img_width, screen_height / img_height, 1.0)

        self.display_width = int(img_width * scale)
        self.display_height = int(img_height * scale)
        self.scale = scale

        # Resize for display
        self.display_image = self.original_image.resize(
            (self.display_width, self.display_height),
            Image.Resampling.LANCZOS
        )

        # Center crop initially
        self.crop_x = max(0, (img_width - self.target_width) // 2)
        self.crop_y = max(0, (img_height - self.target_height) // 2)

        # Update canvas size
        self.canvas.config(width=self.display_width, height=self.display_height)

        # Draw
        self.draw_image()

    def draw_image(self):
        self.canvas.delete("all")

        # Display image
        self.photo = ImageTk.PhotoImage(self.display_image)
        self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)

        # Draw crop rectangle
        x1 = int(self.crop_x * self.scale)
        y1 = int(self.crop_y * self.scale)
        x2 = int((self.crop_x + self.target_width) * self.scale)
        y2 = int((self.crop_y + self.target_height) * self.scale)

        # Darken areas outside crop
        self.canvas.create_rectangle(0, 0, self.display_width, y1,
                                     fill='black', stipple='gray50', outline='')
        self.canvas.create_rectangle(0, y2, self.display_width, self.display_height,
                                     fill='black', stipple='gray50', outline='')
        self.canvas.create_rectangle(0, y1, x1, y2,
                                     fill='black', stipple='gray50', outline='')
        self.canvas.create_rectangle(x2, y1, self.display_width, y2,
                                     fill='black', stipple='gray50', outline='')

        # Draw crop rectangle
        self.canvas.create_rectangle(x1, y1, x2, y2,
                                     outline='lime', width=3)

        # Draw crop dimensions label
        self.canvas.create_text(x1 + 10, y1 + 10,
                               text=f"736 × 414",
                               anchor=tk.NW, fill='lime',
                               font=("Arial", 14, "bold"))

    def on_mouse_down(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        self.drag_crop_x = self.crop_x
        self.drag_crop_y = self.crop_y

    def on_mouse_drag(self, event):
        dx = (event.x - self.drag_start_x) / self.scale
        dy = (event.y - self.drag_start_y) / self.scale

        self.crop_x = self.drag_crop_x + int(dx)
        self.crop_y = self.drag_crop_y + int(dy)

        self.constrain_crop()
        self.draw_image()

    def on_mouse_up(self, event):
        pass

    def adjust_crop(self, dx, dy):
        self.crop_x += dx
        self.crop_y += dy
        self.constrain_crop()
        self.draw_image()

    def constrain_crop(self):
        img_width, img_height = self.original_image.size

        self.crop_x = max(0, min(self.crop_x, img_width - self.target_width))
        self.crop_y = max(0, min(self.crop_y, img_height - self.target_height))

    def save_and_next(self):
        # Crop the original image
        cropped = self.original_image.crop((
            self.crop_x,
            self.crop_y,
            self.crop_x + self.target_width,
            self.crop_y + self.target_height
        ))

        # Save to output directory
        output_file = self.output_dir / os.path.basename(self.current_file)
        cropped.save(output_file, quality=95)

        print(f"✓ Saved: {output_file}")

        # Next image
        self.current_index += 1
        self.load_current_image()

    def next_image(self):
        print(f"⊘ Skipped: {os.path.basename(self.current_file)}")
        self.current_index += 1
        self.load_current_image()

    def prev_image(self):
        if self.current_index > 0:
            self.current_index -= 1
            self.load_current_image()


def main():
    # Get all images in current directory
    current_dir = Path(__file__).parent
    image_extensions = {'.jpg', '.jpeg', '.png'}

    image_files = sorted([
        f for f in current_dir.iterdir()
        if f.suffix.lower() in image_extensions and f.name != 'crop_tool.py'
    ])

    if not image_files:
        print("No images found in directory!")
        return

    # Create output directory
    output_dir = current_dir / "cropped_736x414"

    print(f"Found {len(image_files)} images")
    print(f"Output directory: {output_dir}")
    print("\nStarting cropper...\n")

    # Create GUI
    root = tk.Tk()
    root.geometry("1200x800")
    app = ImageCropper(root, image_files, output_dir)
    root.mainloop()

    print("\n✓ Done!")


if __name__ == "__main__":
    main()
