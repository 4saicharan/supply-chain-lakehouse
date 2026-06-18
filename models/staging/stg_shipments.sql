-- models/staging/stg_shipments.sql
-- Staging model: clean view on top of raw Silver shipments

SELECT
    SHIPMENT_ID,
    PRODUCT_CODE,
    PRODUCT_NAME,
    BRAND,
    SUPPLIER,
    STATUS,
    ORIGIN_WAREHOUSE,
    DEST_WAREHOUSE,
    QUANTITY_UNITS,
    FREIGHT_COST_USD,
    UNIT_WEIGHT_KG,
    TRANSIT_DAYS,
    SHIP_DATE::DATE         AS ship_date,
    EXPECTED_DELIVERY::DATE AS expected_delivery_date,
    CATEGORY,
    SILVER_LOADED_AT
FROM LAKEHOUSE_DB.SILVER.SHIPMENTS
WHERE SHIPMENT_ID IS NOT NULL
  AND FREIGHT_COST_USD > 0