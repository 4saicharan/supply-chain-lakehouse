# scripts/transform_gold.py
import os
import glob
import pandas as pd
from datetime import datetime

SILVER_DIR = "silver"
GOLD_DIR   = "gold"
os.makedirs(GOLD_DIR, exist_ok=True)

run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

def load_latest_silver(prefix: str) -> pd.DataFrame:
    pattern = os.path.join(SILVER_DIR, f"{prefix}_*.parquet")
    files = sorted(glob.glob(pattern), reverse=True)
    if not files:
        raise FileNotFoundError(f"No silver files found for: {prefix}")
    print(f"  Loading: {files[0]}")
    return pd.read_parquet(files[0])

def save_gold(df: pd.DataFrame, name: str):
    path = os.path.join(GOLD_DIR, f"{name}_{run_ts}.parquet")
    df.to_parquet(path, index=False)
    print(f"  Saved {len(df)} rows -> {path}")

def gold_supplier_performance(shipments: pd.DataFrame):
    print("\n[1/4] Building supplier performance...")
    df = shipments.groupby("supplier").agg(
        total_shipments      = ("shipment_id",      "count"),
        delivered_count      = ("status",           lambda x: (x == "Delivered").sum()),
        delayed_count        = ("status",           lambda x: (x == "Delayed").sum()),
        avg_transit_days     = ("transit_days",     "mean"),
        avg_freight_cost_usd = ("freight_cost_usd", "mean"),
        total_freight_cost   = ("freight_cost_usd", "sum"),
        total_units_shipped  = ("quantity_units",   "sum"),
    ).reset_index()
    df["delivery_rate_pct"]    = (df["delivered_count"] / df["total_shipments"] * 100).round(1)
    df["avg_transit_days"]     = df["avg_transit_days"].round(1)
    df["avg_freight_cost_usd"] = df["avg_freight_cost_usd"].round(2)
    df["total_freight_cost"]   = df["total_freight_cost"].round(2)
    df["gold_loaded_at"]       = datetime.utcnow().isoformat()
    save_gold(df, "supplier_performance")

def gold_warehouse_inventory(inventory: pd.DataFrame):
    print("\n[2/4] Building warehouse inventory health...")
    df = inventory.groupby("warehouse").agg(
        total_skus            = ("product_code",          "nunique"),
        total_stock_units     = ("stock_units",           "sum"),
        total_inventory_value = ("total_inventory_value", "sum"),
        skus_needing_reorder  = ("needs_reorder",         "sum"),
        avg_stock_per_sku     = ("stock_units",           "mean"),
        avg_unit_cost         = ("unit_cost_usd",         "mean"),
    ).reset_index()
    df["reorder_alert_pct"]     = (df["skus_needing_reorder"] / df["total_skus"] * 100).round(1)
    df["total_inventory_value"] = df["total_inventory_value"].round(2)
    df["avg_stock_per_sku"]     = df["avg_stock_per_sku"].round(1)
    df["avg_unit_cost"]         = df["avg_unit_cost"].round(2)
    df["gold_loaded_at"]        = datetime.utcnow().isoformat()
    save_gold(df, "warehouse_inventory_health")

def gold_route_analysis(shipments: pd.DataFrame):
    print("\n[3/4] Building route analysis...")
    df = shipments.groupby(["origin_warehouse", "dest_warehouse"]).agg(
        shipment_count     = ("shipment_id",      "count"),
        total_units        = ("quantity_units",   "sum"),
        avg_freight_cost   = ("freight_cost_usd", "mean"),
        total_freight_cost = ("freight_cost_usd", "sum"),
        avg_transit_days   = ("transit_days",     "mean"),
        delayed_shipments  = ("status",           lambda x: (x == "Delayed").sum()),
    ).reset_index()
    df["route"]              = df["origin_warehouse"] + " -> " + df["dest_warehouse"]
    df["avg_freight_cost"]   = df["avg_freight_cost"].round(2)
    df["total_freight_cost"] = df["total_freight_cost"].round(2)
    df["avg_transit_days"]   = df["avg_transit_days"].round(1)
    df["gold_loaded_at"]     = datetime.utcnow().isoformat()
    save_gold(df, "route_analysis")

def gold_category_summary(shipments: pd.DataFrame, inventory: pd.DataFrame):
    print("\n[4/4] Building category summary...")
    ship_agg = shipments.groupby("category").agg(
        total_shipments     = ("shipment_id",      "count"),
        total_units_shipped = ("quantity_units",   "sum"),
        total_freight_cost  = ("freight_cost_usd", "sum"),
        avg_transit_days    = ("transit_days",     "mean"),
    ).reset_index()
    inv_agg = inventory.groupby("category").agg(
        total_stock_value    = ("total_inventory_value", "sum"),
        total_skus           = ("product_code",          "nunique"),
        skus_needing_reorder = ("needs_reorder",         "sum"),
    ).reset_index()
    df = ship_agg.merge(inv_agg, on="category", how="outer")
    df["avg_transit_days"]   = df["avg_transit_days"].round(1)
    df["total_freight_cost"] = df["total_freight_cost"].round(2)
    df["total_stock_value"]  = df["total_stock_value"].round(2)
    df["gold_loaded_at"]     = datetime.utcnow().isoformat()
    save_gold(df, "category_summary")

if __name__ == "__main__":
    print("\nStarting Gold transformation...\n")
    shipments = load_latest_silver("shipments_silver")
    inventory = load_latest_silver("inventory_silver")
    gold_supplier_performance(shipments)
    gold_warehouse_inventory(inventory)
    gold_route_analysis(shipments)
    gold_category_summary(shipments, inventory)
    print("\nGold layer complete!")
    print("  1. supplier_performance       - reliability + cost per supplier")
    print("  2. warehouse_inventory_health - stock levels + reorder alerts")
    print("  3. route_analysis             - busiest + most expensive routes")
    print("  4. category_summary           - category-level supply chain KPIs")