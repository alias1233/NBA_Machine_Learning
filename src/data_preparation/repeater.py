import threading
import time
from typing import Callable

def repeater(
    function: Callable[[int], bool],
    starting_index: int, 
    wait_interval: float
    ) -> int:
    """
    Repeatedly calls a function with a delay and index.
    """
        
    running_event = threading.Event()

    def listen_for_input():
        input("Press enter to quit.")
        running_event.set()

    thread = threading.Thread(target=listen_for_input, daemon=True)
    thread.start()

    i = int(starting_index)
    while not running_event.is_set():
        print(f"Loop Index: {i}")
        if not function(i):
            print("Loop has finished.")
            break

        i += 1
        time.sleep(wait_interval)

    return i