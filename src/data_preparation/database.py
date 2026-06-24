import sqlite3 as sq
from enum import Enum
from typing import Any
import pandas as pd

from .category import Category

class DataConflictHandler(Enum):
        IGNORE = "IGNORE"
        REPLACE = "REPLACE"

class Database():
    """
    Simple SQLite Database
    """
    
    def __init__(
        self, 
        filepath: str, 
        name: str, 
        categories: list[Category], 
        data_conflict_handler: DataConflictHandler, 
        primary_keys: list[Category]
        ):

        self.filepath = filepath
        self.name = name
        self.categories = categories
        self.categories_index_dict = Database.get_categories_index_dict(categories)
        self.category_names = [property.category_name for property in categories]
        self.primary_keys = primary_keys
        self.insert_command = Database.get_insert_command(name, categories, data_conflict_handler)
        
    def initialize_components(self):
        self.connection = sq.connect(self.filepath)
        self.cursor = self.connection.cursor()

    @staticmethod
    def get_categories_index_dict(categories: list[Category]) -> dict[str, int]:
        return {category.category_name : index for index, category in enumerate(categories)}

    @staticmethod
    def get_insert_command(
        name: str, 
        categories: list[Category], 
        data_conflict_handler: DataConflictHandler
        ) -> str:

        insert_command = f"""INSERT OR {data_conflict_handler.value} INTO {name} VALUES ("""
        for category in categories:
            insert_command += f""":{category.category_name},"""
        insert_command = insert_command.rstrip(',') + ")"
        return insert_command

    @staticmethod
    def create_database(
        filepath: str, 
        name: str, 
        categories: list[Category], 
        primary_keys: list[Category]
        ):

        connection = sq.connect(filepath)
        cursor = connection.cursor()
        cursor.execute(Database.get_create_command(name, categories, primary_keys))
        connection.commit()
        connection.close()

    @staticmethod
    def get_create_command(
        name: str, 
        categories: list[Category], 
        primary_keys: list[Category]
        ) -> str:

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

    @staticmethod
    def category_to_category_name_dict(value: dict[Category, Any]):
        return {category.category_name : v for category, v in value.items()}

    def add_value(self, value: dict[Category, Any]):
        string_dict = self.category_to_category_name_dict(value)
        self.cursor.execute(self.insert_command, string_dict)
        self.connection.commit()

    def add_many_values(self, values: list[dict[Category, Any]]):
        string_dicts = []
        for value in values:
            string_dicts.append(self.category_to_category_name_dict(value))
        self.cursor.executemany(self.insert_command, string_dicts)
        self.connection.commit()

    def query_SQL_command(self, command: str) -> list:
        self.cursor.execute(command)
        return self.cursor.fetchall()
    
    @staticmethod
    def get_query_columns(categories: list[Category] | None = None) -> str:
        query_columns = "*"
        if categories:
            query_columns = ",".join(category.category_name for category in categories)
        return query_columns
    
    def query(
            self, 
            SQL_condition: str | None = None, 
            condition_params: dict[Category, Any] | None = None, 
            categories: list[Category] | None = None, 
            limit: int | None = None
            ) -> list:
        """
        Queries the database with the given parameters and returns the values found as a list.

        Args:
            SQL_condition: A filter in SQL style on the returned values.
            condition_params: A dictionary that maps each category in the SQL_condition to a value.
            categories: The specified returned categories of the fetched values. An input value of None will return all categories.
            limit: The maximum number of returned values. An input value of None corresponds to no limit.
        """
        
        query_columns = self.get_query_columns(categories)
        command = f"""SELECT {query_columns} FROM {self.name}"""
        if SQL_condition:
            command = f"{command} WHERE {SQL_condition}"
        if limit is not None:
            command += f""" LIMIT {limit}"""
        if condition_params:
            string_dict = self.category_to_category_name_dict(condition_params)
            self.cursor.execute(command, string_dict)
        else:
            self.cursor.execute(command)
        return self.cursor.fetchall()
    
    def query_dataframe(
            self, 
            SQL_condition: str | None = None, 
            condition_params: dict[Category, Any] | None = None, 
            categories: list[Category] | None = None, 
            limit: int | None = None
            ) -> pd.DataFrame:
        """
        Identical to [query] except that the values are returned as a labeled pandas.DataFrame.
        """

        data = self.query(SQL_condition, condition_params, categories, limit)
        if not categories:
            categories = self.categories
        return pd.DataFrame(data, columns=[category.category_name for category in categories])
    
    def print_values(self, amount_to_print: int = 10):
        amount_to_print = min(amount_to_print, 100)
        data = self.query(limit=amount_to_print)
        for row in data:
            print(row)
    
    def close(self):
        self.connection.commit()
        self.connection.close()

    def get_categories(self) -> list[Category]:
        return self.categories
    
    def get_category_names(self) -> list[str]:
        return self.category_names

    def get_value_from_category(
            self, 
            value: list, 
            category_name: str
            ):
        
        return value[self.categories_index_dict[category_name]]
    
    def __enter__(self):
        self.initialize_components()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False