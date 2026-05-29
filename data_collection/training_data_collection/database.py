import sqlite3 as sq
from abc import ABC, abstractmethod

# Simple SQLite Database
class Database():
    def __init__(self, filepath: str, name: str, categories: list):
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
    
    def close(self):
        self.connection.commit()
        self.connection.close()

# Base Collector With User Input
class DataCollector(ABC):
    def __init__(self, filepath: str, name: str, categories: list):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.database = Database(filepath, name, categories)

    def begin_fetch_data(self):
        create_database = input("Create database? (y/n): ").capitalize()
        if create_database == 'Y':
            Database.create_database(self.filepath, self.name, self.categories)
        
        self.fetch_data()

    @abstractmethod
    def fetch_data(self):
        pass

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