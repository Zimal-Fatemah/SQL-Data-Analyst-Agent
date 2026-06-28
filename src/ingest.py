import os
import sqlite3
import pandas as pd

# Define paths relative to this script's location
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_DIR = os.path.join(BASE_DIR, "db")
DB_PATH = os.path.join(DB_DIR, "olist.db")

CSV_FILES = {
    "olist_customers_dataset": "olist_customers_dataset.csv",
    "olist_geolocation_dataset": "olist_geolocation_dataset.csv",
    "olist_order_items_dataset": "olist_order_items_dataset.csv",
    "olist_order_payments_dataset": "olist_order_payments_dataset.csv",
    "olist_order_reviews_dataset": "olist_order_reviews_dataset.csv",
    "olist_orders_dataset": "olist_orders_dataset.csv",
    "olist_products_dataset": "olist_products_dataset.csv",
    "olist_sellers_dataset": "olist_sellers_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv",
}


def get_readonly_connection(db_path: str = DB_PATH) -> sqlite3.Connection:
    """
    Returns a strictly READ-ONLY connection to the SQLite database.
    """
    db_uri = f"file:{os.path.abspath(db_path)}?mode=ro"
    return sqlite3.connect(db_uri, uri=True)


def ingest():
    print("🚀 Starting Olist dataset ingestion (ULTRA-LIGHT DEV MODE)...")

    # Ensure DB directory exists
    os.makedirs(DB_DIR, exist_ok=True)

    # Wipe out any old broken database file to clean disk space
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except OSError:
            pass

    # Connect in read-write mode just for initial creation
    conn = sqlite3.connect(DB_PATH)

    for table_name, csv_filename in CSV_FILES.items():
        csv_path = os.path.join(DATA_DIR, csv_filename)

        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"❌ Missing file: {csv_path}")

        print(f"📦 Skimming {csv_filename} -> Table: '{table_name}'...")
        
        # Read only the first 2000 rows to protect disk space completely
        df = pd.read_csv(csv_path, nrows=2000)

        # Write to SQLite
        df.to_sql(table_name, conn, if_exists="replace", index=False)

    conn.close()
    print("\n✅ Ultra-light database build complete!")
    print("-" * 50)


def verify_and_summarize():
    print("🔒 Verifying Read-Only Access & Schema Integrity...\n")

    ro_conn = get_readonly_connection()
    cursor = ro_conn.cursor()

    try:
        cursor.execute("CREATE TABLE security_test (id INT)")
        print("❌ SECURITY WARNING: Database allowed write access!")
    except sqlite3.OperationalError as e:
        print(f"🛡️ Read-Only enforcement confirmed: ({e})")

    print("\n📊 Database Summary (Row Counts):")
    for table_name in CSV_FILES.keys():
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"  • {table_name:<35} : {count:,} rows")

    ro_conn.close()
    print("\n🎯 Step 2 Finished Successfully!")


if __name__ == "__main__":
    ingest()
    verify_and_summarize()