import psycopg2
# from sqlalchemy import create_engine
# import pandas as pd
from psycopg2 import OperationalError
from colorama import Fore, Back, Style
from pydantic import BaseModel, Field

# --------------------------------------------------------------
# connect to db
# --------------------------------------------------------------
def create_connection():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="postgres",
            host="localhost",      # Docker PostgreSQL runs on localhost
            port="5432",
            database="postgres"
        )
        print(Fore.GREEN + "Connected successfully!")
        return connection
    except OperationalError as e:
        print(Fore.RED + f"Error connecting: {e}")
    
# --------------------------------------------------------------
# models for request and response
# --------------------------------------------------------------
# Pydantic models for request and response
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's input message to the chat")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Response to the user, either query result or text")

# --------------------------------------------------------------
# get all table names
# --------------------------------------------------------------
def get_table_names():
    conn = create_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
    tables = cursor.fetchall()
    cursor.close()
    conn.close()
    return tables

# --------------------------------------------------------------
# get all column names with data types
# --------------------------------------------------------------
def get_column_names(table_name):
    conn = create_connection()
    if conn is None:
        return []
    cursor = conn.cursor()
    cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' AND table_schema = 'public';")
    columns = cursor.fetchall()
    cursor.close()
    conn.close()
    return columns

# --------------------------------------------------------------
# print column and table names
# --------------------------------------------------------------
def print_table_columns():
    tables = get_table_names()
    if not tables:
        print(Fore.RED + "No tables found or connection failed.")
        return
    for table in tables:
        table_name = table[0]  # Unpack the tuple
        print(Fore.YELLOW + f"Table: {table_name}")
        columns = get_column_names(table_name)
        if columns:
            # Format columns with their data types
            column_list = [f"{col[0]} ({col[1]})" for col in columns]
            print(Fore.BLUE + "Columns: " + Fore.MAGENTA + ", ".join(column_list))
        else:
            print(Fore.YELLOW + "No columns found for this table.")

# --------------------------------------------------------------
# Test the connection and print schema
# --------------------------------------------------------------
conn = create_connection()

if conn:
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL Version: {version}")
    cursor.close()
    conn.close()

# Print the schema
print_table_columns()