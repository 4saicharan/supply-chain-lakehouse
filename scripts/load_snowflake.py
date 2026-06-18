# scripts/load_snowflake.py
# Loads all Silver and Gold Parquet files into Snowflake
# Uses LAKEHOUSE_DB with BRONZE, SILVER, GOLD schemas

import os
import glob
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# ── Connect to Snowflake ──────────────────────────────────────────────────────
def get_connection():
    return snowflake.connector.connect(
        account   = os.environ["SNOWFLAKE_ACCOUNT"],
        user      = os.environ["SNOWFLAKE_USER"],
        password  = os.environ["SNOWFLAKE_PASSWORD"],
        database  = os.environ["SNOWFLAKE_DATABASE"],
        warehouse = os.environ["SNOWFLAKE_WAREHOUSE"],
        role      = os.environ["SNOWFLAKE_ROLE"],
    )

# ── Load a single Parquet file into Snowflake ────────────────────────────────
def load_parquet_to_snowflake(conn, parquet_path: str, schema: str, table_name: str):
    print(f"  Loading {os.path.basename(parquet_path)} -> {schema}.{table_name}")

    df = pd.read_parquet(parquet_path)

    # Snowflake column names must be uppercase
    df.columns = [c.upper() for c in df.columns]

    # Convert datetime columns to string (Snowflake connector handles better)
    for col in df.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
        df[col] = df[col].astype(str)

    # Convert boolean to string for compatibility
    for col in df.select_dtypes(include=["bool"]).columns:
        df[col] = df[col].astype(str)

    # Set schema context
    conn.cursor().execute(f"USE SCHEMA {os.environ['SNOWFLAKE_DATABASE']}.{schema}")

    # Write to Snowflake (auto-creates table if not exists)
    success, nchunks, nrows, _ = write_pandas(
        conn,
        df,
        table_name=table_name.upper(),
        auto_create_table=True,
        overwrite=True,
    )

    if success:
        print(f"  OK  {nrows} rows loaded into {schema}.{table_name}")
    else:
        print(f"  FAILED loading {table_name}")

    return nrows

# ── Load latest file per prefix ───────────────────────────────────────────────
def get_latest(folder: str, prefix: str) -> str:
    pattern = os.path.join(folder, f"{prefix}_*.parquet")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        raise FileNotFoundError(f"No file found for {prefix} in {folder}")
    return files[0]

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\nConnecting to Snowflake...")
    conn = get_connection()
    print("Connected!\n")

    total_rows = 0

    # Silver tables
    silver_tables = [
        ("products_silver",  "SILVER", "PRODUCTS"),
        ("shipments_silver", "SILVER", "SHIPMENTS"),
        ("inventory_silver", "SILVER", "INVENTORY"),
    ]

    print("Loading Silver tables...")
    for prefix, schema, table in silver_tables:
        path = get_latest("silver", prefix)
        rows = load_parquet_to_snowflake(conn, path, schema, table)
        total_rows += rows

    # Gold tables
    gold_tables = [
        ("supplier_performance",       "GOLD", "SUPPLIER_PERFORMANCE"),
        ("warehouse_inventory_health", "GOLD", "WAREHOUSE_INVENTORY_HEALTH"),
        ("route_analysis",             "GOLD", "ROUTE_ANALYSIS"),
        ("category_summary",           "GOLD", "CATEGORY_SUMMARY"),
    ]

    print("\nLoading Gold tables...")
    for prefix, schema, table in gold_tables:
        path = get_latest("gold", prefix)
        rows = load_parquet_to_snowflake(conn, path, schema, table)
        total_rows += rows

    conn.close()

    print(f"\nSnowflake load complete!")
    print(f"  Total rows loaded: {total_rows}")
    print(f"  Silver schema: PRODUCTS, SHIPMENTS, INVENTORY")
    print(f"  Gold schema:   SUPPLIER_PERFORMANCE, WAREHOUSE_INVENTORY_HEALTH,")
    print(f"                 ROUTE_ANALYSIS, CATEGORY_SUMMARY")
    print(f"\nCheck your Snowflake UI -> LAKEHOUSE_DB -> SILVER / GOLD schemas")