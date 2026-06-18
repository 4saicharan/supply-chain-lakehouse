# scripts/extract_api.py
# Bronze Layer — Extract raw supply chain data from Open Food Facts API
# Simulates: products catalog, supplier inventory, shipment records

import requests
import json
import pandas as pd
import os
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

# ── Config ───────────────────────────────────────────────────────────────────
BRONZE_DIR = "bronze"
os.makedirs(BRONZE_DIR, exist_ok=True)

BASE_URL = "https://world.openfoodfacts.org/cgi/search.pl"
CATEGORIES = ["beverages", "snacks", "dairy", "frozen-foods", "cereals"]
WAREHOUSES = ["Chicago-IL", "Dallas-TX", "Atlanta-GA", "Seattle-WA", "Newark-NJ"]
SUPPLIERS  = ["FreshCo Supply", "GlobalFoods Inc", "NorthStar Logistics",
               "PrimePack Ltd", "SwiftShip Partners"]

# ── Step 1: Pull products from API ───────────────────────────────────────────
def fetch_products(category: str, page_size: int = 50) -> list[dict]:
    print(f"  Fetching category: {category}...")
    url = "https://world.openfoodfacts.org/api/v2/search"
    params = {
        "categories_tags_en": category,
        "fields": "code,product_name,brands,categories_tags,countries_tags,quantity,packaging,labels_tags",
        "page_size": page_size,
        "page": 1,
    }
    headers = {
        "User-Agent": "SupplyChainLakehouse/1.0 (learning-project)"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=20)
        resp.raise_for_status()
        products = resp.json().get("products", [])
        valid = [p for p in products if p.get("product_name") and p.get("code")]
        print(f"  → {len(valid)} products fetched")
        return valid
    except Exception as e:
        print(f"  ✗ Failed fetching {category}: {e}")
        return []

# ── Step 2: Simulate shipment records from products ──────────────────────────
def generate_shipments(products: list[dict]) -> list[dict]:
    shipments = []
    statuses = ["In Transit", "Delivered", "Pending", "Delayed", "Processing"]

    for i, product in enumerate(products):
        ship_date = datetime.now() - timedelta(days=random.randint(1, 30))
        delivery_date = ship_date + timedelta(days=random.randint(2, 10))
        shipments.append({
            "shipment_id":      f"SHP-{str(i+1).zfill(5)}",
            "product_code":     product.get("code"),
            "product_name":     product.get("product_name", "Unknown"),
            "brand":            product.get("brands", "Unknown"),
            "quantity_units":   random.randint(10, 500),
            "origin_warehouse": random.choice(WAREHOUSES),
            "dest_warehouse":   random.choice(WAREHOUSES),
            "supplier":         random.choice(SUPPLIERS),
            "status":           random.choice(statuses),
            "ship_date":        ship_date.isoformat(),
            "expected_delivery":delivery_date.isoformat(),
            "unit_weight_kg":   round(random.uniform(0.1, 25.0), 2),
            "freight_cost_usd": round(random.uniform(50, 2000), 2),
            "category":         product.get("categories", "").split(",")[0].strip(),
            "packaging":        product.get("packaging", "Unknown"),
            "extracted_at":     datetime.utcnow().isoformat(),
        })
    return shipments

# ── Step 3: Simulate inventory snapshot per warehouse ────────────────────────
def generate_inventory(products: list[dict]) -> list[dict]:
    inventory = []
    for product in products:
        for warehouse in random.sample(WAREHOUSES, k=random.randint(1, 3)):
            inventory.append({
                "snapshot_date":    datetime.utcnow().date().isoformat(),
                "warehouse":        warehouse,
                "product_code":     product.get("code"),
                "product_name":     product.get("product_name", "Unknown"),
                "brand":            product.get("brands", "Unknown"),
                "category":         product.get("categories", "").split(",")[0].strip(),
                "stock_units":      random.randint(0, 1000),
                "reorder_point":    random.randint(50, 200),
                "unit_cost_usd":    round(random.uniform(1.5, 150.0), 2),
                "supplier":         random.choice(SUPPLIERS),
                "extracted_at":     datetime.utcnow().isoformat(),
            })
    return inventory

# ── Step 4: Save raw JSON to Bronze folder ───────────────────────────────────
def save_bronze(data: list[dict], filename: str):
    path = os.path.join(BRONZE_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"  ✓ Saved {len(data)} records → {path}")

# ── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n🚀 Starting Bronze extraction...\n")
    run_ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")

    all_products  = []
    all_shipments = []
    all_inventory = []

    for category in CATEGORIES:
        products  = fetch_products(category, page_size=50)
        shipments = generate_shipments(products)
        inventory = generate_inventory(products)

        all_products.extend(products)
        all_shipments.extend(shipments)
        all_inventory.extend(inventory)

    # Save raw files to bronze/
    save_bronze(all_products,  f"products_raw_{run_ts}.json")
    save_bronze(all_shipments, f"shipments_raw_{run_ts}.json")
    save_bronze(all_inventory, f"inventory_raw_{run_ts}.json")

    print(f"\n✅ Bronze extraction complete!")
    print(f"   Products:  {len(all_products)}")
    print(f"   Shipments: {len(all_shipments)}")
    print(f"   Inventory: {len(all_inventory)}")