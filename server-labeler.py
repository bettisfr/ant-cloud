from flask import Flask, request, render_template, jsonify
import os
import json

app = Flask(__name__)

# Paths
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")
LABELS_DIR = UPLOAD_DIR              # same folder for images and labels
STATUS_PATH = os.path.join(LABELS_DIR, "status.json")

os.makedirs(LABELS_DIR, exist_ok=True)


def load_status():
    """Load global status.json, return {} if missing or invalid."""
    if not os.path.exists(STATUS_PATH) or os.path.getsize(STATUS_PATH) == 0:
        return {}

    try:
        with open(STATUS_PATH, "r") as f:
            return json.load(f)
    except Exception:
        # Corrupt or invalid JSON -> start fresh
        return {}


def save_status(status_dict):
    """Overwrite status.json with the given dict."""
    with open(STATUS_PATH, "w") as f:
        json.dump(status_dict, f, indent=2)


@app.route("/label")
def label_page():
    image_name = request.args.get("image")
    if not image_name:
        return "Missing 'image' parameter", 400
    return render_template("labeler.html", image_name=image_name)


@app.route("/save_labels", methods=["POST"])
def save_labels():
    data = request.get_json(silent=True) or {}
    image_name = data.get("image")
    labels = data.get("labels", [])

    if not image_name:
        return jsonify({"status": "error", "message": "Missing 'image' field"}), 400

    # Path to YOLO txt
    base, _ = os.path.splitext(image_name)
    label_path = os.path.join(LABELS_DIR, base + ".txt")

    # --- 1) Build YOLO GT lines only for NON-FP labels ---
    yolo_lines = []
    status_entry = []

    for l in labels:
        try:
            cls = int(l["cls"])
            xc = float(l["x_center"])
            yc = float(l["y_center"])
            w = float(l["width"])
            h = float(l["height"])
        except (KeyError, ValueError, TypeError):
            # skip malformed label
            continue

        # Accept both is_fp and isFp from the client
        is_fp = bool(l.get("is_fp") or l.get("isFp"))

        # Store full info (for status.json)
        status_entry.append({
            "cls": cls,
            "x_center": xc,
            "y_center": yc,
            "width": w,
            "height": h,
            "is_tp": not is_fp
        })

        # Only non-FP boxes go into YOLO txt
        if not is_fp:
            yolo_lines.append(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

    # Write YOLO txt (TP-only); empty file if no lines
    try:
        with open(label_path, "w") as f:
            if yolo_lines:
                f.write("\n".join(yolo_lines) + "\n")
            else:
                # explicitly truncate to empty file
                f.write("")

    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to write label txt: {e}"}), 500

    # --- 2) Update global status.json ---
    try:
        status = load_status()
        # Overwrite or create entry for this image
        status[image_name] = status_entry
        save_status(status)
    except Exception as e:
        return jsonify({"status": "error", "message": f"Failed to update status.json: {e}"}), 500

    kept = len([s for s in status_entry if not s["is_fp"]])
    total = len(status_entry)

    return jsonify({
        "status": "success",
        "message": f"Saved {kept} GT labels (out of {total} total boxes) for {image_name}."
    })


if __name__ == "__main__":
    # Run on 5001, separate from the main gallery server (5000)
    app.run(host="0.0.0.0", port=5001, debug=True)
