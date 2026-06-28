import os
import logging
from datetime import datetime
import sqlglot
import sqlglot.expressions as exp

# Set up logging directories and configurations
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGS_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOGS_DIR, "query_guardrails.log")

# Configure logger
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def validate_query(sql: str) -> tuple[bool, str]:
    """
    Validates a generated SQL statement using a formal AST parser.
    Enforces read-only syntax, blocks multi-statements, and guarantees a result row LIMIT.
    
    Returns:
        tuple[bool, str]: (is_valid, validated_sql_or_error_message)
    """
    clean_sql = sql.strip().strip("`").strip()
    if clean_sql.upper().startswith("SQL"):
        clean_sql = clean_sql[3:].strip()

    try:
        # Parse the SQL using SQLite dialect rules
        parsed_statements = sqlglot.parse(clean_sql, read="sqlite")
        
        # 1. Reject multi-statement queries (separated by ;)
        if len(parsed_statements) != 1:
            error_msg = f"REJECTED: Multiple statements detected ({len(parsed_statements)} statements found)."
            logging.warning(f"{error_msg} | Query: [ {clean_sql} ]")
            return False, error_msg
            
        statement = parsed_statements[0]
        
        # 2. Reject anything that isn't structurally a SELECT statement
        if not isinstance(statement, exp.Select):
            error_msg = f"REJECTED: Statement type '{type(statement).__name__}' is not a SELECT expression."
            logging.warning(f"{error_msg} | Query: [ {clean_sql} ]")
            return False, error_msg

        # 3. Enforce and limit result rows (Cap at 100)
        limit_clause = statement.args.get("limit")
        if limit_clause:
            try:
                current_limit = int(str(limit_clause.expression))
                if current_limit > 100:
                    # Strip out the oversized limit and rewrite safely
                    statement.args.pop("limit", None)
                    statement = statement.limit(100)
            except (ValueError, TypeError):
                statement.args.pop("limit", None)
                statement = statement.limit(100)
        else:
            # Inject a limit clause if missing
            statement = statement.limit(100)

        # Re-serialize back to a valid SQLite string
        validated_sql = statement.sql(dialect="sqlite")
        
        # Log success
        logging.info(f"ALLOWED: Query passed validation | Final SQL: [ {validated_sql} ]")
        return True, validated_sql

    except sqlglot.errors.ParseError as e:
        error_msg = f"REJECTED: Invalid SQL syntax or unparsable expression. Error: {str(e)}"
        logging.error(f"{error_msg} | Query: [ {clean_sql} ]")
        return False, error_msg


# Built-in self-test block to prove functionality
if __name__ == "__main__":
    print("🧪 Running Guardrails Layer Validation Tests...\n")
    
    test_cases = {
        "Valid Query": "SELECT customer_id, customer_city FROM olist_customers_dataset WHERE customer_state = 'SP'",
        "No Limit Check": "SELECT * FROM olist_orders_dataset",
        "Excessive Limit Check": "SELECT * FROM olist_orders_dataset LIMIT 50000",
        "Multi-Statement Exploit": "SELECT * FROM olist_sellers_dataset; DROP TABLE olist_customers_dataset;",
        "Write Attack (Deception)": "SELECT * FROM olist_products_dataset; UPDATE olist_products_dataset SET product_weight_g = 0",
        "Direct Write Query": "DELETE FROM olist_orders_dataset WHERE order_id = '123'",
        "Syntax Garbage": "SELECT FROM CHICKEN NUGGET WHERE WHERE == 1"
    }
    
    for label, query in test_cases.items():
        is_valid, result = validate_query(query)
        status = "🟢 PASSED" if is_valid else "🔴 REJECTED"
        print(f"[{label}] -> {status}")
        print(f"   Input:  {query}")
        print(f"   Output: {result}\n" + "-"*40)
        
    print(f"\n📁 Audit logs recorded instantly to: logs/query_guardrails.log")