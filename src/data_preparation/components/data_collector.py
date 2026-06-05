from abc import ABC, abstractmethod
import threading
import time

from .database import Database

class DataCollector(ABC):
    """
    Automatic Data Collector
    """

    def __init__(self, database: Database):
        self.database = database

    def _begin_collect_data(self, starting_index: int, wait_interval: float, **kwargs) -> int:
        running_event = threading.Event()

        def listen_for_input():
            input("Press enter to quit.")
            running_event.set()

        thread = threading.Thread(target=listen_for_input, daemon=True)
        thread.start()

        self.database.initialize_components()
        self.database.create_database_self()

        i = int(starting_index)
        while not running_event.is_set():
            print(f"Loop Index: {i}")
            if not self._collect_data(i, wait_interval, **kwargs):
                print("Loop has finished.")
                break

            i += 1
            time.sleep(wait_interval)
        
        self.database.close()

        return i

    @abstractmethod
    def _collect_data(self, index: int, wait_interval: float, **kwargs) -> bool:
        pass

    @abstractmethod
    def begin_collect_data(self, starting_index: int, wait_interval: float, **kwargs) -> int:
        pass