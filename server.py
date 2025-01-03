from flask import Flask, request, render_template, jsonify, url_for
import os
from werkzeug.utils import secure_filename

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/uploaded_images', methods=['GET'])
def get_uploaded_images():
    images = os.listdir(app.config['UPLOAD_FOLDER'])
    return jsonify(images)

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
        return 'Image received and saved successfully', 200
    return 'Invalid file type', 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
