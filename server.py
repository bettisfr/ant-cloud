from flask import Flask, request, render_template, jsonify
from flask_socketio import SocketIO
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Configuration
UPLOAD_FOLDER = 'static/uploads'
CURRENT_IMAGE_FILE = os.path.join(UPLOAD_FOLDER, 'current_image.txt')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def get_sorted_images(image_folder):
    image_files = os.listdir(image_folder)

    image_files_with_timestamp = []
    for image in image_files:
        file_path = os.path.join(image_folder, image)
        modification_time = os.path.getmtime(file_path)
        image_files_with_timestamp.append((image, modification_time))

    sorted_images = sorted(image_files_with_timestamp, key=lambda x: x[1], reverse=True)

    sorted_image_filenames = [image for image, _ in sorted_images]
    return sorted_image_filenames


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/receive', methods=['POST'])
def receive_image():
    if 'image' not in request.files:
        return 'No image part', 400
    file = request.files['image']
    if file.filename == '':
        return 'No selected file', 400
    if file.filename.endswith('.jpg'):  # Only accept .jpg files
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Notify clients about the new image
        socketio.emit('new_image', {'filename': filename})

        return 'Image received and updated successfully', 200
    return 'Invalid file type', 400


@app.route('/uploaded_images')
def uploaded_images():
    sorted_images = get_sorted_images(UPLOAD_FOLDER)
    return jsonify(sorted_images)


@app.route('/get-images')
def get_images():
    sorted_images = get_sorted_images(UPLOAD_FOLDER)
    return jsonify(sorted_images)


if __name__ == '__main__':
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
