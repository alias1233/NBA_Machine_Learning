import sqlite3 as sq
from abc import ABC, abstractmethod
import threading, time

# Simple SQLite Database
class Database():
    def __init__(self, filepath: str, name: str, categories: list):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.insert_command = Database.get_insert_command(name, categories)
        self.query_command = Database.get_query_command(name, categories)
        self.initialize_components()
        
    def initialize_components(self):
        self.connection = sq.connect(self.filepath)
        self.cursor = self.connection.cursor()

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
    def get_query_command(name: str, categories: list) -> str:
        query_command = f"""SELECT * FROM {name} WHERE """
        return query_command

    @staticmethod
    def create_database_with_user_prompt(filepath: str, name: str, categories: list) -> bool:
        create_database = input("Create database? (y/n): ").capitalize()
        if create_database == 'Y':
            Database.create_database(filepath, name, categories)
            return True
        return False

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
        primary_key_categories = ""
        for index, category in enumerate(categories):
            command += f"""{category[0]} {category[1]}"""
            command += ","
            primary_key_categories += category[0]
            if index < len(categories) - 1:
                primary_key_categories += ","
        command += f"""PRIMARY KEY ({primary_key_categories}) ON CONFLICT IGNORE)"""
        return command
    
    def create_database_with_user_prompt_self(self):
        if self.create_database_with_user_prompt(self.filepath, self.name, self.categories):
            self.initialize_components()

    # TODO: Add method which uses executemany to insert a list of dictionaries in bulk
    def add_value(self, value: dict):
        self.cursor.execute(self.insert_command, value)
        self.connection.commit()

    def query_SQL(self, command: str):
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def query_condition_SQL(self, condition: str):
        self.cursor.execute(self.query_command + condition)
        return self.cursor.fetchall()
    
    def query_all_SQL(self, limit: int | None = None):
        command = f"""SELECT * FROM {self.name}"""
        if limit is not None:
            command += f""" LIMIT {limit}"""
            
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def print_values(self, amount_to_print: int = 10):
        amount_to_print = min(amount_to_print, 100)
        data = self.query_all_SQL(amount_to_print)
        for row in data:
            print(row)
    
    def close(self):
        self.connection.commit()
        self.connection.close()

# Base Data Collector With User Input
class DataCollector(ABC):
    def __init__(self, database: Database):
        self.database = database

    def fetch_data(self, wait_interval: float = 5, start_index: int = 0, **kwargs):
        scheme = input("User controlled or automatic? (u/a): ").capitalize()
        if scheme == 'A':
            self.begin_fetch_data_automatic(wait_interval, start_index, **kwargs)
        else:
            self.fetch_data_user(**kwargs)

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
            print(f"Loop Index: {i}")
            if not self.fetch_data_automatic(i, **kwargs):
                print("Loop has finished.")
                break
            i += 1
            time.sleep(wait_interval)

    @abstractmethod
    def fetch_data_automatic(self, index: int, **kwargs) -> bool:
        pass

# Helper For Lazy Loading Databases
class DatabaseLoader():
    def __init__(self, filepath: str, name: str, raw_categories: list):
        self.filepath = filepath
        self.name = name
        self.category_with_types = list(zip(raw_categories[0::2], raw_categories[1::2]))
        self.category_names = raw_categories[0::2]

    def create_database(self):
        return Database(self.filepath, self.name, self.category_with_types)
    
    def get_category_names(self):
        return self.category_names
    
    def get_category_with_types(self):
        return self.category_with_types

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