# Supply Chain Data Lakehouse

End-to-end data engineering pipeline built with Python and Snowflake. Implements a full Medallion Architecture (Bronze → Silver → Gold) using real supply chain data from the Open Food Facts public API.

## Architecture

```
Open Food Facts API (live data)
        ↓
Bronze Layer — raw JSON (194 products, 194 shipments, 403 inventory records)
        ↓
Silver Layer — cleaned Parquet (deduped, typed, validated)
        ↓
Gold Layer — business aggregations (4 tables)
        ↓
Snowflake — 753 rows across 7 tables in SILVER + GOLD schemas
        ↓
dbt-style SQL models — supplier scorecard, inventory health
```

## Tech Stack

| Tool | Purpose |
|---|---|
| Python 3.x | Pipeline orchestration |
| Open Food Facts API | Live supply chain product data |
| Pandas + PyArrow | Transformations and Parquet I/O |
| Snowflake | Cloud data warehouse |
| snowflake-connector-python | Python to Snowflake loader |
| dbt-style SQL | Business mart models |

## Pipeline Modules

### 1. Bronze — Raw Ingestion (`scripts/extract_api.py`)
- Calls Open Food Facts API across 5 product categories (beverages, snacks, dairy, frozen-foods, cereals)
- Simulates realistic shipment records across 5 US warehouses and 5 suppliers
- Simulates warehouse inventory snapshots with stock levels and reorder points
- Saves raw JSON files to `bronze/` folder
- **Output:** 194 products, 194 shipments, 403 inventory records

### 2. Silver — Transformation (`scripts/transform_silver.py`)
- Reads raw Bronze JSON and applies cleaning rules
- Null handling, type casting, deduplication, date parsing
- Derives new columns: `transit_days`, `total_inventory_value`, `needs_reorder`
- Removes self-shipments (origin = destination) and validates status values
- Saves clean Parquet files to `silver/`
- **Output:** 177 products, 156 shipments, 389 inventory records

### 3. Gold — Business Aggregations (`scripts/transform_gold.py`)
Builds 4 business-ready aggregation tables:

| Table | Description |
|---|---|
| `supplier_performance` | Delivery rate, avg transit days, freight cost per supplier |
| `warehouse_inventory_health` | Stock levels, reorder alerts per warehouse |
| `route_analysis` | Busiest and most expensive shipping routes |
| `category_summary` | Category-level supply chain KPIs |

### 4. Snowflake Loader (`scripts/load_snowflake.py`)
- Connects to Snowflake using environment variables
- Auto-creates tables in SILVER and GOLD schemas
- Loads all Parquet files using `write_pandas` for high performance
- **753 total rows loaded across 7 tables**

### 5. dbt SQL Models (`dbt_project/models/`)
- `staging/stg_shipments.sql` — clean view on Silver shipments
- `staging/stg_inventory.sql` — clean view on Silver inventory  
- `marts/mart_supplier_scorecard.sql` — supplier grading A/B/C/D based on delivery rate

## Key Business Insights

- **Supplier Scorecard** — grades each supplier A-D based on delivery performance, transit time, and freight cost
- **Warehouse Reorder Alerts** — flags understocked SKUs across all 5 warehouse locations
- **Route Analysis** — identifies highest-cost and most-delayed shipping lanes
- **Category KPIs** — inventory value and shipment volume broken down by product category

## Project Structure

```
supply-chain-lakehouse/
├── bronze/                    # Raw JSON files from API
├── silver/                    # Cleaned Parquet files  
├── gold/                      # Aggregated Parquet files
├── scripts/
│   ├── extract_api.py         # Bronze ingestion
│   ├── transform_silver.py    # Silver cleaning + validation
│   ├── transform_gold.py      # Gold business aggregations
│   └── load_snowflake.py      # Snowflake loader
├── dbt_project/
│   ├── models/
│   │   ├── staging/           # Staging SQL views
│   │   └── marts/             # Business mart SQL models
│   └── dbt_project.yml        # dbt configuration
├── .env.example               # Credential template
└── README.md
```

## Setup & Run

```bash
# 1. Clone the repo
git clone https://github.com/YOUR_USERNAME/supply-chain-lakehouse.git
cd supply-chain-lakehouse

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux

# 3. Install dependencies
pip install requests pandas pyarrow python-dotenv snowflake-connector-python

# 4. Configure credentials
cp .env.example .env
# Fill in your Snowflake account, user, password, database, warehouse

# 5. Run the full pipeline
python scripts/extract_api.py       # Bronze
python scripts/transform_silver.py  # Silver
python scripts/transform_gold.py    # Gold
python scripts/load_snowflake.py    # Load to Snowflake
```

## Environment Variables

```env
SNOWFLAKE_ACCOUNT=your_account_identifier
SNOWFLAKE_USER=LAKEHOUSE_USER
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=LAKEHOUSE_DB
SNOWFLAKE_WAREHOUSE=LAKEHOUSE_WH
SNOWFLAKE_ROLE=LAKEHOUSE_ROLE
```

## Skills Demonstrated

- Medallion architecture design (Bronze / Silver / Gold)
- REST API ingestion with error handling and pagination
- Data cleaning and transformation with Pandas
- Columnar storage with Parquet and PyArrow
- Cloud data warehousing with Snowflake
- dbt-style SQL modeling and business mart design
- Python pipeline orchestration end-to-end
