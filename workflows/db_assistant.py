import psycopg2
from psycopg2 import OperationalError
from colorama import Fore, Back, Style
from pydantic import BaseModel, Field
import openai
import json
import os
import sys

# --------------------------------------------------------------
# Connect to DB
# --------------------------------------------------------------
def create_connection():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="postgres",
            host="localhost",
            port="5432",
            database="postgres"
        )
        return connection
    except OperationalError as e:
        print(Fore.RED + f"Error connecting: {e}")
        return None

# --------------------------------------------------------------
# Models for Request and Response
# --------------------------------------------------------------
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's input message to the chat")

class ChatResponse(BaseModel):
    reply: str = Field(..., description="Text response to the user")
    query: str = Field(..., description="SQL query generated by the LLM")

# --------------------------------------------------------------
# Get Table and Column Names
# --------------------------------------------------------------
def get_table_names(conn):
    if conn is None:
        print(Fore.RED + "No connection for table names.")
        return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public' AND table_type='BASE TABLE';")
        tables = cursor.fetchall()
        cursor.close()
        return tables
    except Exception as e:
        print(Fore.RED + f"Error fetching table names: {e}")
        return []

def get_column_names(conn, table_name):
    if conn is None:
        print(Fore.RED + "No connection for column names.")
        return []
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table_name}' AND table_schema = 'public';")
        columns = cursor.fetchall()
        cursor.close()
        return columns
    except Exception as e:
        print(Fore.RED + f"Error fetching columns for {table_name}: {e}")
        return []

# --------------------------------------------------------------
# Get Schema Summary
# --------------------------------------------------------------
def get_schema_summary(conn):
    tables = get_table_names(conn)
    if not tables:
        return "No tables found."
    schema = []
    for table in tables:
        table_name = table[0]
        columns = get_column_names(conn, table_name)
        column_list = [f"{col[0]} ({col[1]})" for col in columns]
        schema.append(f"Table: {table_name}\nColumns: {', '.join(column_list)}")
    return "\n".join(schema)

# --------------------------------------------------------------
# Print Column and Table Names
# --------------------------------------------------------------
def print_table_columns(conn):
    tables = get_table_names(conn)
    if not tables:
        print(Fore.RED + "No tables found or connection failed.")
        return
    for table in tables:
        table_name = table[0]
        print(Fore.YELLOW + f"Table: {table_name}")
        columns = get_column_names(conn, table_name)
        if columns:
            column_list = [f"{col[0]} ({col[1]})" for col in columns]
            print(Fore.BLUE + "Columns: " + Fore.MAGENTA + ", ".join(column_list))
        else:
            print(Fore.YELLOW + "No columns found for this table.")

# --------------------------------------------------------------
# OpenAI Call to Generate SQL Query
# --------------------------------------------------------------
def generate_sql_query(conn, user_message):
    client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    if not os.getenv("OPENAI_API_KEY"):
        print(Fore.RED + "OpenAI API key not set. Please set OPENAI_API_KEY environment variable.")
        return ChatResponse(reply="API key missing.", query="")
    
    schema_summary = get_schema_summary(conn)
    if "No tables found" in schema_summary:
        print(Fore.RED + "Cannot generate query: No schema available.")
        return ChatResponse(reply="No database schema available.", query="")

    response_schema = {
        "type": "object",
        "properties": {
            "reply": {"type": "string"},
            "query": {"type": "string"}
        },
        "required": ["reply", "query"],
        "additionalProperties": False
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o-2024-08-06",
            messages=[
                {"role": "system", "content": f"You are a SQL expert. Given the following database schema, generate a SQL query based on the user's request. Respond in JSON with 'reply' (a brief explanation) and 'query' (the SQL query).\nSchema:\n{schema_summary}"},
                {"role": "user", "content": user_message}
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "sql_response",
                    "schema": response_schema,
                    "strict": True
                }
            }
        )
        result = json.loads(response.choices[0].message.content)
        return ChatResponse(**result)
    except Exception as e:
        print(Fore.RED + f"OpenAI error: {str(e)}")
        return ChatResponse(reply=f"Error generating query: {str(e)}", query="")

# --------------------------------------------------------------
# Execute SQL Query
# --------------------------------------------------------------
def execute_query(conn, query):
    if not query:
        return "No query provided."
    if conn is None:
        return "Database connection failed."
    try:
        cursor = conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()
        return {"columns": column_names, "rows": results}
    except Exception as e:
        return f"Error executing query: {str(e)}"

# --------------------------------------------------------------
# Main Function to Handle Chat
# --------------------------------------------------------------
def handle_chat_request(conn, user_message):
    chat_response = generate_sql_query(conn, user_message)
    if not chat_response.query:
        print(Fore.RED + "No valid query generated. Exiting.")
        return
    
    print(Fore.GREEN + f"Agent Reply: {chat_response.reply}")
    print(Fore.BLUE + f"Generated Query: {chat_response.query}")

    result = execute_query(conn, chat_response.query)
    if isinstance(result, dict):
        print(Fore.WHITE + "Query Results:")
        print(f"Columns: {result['columns']}")
        print(f"Rows: {result['rows']}")
    else:
        print(Fore.RED + result)

# --------------------------------------------------------------
# Test the Script
# --------------------------------------------------------------
if __name__ == "__main__":
    # Single connection for the entire script
    conn = create_connection()
    if conn is None:
        print(Fore.RED + "Initial connection failed. Exiting.")
        sys.exit(1)
    
    print(Fore.GREEN + "Connected successfully!")  # Print only once here
    
    print(Fore.CYAN + "Database Schema:")
    print_table_columns(conn)
    print(Fore.CYAN + "-" * 50)

    user_question = "What are the names of players who scored more than 20 points in the 2020 season?"
    handle_chat_request(conn, user_question)

    conn.close()  # Close the connection when done
    
    