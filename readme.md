# Ant Detector 🚀

## Overview

Welcome to **Ant Detector**, an innovative solution for capturing and analyzing field images with environmental data (temperature, humidity, GPS) embedded within them. Powered by **Flask**, **Socket.IO**, and modern front-end technologies, Ant Detector allows you to effortlessly view real-time image uploads in a sleek gallery, and dive into the metadata insights that help us understand the environment where these images were taken.

---

## Features 🌟

- **Real-Time Updates**: Using Socket.IO, new images are added to the gallery as soon as they’re uploaded.
- **Dynamic Image Gallery**: Responsive and minimal gallery that displays images in sync with your viewport.
- **Data-Driven Insights**: View metadata like temperature, humidity, and GPS coordinates directly alongside images.
- **Modern UI**: Clean, minimal, and user-friendly interface with a touch of sustainability-themed colors.
- **Modular Design**: Built using Flask and Flask-SocketIO, designed to scale with ease.

---

## 🛠️ Installation & Running the Code

### Prerequisites

Before diving into Ant Detector, make sure you have these tools installed:

- **Python 3** ([Download](https://www.python.org/downloads/))
- **pip** (Python's package manager, usually bundled with Python)

### Steps to Get Started 🚀

#### 1. Clone the Repository

```bash
git clone https://github.com/bettisfr/ant-detector.git
cd ant-detector
```

#### 2. Set Up a Virtual Environment (Recommended)

```bash
python -m venv venv
```

Activate it:

- **Windows**:
  ```bash
  .\venv\Scripts\activate
  ```
- **macOS/Linux**:
  ```bash
  source venv/bin/activate
  ```

#### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Run the Flask Server

```bash
python server.py
```

Visit `http://127.0.0.1:5000/` to launch the app locally!

---

## 🚀 Features in Action

1. **Gallery Page** (`/gallery`): Responsive grid of uploaded images with embedded metadata.
2. **Analytics Page** (`/analytics`): Visualize temperature, humidity, and GPS data. *[Under Development]*

---

## 👨‍💻 How It Works

### Back-End (Python/Flask)
- **Server Setup**: Uses Flask-SocketIO for real-time communication.
- **Image Upload**: Extracts metadata (e.g., GPS, temperature) via `Piexif`.
- **API Endpoints**: `/get-images` serves sorted images and metadata.

### Front-End (JavaScript/HTML)
- **Socket.IO**: Real-time gallery updates.
- **Lazy Loading**: Optimized image loading.
- **Responsive Design**: Works on all screen sizes.
- **Client.py**: *[No Written So Far]*
---

## 🎨 Customization

- **Styling**: Modify `styles.css` for colors/fonts.
- **Logo**: Replace `static/logo.png`.
- **Metadata**: Extend backend logic to support new data types.

---

## 📂 Folder Structure

```
/ant-detector
├── static/
│   ├── uploads/      # Uploaded images
│   ├── styles.css    # CSS
│   └── script.js     # Front-end logic
├── templates/
│   ├── index.html    # Homepage
│   ├── gallery.html  # Gallery
│   └── analytics.html
├── server.py         # Flask app
├── requirements.txt  # Dependencies
└── README.md         # This file
```

---

## 💬 Feedback

[Open an issue](https://github.com/your-username/ant-detector/issues) to share questions or suggestions!

---

🐜 **Let the world see the ants!**