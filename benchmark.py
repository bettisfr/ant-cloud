import os
import signal
import subprocess
from time import time, sleep
import numpy as np
import re

# Raspberry Pi SSH details
HOST = "192.168.1.197"
USER = "fra"
PRIVATE_KEY_PATH = "~/.ssh/id_rsa"
SCRIPT_PATH = "/home/fra/tests/strees.py"
VENV_PATH = "/home/fra/antenv/bin/activate"
FNIRSI_BIN_PATH = "/home/fra/fnirsi/fnirsi_logger.py"
LOG_FILE_PATH = "/home/fra/fnirsi/log.txt"

avg_RAM = []
max_RAM = []
avg_CPU = []
max_CPU = []
avg_W = []
max_W = []
avg_V = []
max_V = []
avg_A = []
max_A = []

# Function to execute the script remotely with an argument
def run_remote_script(argument):
    # Command to activate the virtual environment and run stress.py remotely
    cmd = f"source {VENV_PATH} && python3 {SCRIPT_PATH} {argument}"

    # SSH command with the private key to execute the command on the remote Raspberry Pi
    ssh_command = f"ssh -i {PRIVATE_KEY_PATH} {USER}@{HOST} '{cmd}'"

    # Record the start timestamp
    start_time = time()

    # Run the command using subprocess
    process = subprocess.Popen(ssh_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = process.communicate()

    # Print the output
    # print("Output:\n", stdout.decode())
    if stderr:
        print("Error:\n", stderr.decode())

    # Record the end timestamp
    end_time = time()

    pattern = r"max_RAM=(\d+\.\d+)\navg_RAM=(\d+\.\d+)"

    # Find matches using the pattern
    matches = re.search(pattern, stdout.decode())

    # If matches are found, extract the values
    if matches:
        max_ram = float(matches.group(1))
        avg_ram = float(matches.group(2))

        max_RAM.append(max_ram)
        avg_RAM.append(avg_ram)

        max_CPU.append(0)
        avg_CPU.append(0)
    else:
        print("No matches found")

    return start_time, end_time


# Function to process the output of the logger
def process_logger_output(start_time, end_time):
    voltage_vals = []
    current_vals = []
    power_vals = []

    # Open the log file
    with open(LOG_FILE_PATH, 'r') as log_file:
        for line in log_file:
            # Skip the header
            if line.startswith("timestamp"):
                continue

            # Extract the columns (assuming they are space-separated)
            columns = line.split()

            if len(columns) >= 9:
                timestamp = float(columns[0])  # timestamp
                voltage = float(columns[2])  # voltage_V
                current = float(columns[3])  # current_A
                # energy = float(columns[7])  # energy_Ws

                # Filter data based on timestamps
                if start_time <= timestamp <= end_time:
                    # Calculate instantaneous power (P = V * I)
                    power = voltage * current
                    power_vals.append(power)

                    # Add voltage and current for reporting
                    voltage_vals.append(voltage)
                    current_vals.append(current)

    # Calculate max and average power
    max_power = max(power_vals) if power_vals else 0.
    avg_power = np.mean(power_vals) if power_vals else 0.

    # Calculate max and average voltage and current for reporting
    max_voltage = max(voltage_vals) if voltage_vals else 0.
    avg_voltage = np.mean(voltage_vals) if voltage_vals else 0.

    max_current = max(current_vals) if current_vals else 0.
    avg_current = np.mean(current_vals) if current_vals else 0.

    max_W.append(max_power)
    avg_W.append(avg_power)

    max_V.append(max_voltage)
    avg_V.append(avg_voltage)

    max_A.append(max_current)
    avg_A.append(avg_current)

    # # Print the results
    # print(f"Max Power: {max_power} W, Avg Power: {avg_power} W")
    # print(f"Max Voltage: {max_voltage} V, Avg Voltage: {avg_voltage} V")
    # print(f"Max Current: {max_current} A, Avg Current: {avg_current} A")


# Function to start the logger in the background (overwrite log.txt)
def start_logger():
    print("Starting logger")
    # subprocess.Popen(f"python3 {FNIRSI_BIN_PATH} > {LOG_FILE_PATH} &", shell=True)


# Function to kill the logger by simulating CTRL+C (SIGINT)
def kill_logger():
    print(f"Killing logger")


# Start the logger
# start_logger()

starts = []
ends = []

# Run first and get RAM and CPU
for i in range(1, 4):
    print(f"Running with argument {i}...")
    start_time, end_time = run_remote_script(i)

    starts.append(start_time)
    ends.append(end_time)

# Iterate to read the log file for V, W, A
for i in range(0, len(starts)):
    start_time = starts[i]
    end_time = ends[i]
    process_logger_output(start_time, end_time)

# Iterate to print everything
for i in range(0, len(starts)):
    print(f"\nSummary with argument {i}...")
    print(f"Max RAM: {max_RAM[i]:.2f} MB, Avg RAM: {avg_RAM[i]:.2f} MB")
    print(f"Max CPU: {max_CPU[i]:.2f} %, Avg CPU: {avg_CPU[i]:.2f} %")
    print(f"Max Power: {max_W[i]:.2f} W, Avg Power: {avg_W[i]:.2f} W")
    print(f"Max Voltage: {max_V[i]:.2f} V, Avg Voltage: {avg_V[i]:.2f} V")
    print(f"Max Current: {max_A[i]:.2f} A, Avg Current: {avg_A[i]:.2f} A")


# Kill the logger after all remote executions are done
# kill_logger()
