from flask import Flask, request, render_template, jsonify, send_file
from flask_socketio import SocketIO
from werkzeug.utils import secure_filename
import os
import io
import zipfile
import time
import json
import piexif

app = Flask(__name__)
socketio = SocketIO(app, async_mode='eventlet')

# ----------------------------------------------------------------------
# Configuration
# ----------------------------------------------------------------------
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_FOLDER = os.path.join(STATIC_DIR, "uploads")   # images AND labels_live here
LABELS_FOLDER = UPLOAD_FOLDER                         # alias: labels next to images
STATUS_PATH = os.path.join(LABELS_FOLDER, "status.json")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def load_status():
    """Load status.json created by the labeler server (if present)."""
    if not os.path.exists(STATUS_PATH):
        return {}
    try:
        with open(STATUS_PATH, "r") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


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


# def extract_metadata(image_path):
#     """Extract metadata including temperature, humidity, and GPS from EXIF data."""
#     try:
#         exif_dict = piexif.load(image_path)
#         gps_data = exif_dict.get("GPS", {})
#
#         gps_latitude = gps_data.get(piexif.GPSIFD.GPSLatitude)
#         gps_latitude_ref = gps_data.get(
#             piexif.GPSIFD.GPSLatitudeRef, b"N"
#         ).decode(errors="ignore")
#
#         gps_longitude = gps_data.get(piexif.GPSIFD.GPSLongitude)
#         gps_longitude_ref = gps_data.get(
#             piexif.GPSIFD.GPSLongitudeRef, b"E"
#         ).decode(errors="ignore")
#
#         latitude = (
#             to_gps_decimal(gps_latitude, gps_latitude_ref) if gps_latitude else None
#         )
#         longitude = (
#             to_gps_decimal(gps_longitude, gps_longitude_ref) if gps_longitude else None
#         )
#
#         user_comment = exif_dict.get("0th", {}).get(
#             piexif.ImageIFD.ImageDescription, b""
#         ).decode("utf-8", errors="ignore").strip()
#
#         metadata = {}
#         for line in user_comment.splitlines():
#             if "=" in line:
#                 no_space_line = line.replace(" ", "")
#                 parts = no_space_line.split("|")
#                 for part in parts:
#                     if "=" in part:
#                         key, value = part.split("=", 1)
#                         metadata[key] = value
#
#         temperature = metadata.get("Temperature", "N/A")
#         pressure = metadata.get("Pressure", "N/A")
#         humidity = metadata.get("Humidity", "N/A")
#
#         def safe_float(v):
#             try:
#                 fv = float(v)
#                 return fv if fv != 0 else None
#             except Exception:
#                 return None
#
#         return {
#             "temperature": safe_float(temperature),
#             "pressure": safe_float(pressure),
#             "humidity": safe_float(humidity),
#             "latitude": round(latitude, 6) if latitude not in (None, 0) else None,
#             "longitude": round(longitude, 6) if longitude not in (None, 0) else None,
#             "user_comment": user_comment,
#         }
#
#     except Exception as e:
#         print(f"Error extracting metadata from {image_path}: {e}")
#         return {}

def extract_metadata(image_path):
    """
    TEMP: disable EXIF parsing for performance testing.
    """
    return {
        "temperature": None,
        "pressure": None,
        "humidity": None,
        "latitude": None,
        "longitude": None,
        "user_comment": "",
    }


# ----------------------------------------------------------------------
# Image listing (gallery)
# ----------------------------------------------------------------------
def get_sorted_images(image_folder):
    """
    Retrieve images and sort them by the timestamp encoded in the filename
    (e.g., 2023-07-20T20-19-46+0200_...), newest first.
    If parsing fails, fall back to file modification time.
    Image files: *.jpg, *.jpeg
    Label files: same base name, *.txt in LABELS_FOLDER
    """

    def parse_timestamp_from_filename(filename: str, file_path: str) -> float:
        """
        Try to parse the leading timestamp in the filename:
        2023-07-20T20-19-46+0200_b8-27-eb-3b-8d-1c.jpeg

        Prefix:  %Y-%m-%dT%H-%M-%S%z
        If anything goes wrong, fall back to os.path.getmtime(file_path).
        """
        base_name, _ = os.path.splitext(filename)

        try:
            # Take the part before the first underscore
            prefix = base_name.split("_", 1)[0]  # "2023-07-20T20-19-46+0200"
            dt = datetime.datetime.strptime(prefix, "%Y-%m-%dT%H-%M-%S%z")
            return dt.timestamp()
        except Exception:
            # Fallback: filesystem mtime
            return os.path.getmtime(file_path)

    image_files = [
        f
        for f in os.listdir(image_folder)
        if f.lower().endswith((".jpg", ".jpeg"))
    ]

    image_files_with_metadata = []
    for image in image_files:
        file_path = os.path.join(image_folder, image)

        # sort key based on filename timestamp (or mtime as fallback)
        sort_ts = parse_timestamp_from_filename(image, file_path)

        metadata = extract_metadata(file_path)

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
                "upload_ts": sort_ts,   # numeric timestamp used for sorting
                "metadata": metadata,
                "labels_count": labels_count,
            }
        )

    # Sort by our parsed timestamp (newest first)
    sorted_images = sorted(
        image_files_with_metadata, key=lambda x: x["upload_ts"], reverse=True
    )

    # Add a human-readable upload_time string
    for image in sorted_images:
        image["upload_time"] = time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(image["upload_ts"])
        )
        # If you don't want to expose the raw ts to the frontend, you can:
        # del image["upload_ts"]

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
    """
    Return the list of images with optional filtering.

    Query parameters:
      - filter: substring (case-insensitive) to match in filename
      - only_labeled: if true/1/yes → keep only images that have an entry in status.json
    """
    # read query params
    filter_str = request.args.get("filter", "").strip().lower()
    only_labeled_raw = request.args.get("only_labeled", "false").strip().lower()
    only_labeled = only_labeled_raw in ("1", "true", "yes", "on")

    images = get_sorted_images(UPLOAD_FOLDER)
    status = load_status()

    # add is_labeled flag to each image (true if present in status.json)
    for img in images:
        fname = img.get("filename")
        img["is_labeled"] = fname in status

    # apply filename filter (if any)
    if filter_str:
        images = [
            img for img in images
            if filter_str in img["filename"].lower()
        ]

    # apply "only non labeled" filter
    if only_labeled:  # NOW means: only NON-labeled
        images = [img for img in images if not img.get("is_labeled")]

    return jsonify(images)



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
