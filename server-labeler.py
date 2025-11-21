# server-labeler.py
import os
from flask import Flask, render_template

app = Flask(__name__)

# Base paths (shared with server-picture)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
LABEL_FOLDER = os.path.join(BASE_DIR, "static", "labels")

# Make sure folders exist (good for future server-side save of .txt)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(LABEL_FOLDER, exist_ok=True)


@app.route("/label")
def label():
    """
    YOLO labeler UI.

    Called as:
        http://192.168.1.67:5001/label?image=img_20250523-160427.jpg

    The frontend (labeler.js) will read ?image=... and load:
      - /static/uploads/<image>         for the picture
      - /static/labels/<stem>.txt       for YOLO annotations (if present)
    """
    return render_template("labeler.html")


if __name__ == "__main__":
    # Run on 5001, separate from server-picture (5000)
    app.run(host="0.0.0.0", port=5001, debug=True)
