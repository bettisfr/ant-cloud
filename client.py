from gpiozero import Button, PWMLED
from picamera2 import Picamera2
from time import sleep
import requests
from datetime import datetime
import piexif
from PIL import Image
import serial
import adafruit_dht
import board

# Initialize serial port for GPS
ser = serial.Serial("/dev/ttyS0", 9600)  # Use correct baud rate for your GPS module

# Initialize the DHT sensor
dht_device = adafruit_dht.DHT11(board.D18)  # GPIO 18

# Camera setup
picam2 = Picamera2()
config = picam2.create_still_configuration()
picam2.configure(config)
print("Initializing camera...")
picam2.start()
print("Camera initialized and ready.")

# GPIO setup
button_take_picture_send_image = Button(2)
led_green_take_picture = PWMLED(17)
led_red_send_image = PWMLED(27)

# Function to parse GPS coordinates from NMEA sentence
def parse_coordinates(coord, direction):
    if not coord or not direction:
        return None
    degrees_length = 2 if direction in ['N', 'S'] else 3
    degrees = int(coord[:degrees_length])
    minutes = float(coord[degrees_length:])
    decimal = degrees + (minutes / 60)
    return -decimal if direction in ['S', 'W'] else decimal

# Function to get GPS data
def get_gps_data():
    while True:
        received_data = ser.readline().decode('ascii', errors='ignore').strip()
        if received_data.startswith('$GPGGA'):
            try:
                gpgga_data = received_data.split(',')
                latitude = parse_coordinates(gpgga_data[2], gpgga_data[3])
                longitude = parse_coordinates(gpgga_data[4], gpgga_data[5])
                return latitude, longitude
            except (IndexError, ValueError):
                return None, None

# Function to capture image and add metadata
def take_picture_with_metadata():
    led_green_take_picture.value = 1

    # Generate a timestamped filename
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = f"img/img_{timestamp}.jpg"

    # Capture the image
    print("Capturing photo...")
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")

    # Get GPS, temperature, and humidity
    latitude, longitude = get_gps_data()
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
    except RuntimeError as e:
        print(f"Error reading DHT sensor: {e}")
        temperature, humidity = None, None

    # Prepare metadata
    exif_data = {
        "0th": {
            piexif.ImageIFD.ImageDescription: f"Captured on {timestamp}",
            piexif.ImageIFD.Artist: "Raspberry Pi",
        },
        "GPS": {
            piexif.GPSIFD.GPSLatitudeRef: 'N' if latitude >= 0 else 'S',
            piexif.GPSIFD.GPSLatitude: piexif.GPSHelper.deg_to_dms_rational(abs(latitude)),
            piexif.GPSIFD.GPSLongitudeRef: 'E' if longitude >= 0 else 'W',
            piexif.GPSIFD.GPSLongitude: piexif.GPSHelper.deg_to_dms_rational(abs(longitude)),
        },
    }

    if temperature is not None and humidity is not None:
        exif_data["0th"][piexif.ImageIFD.UserComment] = f"Temp: {temperature:.1f}C, Humidity: {humidity:.1f}%"

    # Embed metadata into the image
    piexif.insert(piexif.dump(exif_data), file_path)
    print("Metadata added to the image.")

    led_green_take_picture.value = 0
    print("Photo processing complete.")

# Button press handler
button_take_picture_send_image.when_pressed = take_picture_with_metadata

# Keep the program running to listen for button presses
print("Ready to capture photos. Press the button to capture.")
try:
    while True:
        sleep(1)
except KeyboardInterrupt:
    print("Program stopped by user.")
finally:
    dht_device.exit()
