import json
import sys
import gc
import copy
import psutil
import threading
from time import sleep
from memory_profiler import memory_usage

def f(n, a1, b1):
    a = [0] * (25000 * n)
    sleep(0.1)
    b = copy.deepcopy(a) * 100
    sleep(0.1)
    c = copy.deepcopy(b) * 100
    return a

def monitor_cpu_usage(cpu_usage_list, stop_event):
    """ Continuously monitors CPU usage and stores values in cpu_usage_list """
    while not stop_event.is_set():
        cpu_usage_list.append(psutil.cpu_percent(interval=0.1))

def monitor_function(n, a1, b1):
    """ Measures both memory and CPU usage while executing f(n, a1, b1) """
    cpu_usage = []
    stop_event = threading.Event()

    # Start CPU monitoring thread
    cpu_thread = threading.Thread(target=monitor_cpu_usage, args=(cpu_usage, stop_event))
    cpu_thread.start()

    # Force garbage collection before measurement
    gc.collect()

    # Measure memory usage while running the function
    mem_usage = memory_usage((f, (n, a1, b1)), interval=0.1)

    # Stop CPU monitoring thread
    stop_event.set()
    cpu_thread.join()

    # Calculate statistics
    avg_mem_usage = sum(mem_usage) / len(mem_usage)
    max_mem_usage = max(mem_usage)
    avg_cpu_usage = sum(cpu_usage) / len(cpu_usage) if cpu_usage else 0
    max_cpu_usage = max(cpu_usage) if cpu_usage else 0

    # After computing memory and CPU usage
    stats = {
        "max_RAM_MB": round(max_mem_usage, 2),
        "avg_RAM_MB": round(avg_mem_usage, 2),
        "max_CPU_percent": round(max_cpu_usage, 2),
        "avg_CPU_percent": round(avg_cpu_usage, 2),
    }

    # Print JSON output
    print(json.dumps(stats, indent=4))

if __name__ == '__main__':
    a = 5
    b = 10

    for i in range(1, len(sys.argv)):
        n = int(sys.argv[i])
        monitor_function(n, a, b)
