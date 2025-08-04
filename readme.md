# 🐜 AntPi: Raspberry Pi Camera with YOLO Detection and Web Gallery

This repository contains a complete client-server pipeline for remote wildlife/insect/environmental monitoring using Raspberry Pi cameras equipped with object detection, metadata enrichment, and gallery visualization.

---

## 🗂️ Project Structure

- **`server.py`**  
  Launches the server:
  - Receives images uploaded by remote clients (Raspberry Pi).
  - Hosts a web-based gallery to browse images and metadata.

- **`client.py`**  
  Runs on the Raspberry Pi:
  - Captures images.
  - Collects GPS coordinates and weather data.
  - Embeds metadata in the images before uploading them to the server.

- **`autorun.py`**  
  Autostarts the client on Raspberry Pi boot:
  - Attempts to ping a pre-defined server.
  - If reachable, activates the virtual environment and runs the client script.

- **`rpi.py`**  
  Utility to **test YOLO model performance** directly on the Raspberry Pi:
  - Converts models to various formats (e.g., OpenVINO, TFLite).
  - Profiles RAM, CPU usage, and inference time.

- **`benchmark.py`**  
  Runs multiple tests in sequence (on a PC) using `rpi.py` to:
  - Evaluate different YOLO model variants and settings.
  - Compare performance across precision and formats.

---

## 🚀 Getting Started

### 🖥 Server Setup

```bash
pip install -r requirements.txt
python server.py
```

### 🍓 Raspberry Pi Client Setup

1. Clone the repo and install dependencies (use a virtual environment).
2. Place the script in `autorun.py` to ensure auto-execution on boot.
3. Make sure `client.py` has the correct upload target URL and metadata sources.

```bash
source antenv/bin/activate
python client.py
```

---

## 🧪 Model Testing & Benchmarking

Use `rpi.py` to:
- Export YOLO models to optimized formats.
- Measure performance with realistic input data.

Example usage:
```python
run_test("v11n", "FP16", "openvino")
```

Use `benchmark.py` to:
- Run batch experiments from a desktop host.
- Analyze performance trends across models and formats.

---

## 📸 Features

✅ Image upload from multiple Pi devices  
✅ Embedded GPS & weather metadata  
✅ YOLO object detection on-device  
✅ Performance profiling (RAM, CPU, latency)  
✅ Web gallery interface

---

## 📁 Folder Structure (Example)

```
├── server.py
├── client.py
├── autorun.py
├── rpi.py
├── benchmark.py
├── models/
│   └── [YOLO models and weights]
├── src/
│   ├── learning/
│   │   └── test/images/   # Test images for benchmarking
│   └── data.yaml          # Dataset configuration
```

---

## 📌 Notes

- Tested with YOLOv8, v9, v10, and v11 variants.
- Some model-format-precision combinations may not be supported (e.g., INT8 + TFLite).
- Adapt paths inside scripts if using a different folder layout.

---

## 📜 License

MIT License.  
See `LICENSE` file for more details.
