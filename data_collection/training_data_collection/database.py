import sqlite3 as sq
from abc import ABC, abstractmethod
import threading, time

# Simple SQLite Database
class Database():
    def __init__(self, filepath: str, name: str, categories: list):
        self.name = name
        self.connection = sq.connect(filepath)
        self.cursor = self.connection.cursor()
        self.insert_command = Database.get_insert_command(name, categories)

    @staticmethod
    def get_insert_command(name: str, categories: list) -> str:
        insert_command = f"""INSERT INTO {name} VALUES ("""
        for index, category in enumerate(categories):
            insert_command += f""":{category[0]}"""
            if index != len(categories) - 1:
                insert_command += ","
        insert_command += ")"
        return insert_command

    @staticmethod
    def create_database(filepath: str, name: str, categories: list):
        connection = sq.connect(filepath)
        cursor = connection.cursor()
        cursor.execute(Database.get_create_command(name, categories))
        connection.commit()
        connection.close()

    @staticmethod
    def get_create_command(name: str, categories: list) -> str:
        command = f"""CREATE TABLE IF NOT EXISTS {name} ("""
        for index, category in enumerate(categories):
            command += f"""{category[0]} {category[1]}"""
            if index != len(categories) - 1:
                command += ","
        command += ")"
        return command

    def add_value(self, value: dict):
        self.cursor.execute(self.insert_command, value)
        self.connection.commit()

    def query_SQL(self, command: str):
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def print_all(self, rows: int = 0):
        self.cursor.execute(f"""SELECT * FROM {self.name}""")

        data = None
        if rows == 0:
            data = self.cursor.fetchall()
        else:
            data = self.cursor.fetchmany(rows)
        
        for row in data:
            print(row)
    
    def close(self):
        self.connection.commit()
        self.connection.close()

# Base Data Collector With User Input
class DataCollector(ABC):
    def __init__(self, filepath: str, name: str, categories: list):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.database = None

    def create_database(self):
        create_database = input("Create database? (y/n): ").capitalize()
        if create_database == 'Y':
            Database.create_database(self.filepath, self.name, self.categories)

    def initialize_database_instance(self):
        if self.database is None:
            self.database = Database(self.filepath, self.name, self.categories)

    def fetch_data(self, wait_interval: float = 1, start_index: int = 0, print_database: bool = False, rows_to_print: int = 0, **kwargs):
        self.initialize_database_instance()

        scheme = input("User controlled or automatic? (u/a): ").capitalize()
        if scheme == 'A':
            self.begin_fetch_data_automatic(wait_interval, start_index, **kwargs)
        else:
            self.fetch_data_user(**kwargs)

        if self.database is not None:
            if print_database:
                self.database.print_all(rows_to_print)
                
            self.database.close()

    @abstractmethod
    def fetch_data_user(self, **kwargs):
        pass

    def begin_fetch_data_automatic(self, wait_interval: float, start_index: int, **kwargs):
        running_event = threading.Event()

        def listen_for_input():
            input("Press enter to quit.")
            running_event.set()
        
        thread = threading.Thread(target=listen_for_input, daemon=True)
        thread.start()

        i = start_index
        while not running_event.is_set():
            self.fetch_data_automatic(i, **kwargs)
            print(f"Loop Index: {i}")
            i += 1
            time.sleep(wait_interval)

    @abstractmethod
    def fetch_data_automatic(self, index: int, **kwargs):
        pass

    def get_database(self):
        return self.database

if __name__ == "__main__":
    print(
        Database.get_insert_command("test", [
        ("TEST1", "text"),
        ("Test2", "integer")
    ]))
    print(
        Database.get_create_command("test", [
        ("TEST1", "text"),
        ("TEST2", "integer")
    ]))