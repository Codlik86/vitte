#!/usr/bin/env python3
"""
Web-based Image Cropper for 736x414
Open in browser: http://localhost:5000
"""

from flask import Flask, render_template_string, request, send_file, jsonify
from PIL import Image
import os
import base64
from io import BytesIO
from pathlib import Path

app = Flask(__name__)

# Configuration
IMAGE_DIR = Path(__file__).parent
OUTPUT_DIR = IMAGE_DIR / "cropped_736x414"
OUTPUT_DIR.mkdir(exist_ok=True)

TARGET_WIDTH = 736
TARGET_HEIGHT = 414

# Get all images
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
IMAGES = sorted([
    f.name for f in IMAGE_DIR.iterdir()
    if f.suffix.lower() in IMAGE_EXTENSIONS and f.name not in ['crop_tool.py', 'crop_web.py']
])

HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Story Card Cropper - 736x414</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: Arial, sans-serif;
            background: #1a1a1a;
            color: white;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding: 15px;
            background: #2a2a2a;
            border-radius: 8px;
        }
        .filename { font-size: 18px; font-weight: bold; color: #4CAF50; }
        .progress { font-size: 14px; color: #888; }
        .canvas-container {
            position: relative;
            display: inline-block;
            background: #000;
            border: 2px solid #4CAF50;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 20px;
        }
        canvas {
            display: block;
            cursor: move;
        }
        .crop-overlay {
            position: absolute;
            border: 3px solid #00ff00;
            pointer-events: none;
            box-shadow: 0 0 0 9999px rgba(0,0,0,0.5);
        }
        .crop-label {
            position: absolute;
            background: #00ff00;
            color: #000;
            padding: 5px 10px;
            font-weight: bold;
            font-size: 14px;
            border-radius: 4px;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }
        button {
            padding: 12px 24px;
            font-size: 16px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: bold;
            transition: all 0.2s;
        }
        button:hover { transform: scale(1.05); }
        .btn-save { background: #4CAF50; color: white; }
        .btn-skip { background: #FF9800; color: white; }
        .btn-prev { background: #2196F3; color: white; }
        .btn-cancel { background: #f44336; color: white; }
        .instructions {
            background: #2a2a2a;
            padding: 15px;
            border-radius: 6px;
            margin-bottom: 20px;
        }
        .instructions h3 { margin-bottom: 10px; color: #4CAF50; }
        .instructions ul { margin-left: 20px; }
        .instructions li { margin: 5px 0; }
        .message {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            background: #4CAF50;
            color: white;
            border-radius: 6px;
            font-weight: bold;
            display: none;
            z-index: 1000;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="filename" id="filename">📷 Loading...</div>
            <div class="progress" id="progress">0 / 0</div>
        </div>

        <div class="instructions">
            <h3>📌 Инструкция:</h3>
            <ul>
                <li>🖱️ Кликай и тяни мышкой по картинке, чтобы двигать зелёную рамку</li>
                <li>⌨️ Используй стрелки на клавиатуре для точной настройки</li>
                <li>✅ Нажми "Save & Next" чтобы сохранить и перейти к следующей</li>
                <li>⏭️ "Skip" - пропустить без сохранения</li>
            </ul>
        </div>

        <div class="canvas-container" id="canvas-container">
            <canvas id="canvas"></canvas>
            <div class="crop-overlay" id="crop-overlay"></div>
            <div class="crop-label" id="crop-label">736 × 414</div>
        </div>

        <div class="controls">
            <button class="btn-prev" onclick="prevImage()">◀ Previous</button>
            <button class="btn-save" onclick="saveAndNext()">✓ Save & Next</button>
            <button class="btn-skip" onclick="nextImage()">Skip ▶</button>
        </div>
    </div>

    <div class="message" id="message"></div>

    <script>
        let currentIndex = 0;
        let images = {{ images | tojson }};
        let currentImage = null;
        let canvas = document.getElementById('canvas');
        let ctx = canvas.getContext('2d');
        let cropX = 0;
        let cropY = 0;
        let isDragging = false;
        let dragStartX = 0;
        let dragStartY = 0;
        let dragCropX = 0;
        let dragCropY = 0;

        const TARGET_WIDTH = 736;
        const TARGET_HEIGHT = 414;

        function loadImage(index) {
            if (index < 0 || index >= images.length) return;

            currentIndex = index;
            document.getElementById('filename').textContent = '📷 ' + images[index];
            document.getElementById('progress').textContent = `${index + 1} / ${images.length}`;

            let img = new Image();
            img.onload = function() {
                currentImage = img;

                // Scale to fit screen
                let maxWidth = window.innerWidth - 100;
                let maxHeight = window.innerHeight - 400;
                let scale = Math.min(maxWidth / img.width, maxHeight / img.height, 1.0);

                canvas.width = img.width * scale;
                canvas.height = img.height * scale;

                // Center crop initially
                cropX = Math.max(0, (img.width - TARGET_WIDTH) / 2);
                cropY = Math.max(0, (img.height - TARGET_HEIGHT) / 2);

                drawImage();
            };
            img.src = '/image/' + encodeURIComponent(images[index]);
        }

        function drawImage() {
            if (!currentImage) return;

            let scale = canvas.width / currentImage.width;

            // Draw image
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(currentImage, 0, 0, canvas.width, canvas.height);

            // Update overlay
            let x1 = cropX * scale;
            let y1 = cropY * scale;
            let x2 = (cropX + TARGET_WIDTH) * scale;
            let y2 = (cropY + TARGET_HEIGHT) * scale;

            let overlay = document.getElementById('crop-overlay');
            overlay.style.left = x1 + 'px';
            overlay.style.top = y1 + 'px';
            overlay.style.width = (x2 - x1) + 'px';
            overlay.style.height = (y2 - y1) + 'px';

            let label = document.getElementById('crop-label');
            label.style.left = (x1 + 10) + 'px';
            label.style.top = (y1 + 10) + 'px';
        }

        function constrainCrop() {
            cropX = Math.max(0, Math.min(cropX, currentImage.width - TARGET_WIDTH));
            cropY = Math.max(0, Math.min(cropY, currentImage.height - TARGET_HEIGHT));
        }

        // Mouse events
        canvas.addEventListener('mousedown', (e) => {
            isDragging = true;
            let rect = canvas.getBoundingClientRect();
            dragStartX = e.clientX - rect.left;
            dragStartY = e.clientY - rect.top;
            dragCropX = cropX;
            dragCropY = cropY;
        });

        canvas.addEventListener('mousemove', (e) => {
            if (!isDragging) return;

            let rect = canvas.getBoundingClientRect();
            let mouseX = e.clientX - rect.left;
            let mouseY = e.clientY - rect.top;

            let scale = canvas.width / currentImage.width;
            let dx = (mouseX - dragStartX) / scale;
            let dy = (mouseY - dragStartY) / scale;

            cropX = dragCropX + dx;
            cropY = dragCropY + dy;

            constrainCrop();
            drawImage();
        });

        canvas.addEventListener('mouseup', () => {
            isDragging = false;
        });

        // Keyboard events
        document.addEventListener('keydown', (e) => {
            let moved = false;
            if (e.key === 'ArrowUp') { cropY -= 10; moved = true; }
            if (e.key === 'ArrowDown') { cropY += 10; moved = true; }
            if (e.key === 'ArrowLeft') { cropX -= 10; moved = true; }
            if (e.key === 'ArrowRight') { cropX += 10; moved = true; }

            if (moved) {
                e.preventDefault();
                constrainCrop();
                drawImage();
            }
        });

        function showMessage(text, color = '#4CAF50') {
            let msg = document.getElementById('message');
            msg.textContent = text;
            msg.style.background = color;
            msg.style.display = 'block';
            setTimeout(() => { msg.style.display = 'none'; }, 2000);
        }

        function saveAndNext() {
            fetch('/save', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    filename: images[currentIndex],
                    cropX: Math.round(cropX),
                    cropY: Math.round(cropY)
                })
            })
            .then(r => r.json())
            .then(data => {
                showMessage('✓ Saved!');
                if (currentIndex < images.length - 1) {
                    loadImage(currentIndex + 1);
                } else {
                    showMessage('🎉 All done!', '#FF9800');
                }
            });
        }

        function nextImage() {
            if (currentIndex < images.length - 1) {
                loadImage(currentIndex + 1);
            }
        }

        function prevImage() {
            if (currentIndex > 0) {
                loadImage(currentIndex - 1);
            }
        }

        // Start
        loadImage(0);
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE, images=IMAGES)

@app.route('/image/<path:filename>')
def get_image(filename):
    return send_file(IMAGE_DIR / filename)

@app.route('/save', methods=['POST'])
def save_crop():
    data = request.json
    filename = data['filename']
    crop_x = int(data['cropX'])
    crop_y = int(data['cropY'])

    # Load and crop
    img = Image.open(IMAGE_DIR / filename)
    cropped = img.crop((crop_x, crop_y, crop_x + TARGET_WIDTH, crop_y + TARGET_HEIGHT))

    # Save
    output_file = OUTPUT_DIR / filename
    cropped.save(output_file, quality=95)

    print(f"✓ Saved: {filename}")

    return jsonify({'success': True})

if __name__ == '__main__':
    print(f"\n🌐 Starting web cropper...")
    print(f"📂 Found {len(IMAGES)} images")
    print(f"💾 Output: {OUTPUT_DIR}")
    print(f"\n🔗 Open in browser: http://localhost:5000\n")
    app.run(debug=False, port=5000)
