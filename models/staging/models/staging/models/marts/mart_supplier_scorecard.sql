-- models/marts/mart_supplier_scorecard.sql
-- Final business mart: supplier reliability scorecard
-- Used by operations team to evaluate and rank suppliers

WITH shipment_stats AS (
    SELECT
        SUPPLIER,
        COUNT(*)                                          AS total_shipments,
        SUM(QUANTITY_UNITS)                               AS total_units_shipped,
        AVG(FREIGHT_COST_USD)                             AS avg_freight_cost,
        SUM(FREIGHT_COST_USD)                             AS total_freight_spend,
        AVG(TRANSIT_DAYS)                                 AS avg_transit_days,
        SUM(CASE WHEN STATUS = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
        SUM(CASE WHEN STATUS = 'Delayed'   THEN 1 ELSE 0 END) AS delayed,
        SUM(CASE WHEN STATUS = 'In Transit'THEN 1 ELSE 0 END) AS in_transit
    FROM LAKEHOUSE_DB.SILVER.SHIPMENTS
    GROUP BY SUPPLIER
),

scored AS (
    SELECT
        *,
        ROUND(delivered / total_shipments * 100, 1)  AS delivery_rate_pct,
        ROUND(delayed   / total_shipments * 100, 1)  AS delay_rate_pct,
        ROUND(avg_freight_cost, 2)                   AS avg_freight_cost_usd,
        CASE
            WHEN delivery_rate_pct >= 80 THEN 'A - Excellent'
            WHEN delivery_rate_pct >= 60 THEN 'B - Good'
            WHEN delivery_rate_pct >= 40 THEN 'C - Average'
            ELSE                              'D - Poor'
        END AS supplier_grade
    FROM shipment_stats
)

SELECT
    SUPPLIER,
    supplier_grade,
    total_shipments,
    total_units_shipped,
    delivered,
    delayed,
    delivery_rate_pct,
    delay_rate_pct,
    ROUND(avg_transit_days, 1)   AS avg_transit_days,
    avg_freight_cost_usd,
    ROUND(total_freight_spend, 2) AS total_freight_spend,
    CURRENT_TIMESTAMP()           AS mart_refreshed_at
FROM scored
ORDER BY delivery_rate_pct DESC