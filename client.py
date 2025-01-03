from gpiozero import Button, PWMLED, LED
from signal import pause
from picamera2 import Picamera2
from time import sleep

# Camera stuff
picam2 = Picamera2()
config = picam2.create_still_configuration()
picam2.configure(config)
print("Initializing camera...")
picam2.start()
print("Camera initialized and ready.")

# GPIOs stuff
button_a = Button(2)
button_b = Button(3)
led_green = PWMLED(17)
led_red = PWMLED(27)

count_a = 0
count_b = 0


def activate_a():
    global count_a
    # print("Camera: starting")
    led_green.value = 1
    count_a += 1

    # Start the camera
    sleep(2)
    file_path = f"img/photo_{count_a}.jpg"
    picam2.capture_file(file_path)
    print(f"Photo saved as {file_path}")

    print("Camera: ending")
    led_green.value = 0


# def deactivate_a():
#    #print("Deactivate A")
#    led_green.value = 0

def activate_b():
    global count_b
    # print("Activate B")
    led_red.value = 1
    count_b += 1


# def deactivate_b():
#    #print("Deactivate B")
#    led_red.value = 0

button_a.when_pressed = activate_a
# button_a.when_released = deactivate_a
button_b.when_pressed = activate_b
# button_b.when_released = deactivate_b


pause()

