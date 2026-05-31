import sqlite3 as sq
from enum import Enum, auto

class DataConflictHandler(Enum):
        IGNORE = "IGNORE"
        REPLACE = "REPLACE"

# Simple SQLite Database
class Database():
    def __init__(self, filepath: str, name: str, categories: list, data_conflict_handler: DataConflictHandler, primary_keys: list):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.primary_keys = primary_keys
        self.insert_command = Database.get_insert_command(name, categories, data_conflict_handler)
        self.query_command = Database.get_query_command(name)
        self.initialize_components()
        
    def initialize_components(self):
        self.connection = sq.connect(self.filepath)
        self.cursor = self.connection.cursor()

    @staticmethod
    def get_insert_command(name: str, categories: list, data_conflict_handler: DataConflictHandler) -> str:
        insert_command = f"""INSERT OR {data_conflict_handler.value} INTO {name} VALUES ("""
        for category in categories:
            insert_command += f""":{category[0]},"""
        insert_command = insert_command.rstrip(',') + ")"
        return insert_command
    
    @staticmethod
    def get_query_command(name: str) -> str:
        query_command = f"""SELECT * FROM {name} WHERE """
        return query_command

    @staticmethod
    def create_database(filepath: str, name: str, categories: list, primary_keys: list):
        connection = sq.connect(filepath)
        cursor = connection.cursor()
        cursor.execute(Database.get_create_command(name, categories, primary_keys))
        connection.commit()
        connection.close()

    @staticmethod
    def get_create_command(name: str, categories: list, primary_keys: list) -> str:
        command = f"CREATE TABLE IF NOT EXISTS {name} ("
        for category in categories:
            command += f"{category[0]} {category[1]},"
        
        primary_key_categories = ""
        for category in primary_keys:
            primary_key_categories += category + ","
        
        primary_key_categories = primary_key_categories.rstrip(',')
        command += f"PRIMARY KEY ({primary_key_categories}))"
        
        return command
    
    def create_database_self(self):
        self.create_database(self.filepath, self.name, self.categories, self.primary_keys)
        self.initialize_components()

    def add_value(self, value: dict):
        self.cursor.execute(self.insert_command, value)
        self.connection.commit()

    def add_many_values(self, values: list):
        self.cursor.executemany(self.insert_command, values)
        self.connection.commit()

    def query_SQL(self, command: str):
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def query_condition_SQL(self, condition: str, params: dict):
        self.cursor.execute(self.query_command + condition, params)
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

# Helper For Lazy Loading Databases
class DatabaseLoader():
    def __init__(self, filepath: str, name: str, raw_categories: list, data_conflict_handler: DataConflictHandler, primary_keys: list):
        self.filepath = filepath
        self.name = name
        self.data_conflict_handler = data_conflict_handler
        self.primary_keys = primary_keys
        self.category_with_types = list(zip(raw_categories[0::2], raw_categories[1::2]))
        self.category_names = raw_categories[0::2]

    def create_database(self):
        return Database(self.filepath, self.name, self.category_with_types, self.data_conflict_handler, self.primary_keys)
    
    def get_category_names(self):
        return self.category_names
    
    def get_category_with_types(self):
        return self.category_with_types

if __name__ == "__main__":
    print(Database.get_insert_command(
        "test", 
        [("TEST1", "text"),
        ("Test2", "integer")],
        DataConflictHandler.REPLACE))
    print(Database.get_create_command(
        "test", 
        [("TEST1", "text"),
        ("TEST2", "integer")],
        ["TEST1", "TEST2"]))