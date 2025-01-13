from gpiozero import Button, PWMLED
from signal import pause
from picamera2 import Picamera2
from PIL import Image
import piexif
import os
import requests
from datetime import datetime
import serial
import adafruit_dht
import board
import time
from datetime import datetime

# Constants
SERVER_URL = "http://192.168.1.147:5000/receive"
IMAGE_DIR = "img"

# Camera setup
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())
print("Initializing camera...")
picam2.start()
print("Camera initialized and ready.")

# GPIO setup
capture_button = Button(2)
led_green = PWMLED(17)
led_red = PWMLED(27)

# Initialize serial port for GPS
ser = serial.Serial("/dev/ttyS0", 9600)  # Use correct baud rate for your GPS module

# Initialize the DHT sensor
dht_device = adafruit_dht.DHT11(board.D18)  # GPIO 18


# Function to parse GPS coordinates from NMEA sentence
def parse_coordinates(coord, direction):
    """Convert NMEA coordinates to decimal degrees."""
    if not coord or not direction:
        return None

    # Determine how many digits to use for degrees
    if direction in ['N', 'S']:
        degrees_length = 2  # Latitude uses 2 digits for degrees
    elif direction in ['E', 'W']:
        degrees_length = 3  # Longitude uses 3 digits for degrees
    else:
        return None  # Invalid direction

    # Split into degrees and minutes
    degrees = int(coord[:degrees_length])
    minutes = float(coord[degrees_length:])
    decimal = degrees + (minutes / 60)

    # Apply direction (N/S or E/W)
    if direction in ['S', 'W']:
        decimal = -decimal

    return decimal


# Function to get GPS data
def get_gps_data():
    while True:
        received_data = ser.readline().decode('ascii', errors='ignore').strip()
        if received_data.startswith('$GPGGA'):
            try:
                gpgga_data = received_data.split(',')
                raw_latitude = gpgga_data[2]
                latitude_dir = gpgga_data[3]
                raw_longitude = gpgga_data[4]
                longitude_dir = gpgga_data[5]

                # Parse coordinates
                latitude = parse_coordinates(raw_latitude, latitude_dir)
                longitude = parse_coordinates(raw_longitude, longitude_dir)

                if latitude is not None and longitude is not None:
                    return latitude, longitude
                else:
                    return None, None
            except (IndexError, ValueError):
                return None, None


def get_temperature_humidity():
    temperature = dht_device.temperature
    humidity = dht_device.humidity
    return temperature, humidity


def capture_photo() -> str:
    """Captures a photo and returns the file path."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = f"{IMAGE_DIR}/img_{timestamp}.jpg"
    print("Capturing photo...")
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")
    return file_path


def add_gps_metadata(image_path, latitude=None, longitude=None, temperature=None, humidity=None):
    # Use default values for all
    if temperature is None:
        temperature = 0.0
    if humidity is None:
        humidity = 0.0
    if latitude is None or longitude is None:
        latitude = 0.0
        longitude = 0.0

    # Add custom metadata (e.g., temperature, humidity)
    custom_metadata = []
    if temperature is not None:
        custom_metadata.append(f"Temperature={temperature}")
    if humidity is not None:
        custom_metadata.append(f"Humidity={humidity}")
    user_comment = " | ".join(custom_metadata) if custom_metadata else "No custom data"

    # Convert degrees to GPS format (degrees, minutes, seconds)
    def to_gps_format(value):
        degrees = int(value)
        minutes = int((value - degrees) * 60)
        seconds = int((value - degrees - minutes / 60) * 3600 * 100)
        return (degrees, 1), (minutes, 1), (seconds, 100)

    # Prepare GPS metadata
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: b'N' if latitude >= 0 else b'S',
        piexif.GPSIFD.GPSLatitude: to_gps_format(abs(latitude)),
        piexif.GPSIFD.GPSLongitudeRef: b'E' if longitude >= 0 else b'W',
        piexif.GPSIFD.GPSLongitude: to_gps_format(abs(longitude)),
    }

    # Load the image and add metadata
    exif_dict = piexif.load(image_path)
    exif_dict['GPS'] = gps_ifd

    # Add custom data to 'UserComment' field
    exif_dict['0th'][piexif.ImageIFD.ImageDescription] = user_comment.encode('utf-8')

    # Dump the EXIF data
    exif_bytes = piexif.dump(exif_dict)
    image = Image.open(image_path)

    # Save image with updated metadata
    image.save(image_path, exif=exif_bytes, quality=90, optimize=True)


def send_image_to_server(file_path: str) -> None:
    """Sends the captured photo to the server."""
    print("Sending image to server...")
    with open(file_path, 'rb') as img_file:
        print("Retrieving data...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        temperature, humidity = get_temperature_humidity()
        latitude, longitude = get_gps_data()

        # Print the results
        print(f"Timestamp: {timestamp}")
        print(f"GPS Coordinates: Latitude={latitude:.6f}, Longitude={longitude:.6f}")
        print(f"Temperature: {temperature:.1f}°C")
        print(f"Humidity: {humidity:.1f}%")

        add_gps_metadata(img_file, latitude, longitude, temperature, humidity)

        files = {'image': img_file}
        response = requests.post(SERVER_URL, files=files)
        print(f"Server response: {response.text}")


def handle_button_press() -> None:
    """Handles the button press to capture and send a photo."""
    led_green.value = 1  # Turn on the green LED
    file_path = capture_photo()
    led_green.value = 0  # Turn off the green LED
    led_red.value = 1  # Turn on the red LED
    send_image_to_server(file_path)
    led_red.value = 0  # Turn off the red LED


# Event binding
capture_button.when_pressed = handle_button_press

# Keep the program running to listen for button presses
pause()
