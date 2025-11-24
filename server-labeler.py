from flask import Flask, request, render_template, jsonify
import os

app = Flask(__name__)

# ----------------------------------------------------------------------
# Directories
# ----------------------------------------------------------------------
BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
UPLOAD_DIR = os.path.join(STATIC_DIR, "uploads")   # images live here
LABELS_DIR = UPLOAD_DIR                            # labels: same folder

os.makedirs(UPLOAD_DIR, exist_ok=True)


# ----------------------------------------------------------------------
# Routes
# ----------------------------------------------------------------------
@app.route("/label")
def label_page():
    """
    Open the labeling UI for a server-side image.
    Called as:  /label?image=img_20250523-160427.jpg
    """
    image_name = request.args.get("image")
    if not image_name:
        return "Missing 'image' parameter", 400

    img_path = os.path.join(UPLOAD_DIR, image_name)
    if not os.path.exists(img_path):
        return f"Image '{image_name}' not found on server.", 404

    return render_template("labeler.html", image_name=image_name)


@app.route("/save_labels", methods=["POST"])
def save_labels():
    """
    Save labels in YOLO format next to the image (same base name, .txt).
    Expects JSON:
    {
        "image": "img_20250523-160427.jpg",
        "labels": [
            {"cls": 0, "x_center": 0.5, "y_center": 0.5, "width": 0.2, "height": 0.1},
            ...
        ]
    }
    """
    data = request.get_json(silent=True) or {}
    image_name = data.get("image")
    labels = data.get("labels", [])

    if not image_name:
        return jsonify({"status": "error", "message": "Missing 'image' field"}), 400

    base, _ = os.path.splitext(image_name)
    label_path = os.path.join(LABELS_DIR, base + ".txt")

    try:
        lines = []
        for l in labels:
            cls = int(l["cls"])
            xc = float(l["x_center"])
            yc = float(l["y_center"])
            w = float(l["width"])
            h = float(l["height"])
            lines.append(f"{cls} {xc:.6f} {yc:.6f} {w:.6f} {h:.6f}")

        with open(label_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        return jsonify(
            {
                "status": "success",
                "message": f"Saved {len(labels)} labels to {os.path.basename(label_path)}",
            }
        )
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    # Run on 5001, separate from server-picture (5000)
    app.run(host="0.0.0.0", port=5001, debug=True)
