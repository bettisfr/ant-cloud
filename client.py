from gpiozero import Button, PWMLED, LED
from signal import pause
from picamera2 import Picamera2
from time import sleep
import tensorflow as tf
import numpy as np
from PIL import Image
import requests

# Camera setup
picam2 = Picamera2()
config = picam2.create_still_configuration()
picam2.configure(config)
print("Initializing camera...")
picam2.start()
print("Camera initialized and ready.")

# GPIO setup
button_a = Button(2)
button_b = Button(3)
led_green = PWMLED(17)
led_red = PWMLED(27)

count_a = 0
count_b = 0

# # Load the TFLite model
# model_path = "model.tflite"
# interpreter = tf.lite.Interpreter(model_path=model_path)
# interpreter.allocate_tensors()
#
# # Get input details
# input_details = interpreter.get_input_details()
# input_shape = input_details[0]['shape']  # Typically [1, height, width, channels]
# input_dtype = input_details[0]['dtype']  # Data type of the input tensor
# input_size = (input_shape[1], input_shape[2])  # (height, width)


def preprocess_image(image_path, input_size, input_dtype):
    image = np.array(Image.open(image_path).convert("RGB"))
    image = np.resize(image, (input_size[0], input_size[1], 3))
    if input_dtype == np.uint8:
        image = image.astype(np.uint8)
    else:
        image = image.astype(np.float32) / 255.0
    return np.expand_dims(image, axis=0)


# def predict(interpreter, input_data):
#     interpreter.set_tensor(input_details[0]['index'], input_data)
#     interpreter.invoke()
#     output_data = interpreter.get_tensor(interpreter.get_output_details()[0]['index'])
#     return output_data


def activate_a():
    global count_a
    led_green.value = 1
    count_a += 1

    # Capture the image
    file_path = f"img/photo_{count_a}.jpg"
    print("Capturing photo...")
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")

    print("Camera: ending")
    led_green.value = 0


# def activate_b():
#     global count_b, count_a
#     led_red.value = 1
#     count_b += 1
#
#     # Run the ML model on the last captured image
#     if count_a > 0:  # Ensure there's at least one image captured
#         image_path = f"img/photo_{count_a}.jpg"
#         print(f"Running ML model on {image_path}...")
#         input_data = preprocess_image(image_path, input_size, input_dtype)
#         predictions = predict(interpreter, input_data)
#         print("Predictions:", predictions)
#     else:
#         print("No image available to process.")
#
#     led_red.value = 0

def activate_b():
    global count_b, count_a
    led_red.value = 1
    count_b += 1

    # Run the ML model on the last captured image
    if count_a > 0:  # Ensure there's at least one image captured
        image_path = f"img/photo_{count_a}.jpg"
        SERVER_URL = "http://192.168.1.147:5000/receive"

        with open(image_path, 'rb') as img_file:
            files = {'image': img_file}
            response = requests.post(SERVER_URL, files=files)

        print(f"Server response: {response.text}")
    else:
        print("No image available to process.")

    led_red.value = 0

button_a.when_pressed = activate_a
button_b.when_pressed = activate_b

pause()

