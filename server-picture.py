from flask import Flask, request, render_template, jsonify, send_file
from flask_socketio import SocketIO
import os
import io
import zipfile
from werkzeug.utils import secure_filename
import time
import piexif
from datetime import datetime


app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# Configuration
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
LABELS_FOLDER = 'static/labels'
os.makedirs(LABELS_FOLDER, exist_ok=True)


def to_gps_decimal(gps_data, ref):
    """Convert GPS EXIF format to decimal coordinates."""
    if not gps_data:
        return None

    degrees, minutes, seconds = gps_data
    decimal = degrees[0] / degrees[1] + (minutes[0] / minutes[1]) / 60 + (seconds[0] / seconds[1]) / 3600
    return -decimal if ref in ['S', 'W'] else decimal


def extract_metadata(image_path):
    """Extract metadata including temperature, humidity, and GPS from EXIF data."""
    try:
        exif_dict = piexif.load(image_path)
        gps_data = exif_dict.get("GPS", {})

        gps_latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
        gps_latitude_ref = gps_data.get(piexif.GPSIFD.GPSLatitudeRef, b'N').decode()

        gps_longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
        gps_longitude_ref = gps_data.get(piexif.GPSIFD.GPSLongitudeRef, b'E').decode()

        latitude = to_gps_decimal(gps_latitude, gps_latitude_ref) if gps_latitude else None
        longitude = to_gps_decimal(gps_longitude, gps_longitude_ref) if gps_longitude else None

        user_comment = exif_dict.get("0th", {}).get(piexif.ImageIFD.ImageDescription, b"").decode("utf-8").strip()

        metadata = {}
        for line in user_comment.splitlines():
            if "=" in line:
                no_space_line = line.replace(" ", "")
                split = no_space_line.split("|")
                for i in range(len(split)):
                    key, value = split[i].split("=")
                    metadata[key] = value


        temperature = metadata.get("Temperature", "N/A")
        pressure = metadata.get("Pressure", "N/A")
        humidity = metadata.get("Humidity", "N/A")

        return {
            "temperature": float(temperature) if temperature.replace(".", "", 1).isdigit() and float(temperature) != 0 else None,
            "pressure": float(pressure) if pressure.replace(".", "", 1).isdigit() and float(pressure) != 0 else None,
            "humidity": float(humidity) if humidity.replace(".", "", 1).isdigit() and float(humidity) != 0 else None,
            "latitude": round(latitude, 6) if latitude != 0 else None,
            "longitude": round(longitude, 6) if longitude != 0 else None,
            "user_comment": user_comment
        }


    except Exception as e:
        print(f"Error extracting metadata from {image_path}: {e}")
        return {}


def get_sorted_images(image_folder):
    """Retrieve images and sort them by modification time."""
    image_files = [f for f in os.listdir(image_folder) if f.lower().endswith((".jpg", ".jpeg"))]

    image_files_with_metadata = []
    for image in image_files:
        file_path = os.path.join(image_folder, image)

        metadata = extract_metadata(file_path)
        modification_time = os.path.getmtime(file_path)

        # Count labels, if a corresponding .txt exists
        base_name, _ = os.path.splitext(image)
        labels_path = os.path.join(LABELS_FOLDER, base_name + ".txt")
        labels_count = 0
        if os.path.exists(labels_path):
            with open(labels_path, "r") as lf:
                for line in lf:
                    if line.strip():
                        labels_count += 1

        image_files_with_metadata.append({
            "filename": image,
            "upload_time": modification_time,  # timestamp for sorting
            "metadata": metadata,
            "labels_count": labels_count
        })

    sorted_images = sorted(image_files_with_metadata, key=lambda x: x["upload_time"], reverse=True)

    for image in sorted_images:
        image["upload_time"] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(image["upload_time"]))  # Format after sorting

    return sorted_images

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/gallery')
def gallery():
    return render_template('gallery.html')

@app.route('/receive', methods=['POST'])
def receive_image():
    """Handles image upload and metadata extraction."""
    if "image" not in request.files:
        return jsonify({"error": "No image part"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if "." in file.filename and file.filename.rsplit(".", 1)[1].lower() in {"jpg", "jpeg"}:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(file_path)

        metadata = extract_metadata(file_path)

        socketio.emit("new_image", {
            "filename": filename,
            "metadata": metadata
        })

        return jsonify({"message": "Image received", "metadata": metadata}), 200

    return jsonify({"error": "Invalid file type"}), 400


@app.route('/uploaded_images')
def uploaded_images():
    return jsonify(get_sorted_images(UPLOAD_FOLDER))


@app.route('/get-images')
def get_images():
    return jsonify(get_sorted_images(UPLOAD_FOLDER))


@app.route('/delete-image', methods=['POST'])
def delete_image():
    data = request.get_json(silent=True) or {}
    filename = data.get('filename')

    if not filename:
        return jsonify({"status": "error", "message": "filename missing"}), 400

    img_path = os.path.join(UPLOAD_FOLDER, filename)
    base, _ = os.path.splitext(filename)
    labels_path = os.path.join(LABELS_FOLDER, base + ".txt")

    removed = {"image": False, "labels": False}

    try:
        if os.path.exists(img_path):
            os.remove(img_path)
            removed["image"] = True

        if os.path.exists(labels_path):
            os.remove(labels_path)
            removed["labels"] = True

        status = "success"
        if not any(removed.values()):
            status = "not_found"
        elif not all(removed.values()):
            status = "partial"

        return jsonify({
            "status": status,
            "removed": removed
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download-dataset-range')
def download_dataset_range():
    date_from = request.args.get('from')
    date_to = request.args.get('to')

    if not date_from or not date_to:
        return "Missing date range", 400

    dt_from = datetime.strptime(date_from, "%Y-%m-%d")
    dt_to   = datetime.strptime(date_to, "%Y-%m-%d")

    images = get_sorted_images(UPLOAD_FOLDER)

    selected = []
    for img in images:
        ts = datetime.strptime(img["upload_time"], "%Y-%m-%d %H:%M:%S")
        if dt_from <= ts.date() <= dt_to.date():
            selected.append(img["filename"])

    # Create ZIP in memory
    mem = io.BytesIO()
    with zipfile.ZipFile(mem, 'w', zipfile.ZIP_DEFLATED) as z:
        for filename in selected:
            img_path = os.path.join(UPLOAD_FOLDER, filename)
            if os.path.exists(img_path):
                z.write(img_path, f"uploads/{filename}")

            txt_path = os.path.join("static/labels", filename.replace(".jpg", ".txt"))
            if os.path.exists(txt_path):
                z.write(txt_path, f"labels/{os.path.basename(txt_path)}")

    mem.seek(0)
    return send_file(
        mem,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"dataset_{date_from}_to_{date_to}.zip"
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
