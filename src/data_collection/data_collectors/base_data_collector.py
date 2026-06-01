from abc import ABC, abstractmethod
import threading
import time

from .components.database import Database

# Base Data Collector
class DataCollector(ABC):
    def __init__(self, database: Database):
        self.database = database

    def begin_fetch_data(self, starting_index: int, wait_interval: float, **kwargs) -> int:
        running_event = threading.Event()

        def listen_for_input():
            input("Press enter to quit.")
            running_event.set()

        thread = threading.Thread(target=listen_for_input, daemon=True)
        thread.start()

        i = int(starting_index)
        while not running_event.is_set():
            print(f"Loop Index: {i}")
            if not self.fetch_data_automatic(i, wait_interval, **kwargs):
                print("Loop has finished.")
                break
            i += 1
            time.sleep(wait_interval)
        
        return i

    @abstractmethod
    def fetch_data_automatic(self, index: int, wait_interval: float, **kwargs) -> bool:
        pass