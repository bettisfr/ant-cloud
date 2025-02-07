import os
import sys
import gc
from memory_profiler import memory_usage
from time import sleep
import copy

def f(n, a1, b1):
    print(f"n={n}, a1={a1}, b1={b1}")
    a = [0] * (25000 * n)
    sleep(0.1)
    b = copy.deepcopy(a) * 100
    sleep(0.1)
    c = copy.deepcopy(b) * 100
    return a

if __name__ == '__main__':
    a = 5
    b = 10

    for i in range(1, len(sys.argv)):
        n = int(sys.argv[i])

        # Force garbage collection before measuring
        gc.collect()

        # Wrap f inside a lambda function to pass arguments correctly
        mem_usage = memory_usage((lambda: f(n, a, b)), interval=0.1)

        avg_mem_usage = sum(mem_usage) / len(mem_usage)
        max_mem_usage = max(mem_usage)

        print(f"max_RAM={max_mem_usage:.2f}")
        print(f"avg_RAM={avg_mem_usage:.2f}")

