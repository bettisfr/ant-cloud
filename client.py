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
from time import sleep
from datetime import datetime
import logging
import smbus2
import bme280

# Configure logging
logging.basicConfig(
    format='%(asctime)s [%(levelname)s] %(message)s',  # Log format
    level=logging.INFO  # Log level (e.g., INFO, DEBUG, ERROR)
)

# Constants
#SERVER_URL = "http://192.168.1.147:5000/receive"
SERVER_URL = "http://141.250.25.160:5000/receive"
IMAGE_DIR = "img"

# GPIO setup
capture_button = Button(12)
led_green = PWMLED(4)
led_red = PWMLED(22)
led_blue = PWMLED(25)

led_green.value = 0
led_red.value = 0
led_blue.value = 0

# Device is busy, right led
led_red.blink(on_time=0.5, off_time=0.5, n=10, background=True)

# Camera setup
picam2 = Picamera2()
picam2.configure(picam2.create_still_configuration())

# Set manual focus mode and close focus
picam2.set_controls({"AfMode": 0})  # Manual focus mode
picam2.set_controls({"LensPosition": 0.0})  # Try values: 0.0 to 2.0

logging.info("Initializing camera...")
picam2.start()
logging.info("Camera started in manual focus mode.")

# GPS
try:
    ser = serial.Serial("/dev/ttyACM0", 9600)
    logging.info("GPS found")
except:
    logging.warning("GPS is not attached")

# Temperature, Pressure, Humidity (not present)
address = 0x76
try:
    bus = smbus2.SMBus(1)
    par = bme280.load_calibration_params(bus, address)
    logging.info("Weather found")
except:
    logging.warning("Weather not found")

# Device is ready
led_green.value = 1
led_red.off()


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
    try:
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
                    logging.warning("Error parsing GPS")
                    return None, None
    except:
        logging.warning("No GPS coordinates")
        return None, None
    

def get_weather():
    try:
        # Read sensor data
        data = bme280.sample(bus, address, par)
        #logging.info(data)

        # Extract temperature, pressure, and humidity
        temperature = round(data.temperature, 2)
        pressure = round(data.pressure, 2)
        humidity = round(data.humidity, 2)
        
        return temperature, pressure, humidity
    except:
        logging.warning("No weather data")
        return None, None, None


def capture_photo() -> str:
    """Captures a photo and returns the file path."""
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = f"{IMAGE_DIR}/img_{timestamp}.jpg"
    logging.info("Capturing photo...")
    picam2.capture_file(file_path)
    logging.info(f"Photo saved as {file_path}")
    return file_path


def add_gps_metadata(image_path, latitude=None, longitude=None, temperature=None, pressure=None, humidity=None):
    # Use default values for all
    if temperature is None:
        temperature = 0.0
    if pressure is None:
        pressure = 0.0
    if humidity is None:
        humidity = 0.0
    if latitude is None or longitude is None:
        latitude = 0.0
        longitude = 0.0

    custom_metadata = []
    if temperature is not None:
        custom_metadata.append(f"Temperature={temperature}")
    if pressure is not None:
        custom_metadata.append(f"Pressure={pressure}")
    if humidity is not None:
        custom_metadata.append(f"Humidity={humidity}")
    user_comment = "|".join(custom_metadata) if custom_metadata else "No custom data"

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
        logging.info("Retrieving data...")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        temperature, pressure, humidity = get_weather()
        latitude, longitude = get_gps_data()

        # Print the results
        logging.info(f"Timestamp: {timestamp}")
        if not (latitude is None or longitude is None):
            logging.info(f"GPS Coordinates: Latitude={latitude:.6f}, Longitude={longitude:.6f}")
        if not temperature is None:
            logging.info(f"Temperature: {temperature:.2f}°C")
        if not pressure is None:
            logging.info(f"Pressure: {pressure:.2f}hPa")
        if not humidity is None:
            logging.info(f"Humidity: {humidity:.2f}%")

        add_gps_metadata(file_path, latitude, longitude, temperature, pressure, humidity)

        files = {'image': img_file}
        
        try:
            response = requests.post(SERVER_URL, files=files)
            return True
        except:
            logging.info("Error, server unreachable!")
            return False



def handle_button_press() -> None:
    led_green.value = 0
    led_blue.value = 1
    
    file_path = capture_photo()
    
    led_green.value = 0
    led_red.value = 1
    
    if send_image_to_server(file_path):
        led_blue.value = 0
        led_red.value = 0
        led_green.value = 1
    else:
        led_green.blink(on_time=0.5, off_time=0.5, n=1000, background=True)
        led_red.blink(on_time=0.5, off_time=0.5, n=1000, background=True)
        led_blue.blink(on_time=0.5, off_time=0.5, n=1000, background=True)


def focus_sweep(start=0.0, end=2.0, step=0.1, delay=0.5):
    """Sweep through manual focus positions and capture images for visual comparison."""
    logging.info("Starting focus sweep...")
    if not os.path.exists(IMAGE_DIR):
        os.makedirs(IMAGE_DIR)

    positions = [round(start + i * step, 2) for i in range(int((end - start) / step) + 1)]

    for pos in positions:
        logging.info(f"Setting lens position to {pos}")
        picam2.set_controls({"AfMode": 0})  # Manual focus mode
        picam2.set_controls({"LensPosition": pos})
        time.sleep(delay)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        file_path = f"{IMAGE_DIR}/focus_{pos:.2f}_{timestamp}.jpg"
        picam2.capture_file(file_path)
        logging.info(f"Captured {file_path}")

    logging.info("Focus sweep completed.")


# Event binding
capture_button.when_pressed = handle_button_press

# Test
focus_sweep()

# Keep the program running to listen for button presses
pause()

