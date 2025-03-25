import psycopg2
# from sqlalchemy import create_engine
# import pandas as pd
from psycopg2 import OperationalError

def create_connection():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="postgres",
            host="localhost",      # Docker PostgreSQL runs on localhost
            port="5432",
            database="postgres"
        )
        print("Connected successfully!")
        return connection
    except OperationalError as e:
        print(f"Error connecting: {e}")

conn = create_connection()

# Optional: Test query
cursor = conn.cursor()
cursor.execute("SELECT version();")
version = cursor.fetchone()
print(f"PostgreSQL Version: {version}")

cursor.close()
conn.close()
