from gpiozero import Button, PWMLED
from signal import pause
from picamera2 import Picamera2
from time import sleep
import requests
from datetime import datetime

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


# Function to take picture and send it to the server
def take_picture_and_send_to_server():
    led_green_take_picture.value = 1

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Capture the image and save it with the timestamped filename
    file_path = f"img/img_{timestamp}.jpg"
    print("Capturing photo...")
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")

    print("Camera: ending")
    led_green_take_picture.value = 0

    led_red_send_image.value = 1

    SERVER_URL = "http://192.168.1.147:5000/receive"

    # Send the image to the server
    with open(file_path, 'rb') as img_file:
        files = {'image': img_file}
        response = requests.post(SERVER_URL, files=files)

    print(f"Server response: {response.text}")

    led_red_send_image.value = 0


button_take_picture_send_image.when_pressed = take_picture_and_send_to_server

# Keep the program running to listen for button presses
pause()
