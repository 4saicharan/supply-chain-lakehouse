# scripts/transform_silver.py
# Silver Layer — Clean and standardize Bronze raw JSON into structured Parquet
# Applies: null handling, type casting, deduplication, column renaming

import os
import json
import glob
import pandas as pd
from datetime import datetime

BRONZE_DIR = "bronze"
SILVER_DIR = "silver"
os.makedirs(SILVER_DIR, exist_ok=True)

run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

# ── Helper ────────────────────────────────────────────────────────────────────
def load_latest_bronze(prefix: str) -> list[dict]:
    """Load the most recently created bronze file matching a prefix."""
    pattern = os.path.join(BRONZE_DIR, f"{prefix}_*.json")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        raise FileNotFoundError(f"No bronze files found for prefix: {prefix}")
    print(f"  Loading: {files[0]}")
    with open(files[0]) as f:
        return json.load(f)

def save_silver(df: pd.DataFrame, name: str):
    path = os.path.join(SILVER_DIR, f"{name}_{run_ts}.parquet")
    df.to_parquet(path, index=False)
    print(f"  ✓ Saved {len(df)} clean records → {path}")

# ── Transform 1: Products ─────────────────────────────────────────────────────
def transform_products() -> pd.DataFrame:
    print("\n[1/3] Transforming products...")
    raw = load_latest_bronze("products_raw")
    df = pd.DataFrame(raw)

    # Select and rename relevant columns
    df = df.rename(columns={
        "code":         "product_code",
        "product_name": "product_name",
        "brands":       "brand",
        "quantity":     "quantity",
        "packaging":    "packaging",
    })

    # Flatten list columns → comma-separated strings
    for col in ["categories_tags", "countries_tags", "labels_tags"]:
        if col in df.columns:
            df[col] = df[col].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else str(x or "")
            )

    # Keep only needed columns
    keep = ["product_code", "product_name", "brand", "quantity",
            "packaging", "categories_tags", "countries_tags", "labels_tags"]
    df = df[[c for c in keep if c in df.columns]]

    # Clean nulls
    df["product_name"] = df["product_name"].fillna("Unknown").str.strip()
    df["brand"]        = df["brand"].fillna("Unknown").str.strip()
    df["quantity"]     = df["quantity"].fillna("Unknown").str.strip()
    df["packaging"]    = df["packaging"].fillna("Unknown").str.strip()

    # Deduplicate by product_code
    before = len(df)
    df = df.drop_duplicates(subset=["product_code"])
    print(f"  Removed {before - len(df)} duplicate products")

    # Add audit columns
    df["silver_loaded_at"] = datetime.utcnow().isoformat()

    save_silver(df, "products_silver")
    return df

# ── Transform 2: Shipments ────────────────────────────────────────────────────
def transform_shipments() -> pd.DataFrame:
    print("\n[2/3] Transforming shipments...")
    raw = load_latest_bronze("shipments_raw")
    df = pd.DataFrame(raw)

    # Parse dates
    df["ship_date"]         = pd.to_datetime(df["ship_date"], errors="coerce")
    df["expected_delivery"] = pd.to_datetime(df["expected_delivery"], errors="coerce")

    # Derive transit days
    df["transit_days"] = (df["expected_delivery"] - df["ship_date"]).dt.days

    # Standardize status values
    valid_statuses = {"In Transit", "Delivered", "Pending", "Delayed", "Processing"}
    df["status"] = df["status"].where(df["status"].isin(valid_statuses), other="Unknown")

    # Clean nulls
    df["supplier"]         = df["supplier"].fillna("Unknown")
    df["origin_warehouse"] = df["origin_warehouse"].fillna("Unknown")
    df["dest_warehouse"]   = df["dest_warehouse"].fillna("Unknown")
    df["category"]         = df["category"].fillna("Uncategorized").str.strip()

    # Cast numeric types
    df["quantity_units"]   = pd.to_numeric(df["quantity_units"],   errors="coerce").fillna(0).astype(int)
    df["unit_weight_kg"]   = pd.to_numeric(df["unit_weight_kg"],   errors="coerce").round(2)
    df["freight_cost_usd"] = pd.to_numeric(df["freight_cost_usd"], errors="coerce").round(2)

    # Remove self-shipments (origin == destination)
    before = len(df)
    df = df[df["origin_warehouse"] != df["dest_warehouse"]]
    print(f"  Removed {before - len(df)} self-shipments")

    # Add audit columns
    df["silver_loaded_at"] = datetime.utcnow().isoformat()

    save_silver(df, "shipments_silver")
    return df

# ── Transform 3: Inventory ────────────────────────────────────────────────────
def transform_inventory() -> pd.DataFrame:
    print("\n[3/3] Transforming inventory...")
    raw = load_latest_bronze("inventory_raw")
    df = pd.DataFrame(raw)

    # Parse snapshot date
    df["snapshot_date"] = pd.to_datetime(df["snapshot_date"], errors="coerce")

    # Cast numeric types
    df["stock_units"]   = pd.to_numeric(df["stock_units"],   errors="coerce").fillna(0).astype(int)
    df["reorder_point"] = pd.to_numeric(df["reorder_point"], errors="coerce").fillna(0).astype(int)
    df["unit_cost_usd"] = pd.to_numeric(df["unit_cost_usd"], errors="coerce").round(2)

    # Derive total_value and reorder_flag
    df["total_inventory_value"] = (df["stock_units"] * df["unit_cost_usd"]).round(2)
    df["needs_reorder"]         = df["stock_units"] <= df["reorder_point"]

    # Clean nulls
    df["warehouse"] = df["warehouse"].fillna("Unknown")
    df["supplier"]  = df["supplier"].fillna("Unknown")
    df["category"]  = df["category"].fillna("Uncategorized").str.strip()

    # Deduplicate on warehouse + product_code + snapshot_date
    before = len(df)
    df = df.drop_duplicates(subset=["warehouse", "product_code", "snapshot_date"])
    print(f"  Removed {before - len(df)} duplicate inventory records")

    # Add audit columns
    df["silver_loaded_at"] = datetime.utcnow().isoformat()

    save_silver(df, "inventory_silver")
    return df

# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🔧 Starting Silver transformation...\n")

    products  = transform_products()
    shipments = transform_shipments()
    inventory = transform_inventory()

    print("\n✅ Silver transformation complete!")
    print(f"   Products:  {len(products)} clean records")
    print(f"   Shipments: {len(shipments)} clean records")
    print(f"   Inventory: {len(inventory)} clean records")
    print(f"\n   Columns added: transit_days, total_inventory_value, needs_reorder")
    print(f"   Output format: Parquet (columnar — optimized for Snowflake loading)")