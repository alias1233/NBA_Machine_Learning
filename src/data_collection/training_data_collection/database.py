import sqlite3 as sq
from enum import Enum, auto
from dataclasses import dataclass

class DataConflictHandler(Enum):
        IGNORE = "IGNORE"
        REPLACE = "REPLACE"

class DataType(Enum):
    INTEGER = "integer"
    REAL = "real"
    TEXT = "text"
    NULL = "null"
    BLOB = "blob"

@dataclass
class Category():
    category_name: str
    category_type: DataType

class Database():
    """
    Simple SQLite Database.
    """
    def __init__(self, filepath: str, name: str, categories: list[Category], data_conflict_handler: DataConflictHandler, primary_keys: list[Category]):
        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.categories_index_dict = Database.get_categories_index_dict(categories)
        self.category_names = [property.category_name for property in categories]
        self.primary_keys = primary_keys
        self.insert_command = Database.get_insert_command(name, categories, data_conflict_handler)
        self.query_command = Database.get_query_command(name)
        
    def initialize_components(self):
        self.connection = sq.connect(self.filepath)
        self.cursor = self.connection.cursor()

    @staticmethod
    def get_categories_index_dict(categories: list[Category]) -> dict:
        return { category.category_name : index for index, category in enumerate(categories) }

    @staticmethod
    def get_insert_command(name: str, categories: list[Category], data_conflict_handler: DataConflictHandler) -> str:
        insert_command = f"""INSERT OR {data_conflict_handler.value} INTO {name} VALUES ("""
        for category in categories:
            insert_command += f""":{category.category_name},"""
        insert_command = insert_command.rstrip(',') + ")"
        return insert_command
    
    @staticmethod
    def get_query_command(name: str) -> str:
        query_command = f"""SELECT * FROM {name} WHERE """
        return query_command

    @staticmethod
    def create_database(filepath: str, name: str, categories: list[Category], primary_keys: list[Category]):
        connection = sq.connect(filepath)
        cursor = connection.cursor()
        cursor.execute(Database.get_create_command(name, categories, primary_keys))
        connection.commit()
        connection.close()

    @staticmethod
    def get_create_command(name: str, categories: list[Category], primary_keys: list[Category]) -> str:
        command = f"CREATE TABLE IF NOT EXISTS {name} ("
        for category in categories:
            command += f"{category.category_name} {category.category_type.value},"
        
        primary_key_categories = ""
        for category in primary_keys:
            primary_key_categories += category.category_name + ","
        
        primary_key_categories = primary_key_categories.rstrip(',')
        command += f"PRIMARY KEY ({primary_key_categories}))"
        
        return command
    
    def create_database_self(self):
        self.create_database(self.filepath, self.name, self.categories, self.primary_keys)

    def add_value(self, value: dict):
        self.cursor.execute(self.insert_command, value)
        self.connection.commit()

    def add_many_values(self, values: list):
        self.cursor.executemany(self.insert_command, values)
        self.connection.commit()

    def query_SQL(self, command: str) -> list:
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def query_condition_SQL(self, condition: str, params: dict) -> list:
        self.cursor.execute(self.query_command + condition, params)
        return self.cursor.fetchall()
    
    def query_all_SQL(self, limit: int | None = None) -> list:
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

    def get_categories(self) -> list[Category]:
        return self.categories
    
    def get_category_names(self) -> list[str]:
        return self.category_names

    def get_property_from_value(self, value: list, category_name: str):
        return value[self.categories_index_dict[category_name]]
    
# Helper Class For Making Categories
class Categories():
    def __init__(self):
        self.categories: list[Category] = []

    def add_category(self, category_name: str, category_type: DataType) -> Category:
        category = Category(category_name, category_type)
        self.categories.append(category)
        return category
    
    def get_categories(self) -> list[Category]:
        return self.categories

if __name__ == "__main__":
    pass