from flask import Flask, request, render_template, jsonify, send_file
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os
import io
import zipfile
import time
import piexif

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")   # images AND labels_live here
LABELS_FOLDER = UPLOAD_FOLDER                         # alias: labels next to images

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ----------------------------------------------------------------------
# EXIF helpers
# ----------------------------------------------------------------------
def to_gps_decimal(gps_data, ref):
    """Convert GPS EXIF format to decimal coordinates."""
    if not gps_data:
        return None

    degrees, minutes, seconds = gps_data
    decimal = (
        degrees[0] / degrees[1]
        + (minutes[0] / minutes[1]) / 60
        + (seconds[0] / seconds[1]) / 3600
    )
    return -decimal if ref in ["S", "W"] else decimal


def extract_metadata(image_path):
    """Extract metadata including temperature, humidity, and GPS from EXIF data."""
    try:
        exif_dict = piexif.load(image_path)
        gps_data = exif_dict.get("GPS", {})

        gps_latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
        gps_latitude_ref = gps_data.get(
            piexif.GPSIFD.GPSLatitudeRef, b"N"
        ).decode(errors="ignore")

        gps_longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
        gps_longitude_ref = gps_data.get(
            piexif.GPSIFD.GPSLongitudeRef, b"E"
        ).decode(errors="ignore")

        latitude = (
            to_gps_decimal(gps_latitude, gps_latitude_ref) if gps_latitude else None
        )
        longitude = (
            to_gps_decimal(gps_longitude, gps_longitude_ref) if gps_longitude else None
        )

        user_comment = exif_dict.get("0th", {}).get(
            piexif.ImageIFD.ImageDescription, b""
        ).decode("utf-8", errors="ignore").strip()

        metadata = {}
        for line in user_comment.splitlines():
            if "=" in line:
                no_space_line = line.replace(" ", "")
                parts = no_space_line.split("|")
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        metadata[key] = value

        temperature = metadata.get("Temperature", "N/A")
        pressure = metadata.get("Pressure", "N/A")
        humidity = metadata.get("Humidity", "N/A")

        def safe_float(v):
            try:
                fv = float(v)
                return fv if fv != 0 else None
            except Exception:
                return None

        return {
            "temperature": safe_float(temperature),
            "pressure": safe_float(pressure),
            "humidity": safe_float(humidity),
            "latitude": round(latitude, 6) if latitude not in (None, 0) else None,
            "longitude": round(longitude, 6) if longitude not in (None, 0) else None,
            "user_comment": user_comment,
        }

    except Exception as e:
        print(f"Error extracting metadata from {image_path}: {e}")
        return {}


# ----------------------------------------------------------------------
# Image listing (gallery)
# ----------------------------------------------------------------------
def get_sorted_images(image_folder):
    """
    Retrieve images and sort them by modification time, plus count labels.
    Image files: *.jpg, *.jpeg
    Label files: same base name, *.txt in LABELS_FOLDER
    """
    image_files = [
        f
        for f in os.listdir(image_folder)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]

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

        image_files_with_metadata.append(
            {
                "filename": image,
                "upload_time": modification_time,  # timestamp for sorting
                "metadata": metadata,
                "labels_count": labels_count,
            }
        )

    sorted_images = sorted(
        image_files_with_metadata, key=lambda x: x["upload_time"], reverse=True
    )

    # Format upload_time as readable string
    for image in sorted_images:
        image["upload_time"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(image["upload_time"])
        )

    return sorted_images


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/gallery")
def gallery():
    return render_template("gallery.html")


@app.route("/receive", methods=["POST"])
def receive_image():
    """
    Handles image upload and metadata extraction.
    Expects form field "image".
    """
    if "image" not in request.files:
        return jsonify({"error": "No image part"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file"}), 400

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in {"jpg", "jpeg"}:
        return jsonify({"error": "Invalid file type"}), 400

    filename = secure_filename(file.filename)
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    metadata = extract_metadata(file_path)

    socketio.emit(
        "new_image",
        {
            "filename": filename,
            "metadata": metadata,
        },
    )

    return jsonify({"message": "Image received", "metadata": metadata}), 200


@app.route("/uploaded_images")
def uploaded_images():
    # kept for backward compatibility (same as /get-images)
    return jsonify(get_sorted_images(UPLOAD_FOLDER))


@app.route("/get-images")
def get_images():
    return jsonify(get_sorted_images(UPLOAD_FOLDER))


@app.route("/delete-image", methods=["POST"])
def delete_image():
    """
    Delete an image and its corresponding .txt labels (if present).
    """
    data = request.get_json(silent=True) or {}
    filename = data.get("filename")

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

        return jsonify({"status": status, "removed": removed})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/download-dataset")
def download_dataset():
    """
    Create a zip on the fly containing:
      - image files from UPLOAD_FOLDER -> uploads/...
      - txt label files from LABELS_FOLDER -> labels/...
    (uploads and labels live in the same directory on disk,
     but we separate them logically in the zip)
    """
    memory_file = io.BytesIO()

    with zipfile.ZipFile(
        memory_file, mode="w", compression=zipfile.ZIP_DEFLATED
    ) as zf:
        # Add images to /uploads
        for root, dirs, files in os.walk(UPLOAD_FOLDER):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in [".jpg", ".jpeg", ".png"]:
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, UPLOAD_FOLDER)
                arcname = os.path.join("uploads", rel_path)
                zf.write(full_path, arcname)

        # Add labels to /labels (only .txt)
        for root, dirs, files in os.walk(LABELS_FOLDER):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext != ".txt":
                    continue
                full_path = os.path.join(root, fname)
                rel_path = os.path.relpath(full_path, LABELS_FOLDER)
                arcname = os.path.join("labels", rel_path)
                zf.write(full_path, arcname)

    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name="antpi_dataset.zip",
    )


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
