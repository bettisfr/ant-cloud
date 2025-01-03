from flask import Flask, request, render_template, jsonify
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
CURRENT_IMAGE_FILE = os.path.join(UPLOAD_FOLDER, 'current_image.txt')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


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
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Update current image file
        with open(CURRENT_IMAGE_FILE, 'w') as f:
            f.write(filename)

        return 'Image received and updated successfully', 200
    return 'Invalid file type', 400


@app.route('/uploaded_images')
def uploaded_images():
    # List all image files in the upload folder
    images = [f for f in os.listdir(UPLOAD_FOLDER) if allowed_file(f)]

    # Sort images alphabetically by filename
    sorted_images = sorted(images, reverse=True)

    return jsonify(sorted_images)


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True, threaded=False)
