import os
import sqlite3
import pandas as pd
from src.guardrails import validate_query

# Resolve database paths safely
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "db", "olist.db")

def get_readonly_connection() -> sqlite3.Connection:
    """Creates a strictly read-only SQLite URI connection connection."""
    db_uri = f"file:{os.path.abspath(DB_PATH)}?mode=ro"
    return sqlite3.connect(db_uri, uri=True)

def get_database_schema() -> str:
    """
    Crawls the SQLite database and returns a comprehensive string representation
    of all tables, columns, and sample schemas for the LLM to read.
    """
    if not os.path.exists(DB_PATH):
        return "Error: Database file does not exist yet. Please run ingest.py first."

    conn = get_readonly_connection()
    cursor = conn.cursor()
    
    # Fetch all table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    schema_dump = []
    schema_dump.append("=== OLIST E-COMMERCE DATABASE SCHEMA ===")
    
    for table in tables:
        schema_dump.append(f"\nTable: {table}")
        schema_dump.append("-" * len(f"Table: {table}"))
        
        # Get column info
        cursor.execute(f"PRAGMA table_info({table});")
        columns = cursor.fetchall()
        
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_flag = " [PRIMARY KEY]" if pk else ""
            schema_dump.append(f"  • {col_name} ({col_type}){pk_flag}")
            
    conn.close()
    return "\n".join(schema_dump)

def execute_agent_query(sql_query: str) -> str:
    """
    Validates a raw SQL string via the guardrails module and, if safe, 
    executes it read-only against the database, returning results formatted as a markdown table.
    """
    # 1. Pass the query through our AST validation gate
    is_valid, validation_result = validate_query(sql_query)
    
    if not is_valid:
        return f" Security Guardrail Exception: {validation_result}"
        
    # 2. Run the validated query securely
    try:
        conn = get_readonly_connection()
        
        # Read the SQL query directly into a Pandas DataFrame
        df = pd.read_sql_query(validation_result, conn)
        conn.close()
        
        if df.empty:
            return "Query executed successfully, but returned 0 result rows."
            
        # Convert to a scannable Markdown table string for the LLM/UI to render
        return df.to_markdown(index=False)
        
    except Exception as e:
        return f"❌ Database Execution Error: {str(e)}"

# Self-test code block
if __name__ == "__main__":
    print(" Testing Database Tools Subsystem...\n")
    
    print("1. Extracting Database Schema...")
    schema = get_database_schema()
    print(f"✅ Extracted {len(schema.splitlines())} lines of structural metadata.")
    
    print("\n2. Executing a safe exploratory test query via tools layer...")
    test_sql = "SELECT customer_state, COUNT(*) as customer_count FROM olist_customers_dataset GROUP BY customer_state ORDER BY customer_count DESC LIMIT 5"
    results = execute_agent_query(test_sql)
    print("\n" + results)