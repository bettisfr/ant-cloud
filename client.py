import serial
import adafruit_dht
import board
import time
from datetime import datetime
from gpiozero import Button, PWMLED
from signal import pause
from picamera2 import Picamera2
import requests

# GPS and DHT setup
ser = serial.Serial("/dev/ttyS0", 9600)  # GPS serial port
dht_device = adafruit_dht.DHT11(board.D18)  # GPIO 18 for DHT sensor

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


# Retrieve GPS data
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
                latitude = parse_coordinates(raw_latitude, latitude_dir)
                longitude = parse_coordinates(raw_longitude, longitude_dir)
                if latitude is not None and longitude is not None:
                    return latitude, longitude
            except (IndexError, ValueError):
                return None, None


# Read temperature and humidity
def get_dht_data():
    try:
        temperature = dht_device.temperature
        humidity = dht_device.humidity
        if temperature is not None and humidity is not None:
            return temperature, humidity
    except RuntimeError as e:
        print(f"Error reading DHT sensor: {e}")
    return None, None


# Capture and send image to the server
def take_picture_and_send_to_server():
    led_green_take_picture.value = 1
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    file_path = f"img/img_{timestamp}.jpg"
    print("Capturing photo...")
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")
    led_green_take_picture.value = 0

    led_red_send_image.value = 1
    SERVER_URL = "http://192.168.1.147:5000/receive"
    with open(file_path, 'rb') as img_file:
        files = {'image': img_file}
        response = requests.post(SERVER_URL, files=files)
    print(f"Server response: {response.text}")
    led_red_send_image.value = 0


# Periodically log GPS, temperature, and humidity data
def log_environment_data():
    try:
        while True:
            latitude, longitude = get_gps_data()
            if latitude is not None and longitude is not None:
                print(f"GPS Coordinates: Latitude={latitude:.6f}, Longitude={longitude:.6f}")
            else:
                print("GPS data not available.")

            temperature, humidity = get_dht_data()
            if temperature is not None and humidity is not None:
                print(f"Temperature: {temperature:.1f}°C, Humidity: {humidity:.1f}%")
            else:
                print("Failed to retrieve DHT sensor data.")

            print("Waiting for next reading...")
            time.sleep(10)  # Adjust delay as needed
    except KeyboardInterrupt:
        print("Stopping environment data logging.")
    finally:
        dht_device.exit()


# Start environment data logging in a separate thread
import threading

threading.Thread(target=log_environment_data, daemon=True).start()

# Set up button to trigger photo capture and image upload
button_take_picture_send_image.when_pressed = take_picture_and_send_to_server

# Keep the program running
pause()
