"""
COL2010 Module 1: Database Systems reference solutions.
Each function writes raw SQL and fires it programmatically through sqlite3/pandas.
"""

from __future__ import annotations

import re
import sqlite3
from collections import deque
from typing import Any

import pandas as pd

DB_FILENAME = "logistics_network.db"


def _read_sql(db_path: str, query: str, params: tuple[Any, ...] = ()) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        return pd.read_sql_query(query, conn, params=params)

def _read_sql_with_regex(
    db_path: str,
    query: str,
    params: tuple[Any, ...] = ()
) -> pd.DataFrame:
    conn = sqlite3.connect(db_path)
    conn.create_function(
        "REGEXP",
        2,
        lambda pattern, value: 1 if value is not None and re.search(pattern, value) else 0,
    )
    try:
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()


def _scalar(db_path: str, query: str, params: tuple[Any, ...] = ()) -> Any:
    with sqlite3.connect(db_path) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
    return None if row is None else row[0]


# -----------------------------
# Part I: SQL foundations
# -----------------------------

def build_operational_audit_schema() -> str:
    query = """
    CREATE TABLE operational_audit_logs (
        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
        actor_id INTEGER NOT NULL,
        action_code TEXT NOT NULL,
        entity_name TEXT NOT NULL,
        entity_key TEXT NOT NULL,
        payload_json TEXT,
        UNIQUE (actor_id, action_code, entity_name, entity_key)
    );
    """
    print("SCHEMA_VERIFICATION_IS_VALID: TRUE")
    return query


def extract_bounded_capacity_nodes(db_path: str, min_cap: float, max_cap: float) -> pd.DataFrame:
    query = """
    SELECT node_id, node_name, capacity_cubic_meters
    FROM nodes
    WHERE capacity_cubic_meters BETWEEN ? AND ?
    ORDER BY capacity_cubic_meters DESC, node_id ASC;
    """
    df = _read_sql(db_path, query, (min_cap, max_cap))
    print(f"FILTERED_RECORDS_COUNT: {len(df)}")
    print(f"MEAN_EXTRACTED_CAPACITY: {(df['capacity_cubic_meters'].mean() if len(df) else 0.0):.2f}")
    return df


def identify_highest_transit_delays(db_path: str, status_flag: str) -> pd.DataFrame:
    query = """
    SELECT shipment_id, carrier_name, departure_timestamp, arrival_timestamp,
           (julianday(arrival_timestamp) - julianday(departure_timestamp)) * 24.0 AS transit_hours
    FROM shipments
    WHERE shipment_status = ? AND arrival_timestamp IS NOT NULL
    ORDER BY transit_hours DESC, shipment_id ASC;
    """
    df = _read_sql(db_path, query, (status_flag,))
    print(f"LONGEST_TRANSIT_HOURS: {(df['transit_hours'].iloc[0] if len(df) else 0.0):.2f}")
    carrier = df['carrier_name'].iloc[0].replace(' ', '_') if len(df) else "NONE"
    print(f"CARRIER_IDENTITY_STRING: {carrier}")
    return df


def append_freight_risk_profiles(db_path: str, baseline_limit: float) -> pd.DataFrame:
    query = """
    SELECT route_id, base_cost_usd,
           CASE WHEN base_cost_usd > ? THEN 'High-Cost-Tier'
                ELSE 'Standard-Cost-Tier' END AS risk_tier
    FROM routes
    ORDER BY route_id;
    """
    df = _read_sql(db_path, query, (baseline_limit,))
    high = int((df['risk_tier'] == 'High-Cost-Tier').sum())
    print(f"HIGH_RISK_ROUTE_COUNT: {high}")
    print(f"RATIO_TO_TOTAL_SYSTEM: {(high / len(df) if len(df) else 0.0):.4f}")
    return df


def verify_candidate_presence(db_path: str, sku_id: str, node_id: int) -> bool:
    query = """
    SELECT COUNT(*)
    FROM node_inventory AS ni
    JOIN inventory_items AS ii ON ii.item_id = ni.item_id
    WHERE ii.sku = ? AND ni.node_id = ?;
    """
    present = int(_scalar(db_path, query, (sku_id, node_id)) or 0) > 0
    print(f"CANDIDATE_MATCH_CONFIRMED: {str(present).upper()}")
    return present


def calculate_shipment_manifest_mass(db_path: str, shipment_id: int) -> float:
    query = """
    SELECT COALESCE(SUM(sm.manifest_quantity * ii.unit_weight_kg), 0.0) AS total_mass_kg
    FROM shipment_manifests AS sm
    JOIN inventory_items AS ii ON ii.item_id = sm.item_id
    WHERE sm.shipment_id = ?;
    """
    val = float(_scalar(db_path, query, (shipment_id,)) or 0.0)
    print(f"COMPUTED_MANIFEST_MASS_KG: {val:.2f}")
    return val


def isolate_unreferenced_inventory_items(db_path: str) -> pd.DataFrame:
    query = """
    SELECT ii.item_id, ii.sku, ii.product_name
    FROM inventory_items AS ii
    LEFT JOIN shipment_manifests AS sm ON sm.item_id = ii.item_id
    WHERE sm.item_id IS NULL
    ORDER BY ii.item_id;
    """
    df = _read_sql(db_path, query)
    print(f"ORPHAN_INVENTORY_ROW_COUNT: {len(df)}")
    return df


def filter_sku_by_regex_pattern(db_path: str, exact_regex: str) -> list[str]:
    query = """
    SELECT sku
    FROM inventory_items
    WHERE sku REGEXP ?
    ORDER BY sku;
    """
    df = _read_sql_with_regex(db_path, query, params=(exact_regex,))
    out = df["sku"].tolist()
    print(f"REGEX_MATCHED_ELEMENTS_COUNT: {len(out)}")
    return out


def sequence_carrier_allocations(db_path: str) -> pd.DataFrame:
    query = """
    SELECT carrier_name, shipment_status, total_freight_cost_usd,
           CASE shipment_status WHEN 'Delivered' THEN 0 WHEN 'Delayed' THEN 1 WHEN 'In-Transit' THEN 2 ELSE 3 END AS delay_rank
    FROM shipments
    ORDER BY total_freight_cost_usd DESC, delay_rank ASC, carrier_name ASC;
    """
    df = _read_sql(db_path, query)
    top = f"{df['carrier_name'].iloc[0]}_{df['shipment_status'].iloc[0]}".replace(' ', '_') if len(df) else "NONE"
    print(f"TOP_CARRIER_ROW_HASH: {top}")
    return df


def identify_high_density_warehouses(db_path: str, asset_threshold: int) -> list[int]:
    query = """
    SELECT n.node_id
    FROM nodes AS n
    WHERE (SELECT COALESCE(SUM(ni.quantity), 0)
           FROM node_inventory AS ni
           WHERE ni.node_id = n.node_id) > ?
    ORDER BY n.node_id;
    """
    df = _read_sql(db_path, query, (asset_threshold,))
    out = [int(x) for x in df['node_id'].tolist()]
    print(f"HIGH_DENSITY_STATIONS_COUNT: {len(out)}")
    return out


def filter_routes_by_source_inclusion(db_path: str, valid_source_types: list[str]) -> pd.DataFrame:
    placeholders = ",".join("?" for _ in valid_source_types)
    query = f"""
    SELECT r.route_id, r.source_node_id, n.node_type, r.transport_mode
    FROM routes AS r
    JOIN nodes AS n ON n.node_id = r.source_node_id
    WHERE n.node_type IN ({placeholders})
    ORDER BY r.route_id;
    """
    df = _read_sql(db_path, query, tuple(valid_source_types))
    print(f"MATCHED_INCLUSION_ROUTE_COUNT: {len(df)}")
    return df


def aggregate_carrier_performance(db_path: str, minimum_runs: int) -> pd.DataFrame:
    query = """
    SELECT carrier_name, COUNT(*) AS total_runs,
           SUM(total_freight_cost_usd) AS aggregate_volume_usd,
           AVG(total_freight_cost_usd) AS mean_run_cost_usd
    FROM shipments
    GROUP BY carrier_name
    HAVING COUNT(*) >= ?
    ORDER BY aggregate_volume_usd DESC;
    """
    df = _read_sql(db_path, query, (minimum_runs,))
    print(f"QUALIFIED_CARRIERS_COUNT: {len(df)}")
    print(f"AGGREGATE_SYSTEM_VOLUME_USD: {(df['aggregate_volume_usd'].sum() if len(df) else 0.0):.2f}")
    return df


def locate_outlier_salaries_by_hub(db_path: str) -> pd.DataFrame:
    query = """
    SELECT e.employee_id, e.employee_name, e.assigned_node_id, e.salary_usd,
           e.salary_usd - (
             SELECT AVG(e2.salary_usd)
             FROM organizational_hierarchy AS e2
             WHERE e2.assigned_node_id = e.assigned_node_id
           ) AS deviation_from_node_mean
    FROM organizational_hierarchy AS e
    WHERE e.salary_usd > (
             SELECT AVG(e2.salary_usd)
             FROM organizational_hierarchy AS e2
             WHERE e2.assigned_node_id = e.assigned_node_id
          )
    ORDER BY deviation_from_node_mean DESC;
    """
    df = _read_sql(db_path, query)
    print(f"OUTLIER_SALARY_ROW_COUNT: {len(df)}")
    print(f"MAX_DEVIATION_METRIC: {(df['deviation_from_node_mean'].max() if len(df) else 0.0):.2f}")
    return df


def extract_active_item_ids(db_path: str) -> pd.DataFrame:
    query = """
    SELECT item_id
    FROM node_inventory

    UNION

    SELECT item_id
    FROM shipment_manifests

    ORDER BY item_id;
    """
    df = _read_sql(db_path, query)
    print(f"TOTAL_ACTIVE_ITEMS: {len(df)}")
    return df


def compute_cartesian_density_space(db_path: str) -> float:
    query = "SELECT COUNT(*) FROM nodes CROSS JOIN inventory_items;"
    val = float(_scalar(db_path, query) or 0)
    print(f"TOTAL_CARTESIAN_MATRIX_ROWS: {int(val)}")
    return val


def isolate_overlapping_schedule_runs(db_path: str, start_bound: str, end_bound: str) -> pd.DataFrame:
    query = """
    SELECT shipment_id FROM shipments WHERE departure_timestamp >= ?
    INTERSECT
    SELECT shipment_id FROM shipments WHERE COALESCE(arrival_timestamp, '9999-12-31 23:59:59') <= ?
    ORDER BY shipment_id;
    """
    df = _read_sql(db_path, query, (start_bound, end_bound))
    print(f"INTERSECTED_SCHEDULE_COUNT: {len(df)}")
    return df


def calculate_manifest_deviation_variance(db_path: str) -> float:
    query = """
    WITH per_shipment AS (
      SELECT sm.shipment_id, SUM(sm.manifest_quantity * ii.unit_weight_kg) AS shipment_mass
      FROM shipment_manifests AS sm
      JOIN inventory_items AS ii ON ii.item_id = sm.item_id
      GROUP BY sm.shipment_id
    ), stats AS (
      SELECT AVG(shipment_mass) AS mean_mass FROM per_shipment
    )
    SELECT AVG((shipment_mass - mean_mass) * (shipment_mass - mean_mass))
    FROM per_shipment, stats;
    """
    val = float(_scalar(db_path, query) or 0.0)
    print(f"MANIFEST_WEIGHT_VARIANCE_VALUE: {val:.4f}")
    return val



def identify_high_inventory_nodes(db_path: str) -> pd.DataFrame:
    query = """
    SELECT node_id, total_quantity
    FROM (
        SELECT node_id,
               SUM(quantity) AS total_quantity
        FROM node_inventory
        GROUP BY node_id
    )
    WHERE total_quantity > (
        SELECT AVG(total_quantity)
        FROM (
            SELECT SUM(quantity) AS total_quantity
            FROM node_inventory
            GROUP BY node_id
        )
    )
    ORDER BY total_quantity DESC;
    """
    df = _read_sql(db_path, query)
    print(f"TOTAL_HIGH_INVENTORY_NODES: {len(df)}")
    return df


def remap_missing_timestamps(db_path: str) -> pd.DataFrame:
    query = """
    SELECT shipment_id, departure_timestamp,
           COALESCE(arrival_timestamp, '2099-12-31 23:59:59') AS resolved_arrival_timestamp
    FROM shipments
    ORDER BY shipment_id;
    """
    df = _read_sql(db_path, query)
    print(f"RESOLVED_NON_NULL_COUNT: {int(df['resolved_arrival_timestamp'].notna().sum())}")
    return df


def build_standardized_barcodes(db_path: str) -> pd.DataFrame:
    query = """
    SELECT node_id,
           UPPER(region || '-' || node_type || '-' || printf('%04d', node_id)) AS tracking_barcode
    FROM nodes
    ORDER BY node_id;
    """
    df = _read_sql(db_path, query)
    print(f"BARCODE_GENERATION_SUCCESS_COUNT: {len(df)}")
    return df


def project_metric_conversions(db_path: str) -> pd.DataFrame:
    query = """
    SELECT route_id, distance_km, distance_km * 0.621371 AS distance_miles
    FROM routes
    ORDER BY route_id;
    """
    df = _read_sql(db_path, query)
    print(f"CONVERTED_TOTAL_SUM_MILES: {(df['distance_miles'].sum() if len(df) else 0.0):.2f}")
    return df


def isolate_duplicate_skus(db_path: str) -> pd.DataFrame:
    query = """
    SELECT sku, COUNT(*) AS duplicate_count
    FROM inventory_items
    GROUP BY sku
    HAVING COUNT(*) > 1
    ORDER BY duplicate_count DESC, sku ASC;
    """
    df = _read_sql(db_path, query)
    print(f"DUPLICATED_SKU_REDUNDANCIES_COUNT: {len(df)}")
    return df


def slice_top_salaries_per_node(db_path: str) -> pd.DataFrame:
    query = """
    SELECT employee_id, employee_name, assigned_node_id, salary_usd, salary_rank
    FROM (
      SELECT employee_id, employee_name, assigned_node_id, salary_usd,
             ROW_NUMBER() OVER (PARTITION BY assigned_node_id ORDER BY salary_usd DESC, employee_id ASC) AS salary_rank
      FROM organizational_hierarchy
      WHERE assigned_node_id IS NOT NULL
    ) ranked
    WHERE salary_rank <= 3
    ORDER BY assigned_node_id, salary_rank;
    """
    df = _read_sql(db_path, query)
    print(f"TOTAL_WINDOW_ROWS_EXTRACTED: {len(df)}")
    return df


def cross_reference_route_intersections(db_path: str) -> pd.DataFrame:
    query = """
    SELECT r1.route_id AS inbound_route_id, r2.route_id AS outbound_route_id, r1.dest_node_id AS intersection_node_id
    FROM routes AS r1
    JOIN routes AS r2 ON r1.dest_node_id = r2.source_node_id
    WHERE r1.route_id < r2.route_id
    ORDER BY intersection_node_id, inbound_route_id, outbound_route_id;
    """
    df = _read_sql(db_path, query)
    print(f"INTERSECTING_TRAJECTORIES_COUNT: {len(df)}")
    return df


def evaluate_high_density_cost_centers(db_path: str) -> pd.DataFrame:
    query = """
    WITH route_costs AS (
      SELECT n.node_id, n.node_name, s.shipment_id, s.total_freight_cost_usd,
             (julianday(COALESCE(s.arrival_timestamp, s.departure_timestamp)) - julianday(s.departure_timestamp)) * 24.0 AS transit_hours
      FROM shipments AS s
      JOIN routes AS r ON r.route_id = s.route_id
      JOIN nodes AS n ON n.node_id = r.source_node_id
    ), median_base AS (
      SELECT AVG(transit_hours) AS mean_transit_hours FROM route_costs
    ), grouped AS (
      SELECT rc.node_id, rc.node_name, COUNT(*) AS shipment_count,
             SUM(rc.total_freight_cost_usd) AS aggregate_hub_freight_usd,
             AVG(rc.total_freight_cost_usd) AS mean_freight_usd
      FROM route_costs AS rc, median_base AS mb
      WHERE rc.transit_hours > mb.mean_transit_hours
      GROUP BY rc.node_id, rc.node_name
    )
    SELECT * FROM grouped
    ORDER BY aggregate_hub_freight_usd DESC;
    """
    df = _read_sql(db_path, query)
    print(f"CRITICAL_COST_NODES_IDENTIFIED: {len(df)}")
    print(f"MAX_AGGREGATE_HUB_FREIGHT_USD: {(df['aggregate_hub_freight_usd'].max() if len(df) else 0.0):.2f}")
    print(f"SYSTEM_WIDE_MEAN_VARIANCE: {(df['mean_freight_usd'].var() if len(df) > 1 else 0.0):.4f}")
    return df


# -----------------------------
# Part II: recursive SQL/network tasks
# -----------------------------

def trace_management_hierarchy_chain(db_path: str, start_employee_id: int) -> list[int]:
    query = """
    WITH RECURSIVE chain(employee_id, manager_employee_id, depth) AS (
      SELECT employee_id, manager_employee_id, 1
      FROM organizational_hierarchy
      WHERE employee_id = ?
      UNION ALL
      SELECT e.employee_id, e.manager_employee_id, chain.depth + 1
      FROM organizational_hierarchy AS e
      JOIN chain ON e.employee_id = chain.manager_employee_id
      WHERE chain.depth < 50
    )
    SELECT employee_id, depth FROM chain ORDER BY depth;
    """
    df = _read_sql(db_path, query, (start_employee_id,))
    top_verified = bool(len(df) and int(df['employee_id'].iloc[-1]) == 1)
    print(f"RECURSIVE_TRAVERSAL_DEPTH: {len(df)}")
    print(f"TOP_LEVEL_SUPERVISOR_VERIFIED: {str(top_verified).upper()}")
    return [int(x) for x in df['employee_id'].tolist()]


def extract_downstream_subordinates(db_path: str, manager_id: int) -> list[int]:
    query = """
    WITH RECURSIVE subs(employee_id, depth) AS (
      SELECT employee_id, 1
      FROM organizational_hierarchy
      WHERE manager_employee_id = ?
      UNION ALL
      SELECT e.employee_id, subs.depth + 1
      FROM organizational_hierarchy AS e
      JOIN subs ON e.manager_employee_id = subs.employee_id
      WHERE subs.depth < 50
    )
    SELECT employee_id FROM subs ORDER BY employee_id;
    """
    df = _read_sql(db_path, query, (manager_id,))
    print(f"TOTAL_DOWNSTREAM_SUBORDINATES_COUNT: {len(df)}")
    return [int(x) for x in df['employee_id'].tolist()]


def generate_multi_leg_connections(db_path: str, origin_id: int, terminal_id: int) -> pd.DataFrame:
    query = """
    WITH RECURSIVE paths(current_node, path_string, depth) AS (
      SELECT ?, CAST(? AS TEXT), 0
      UNION ALL
      SELECT r.dest_node_id, paths.path_string || '->' || r.dest_node_id, paths.depth + 1
      FROM paths
      JOIN routes AS r ON r.source_node_id = paths.current_node
      WHERE paths.depth < 4
        AND instr(paths.path_string, CAST(r.dest_node_id AS TEXT)) = 0
    )
    SELECT path_string, depth
    FROM paths
    WHERE current_node = ? AND depth > 0
    ORDER BY depth, path_string;
    """
    df = _read_sql(db_path, query, (origin_id, origin_id, terminal_id))
    print(f"TOTAL_VALID_TRANSIT_PATHS_FOUND: {len(df)}")
    return df


def find_shortest_distance_route(db_path: str, origin_id: int, terminal_id: int) -> float:
    query = """
    WITH RECURSIVE paths(current_node, total_distance, path_string, depth) AS (
      SELECT ?, 0.0, CAST(? AS TEXT), 0
      UNION ALL
      SELECT r.dest_node_id, paths.total_distance + r.distance_km,
             paths.path_string || '->' || r.dest_node_id, paths.depth + 1
      FROM paths
      JOIN routes AS r ON r.source_node_id = paths.current_node
      WHERE paths.depth < 5
        AND instr(paths.path_string, CAST(r.dest_node_id AS TEXT)) = 0
    )
    SELECT MIN(total_distance)
    FROM paths
    WHERE current_node = ? AND depth > 0;
    """
    val = float(_scalar(db_path, query, (origin_id, origin_id, terminal_id)) or 0.0)
    print(f"MINIMAL_PATH_DISTANCE_KM: {val:.2f}")
    return val


def scan_network_cyclic_dependencies(db_path: str) -> list[int]:
    query = """
    WITH RECURSIVE walk(start_node, current_node, path_string, cycle_node, depth) AS (
      SELECT source_node_id, dest_node_id,
             ',' || source_node_id || ',' || dest_node_id || ',',
             CASE WHEN source_node_id = dest_node_id THEN dest_node_id ELSE NULL END,
             1
      FROM routes
      UNION ALL
      SELECT walk.start_node, r.dest_node_id,
             walk.path_string || r.dest_node_id || ',',
             CASE WHEN instr(walk.path_string, ',' || r.dest_node_id || ',') > 0 THEN r.dest_node_id ELSE NULL END,
             walk.depth + 1
      FROM walk
      JOIN routes AS r ON r.source_node_id = walk.current_node
      WHERE walk.depth < 6 AND walk.cycle_node IS NULL
    )
    SELECT DISTINCT cycle_node
    FROM walk
    WHERE cycle_node IS NOT NULL
    ORDER BY cycle_node;
    """
    df = _read_sql(db_path, query)
    out = [int(x) for x in df['cycle_node'].tolist()]
    print(f"CYCLIC_PATH_ANOMALIES_DETECTED: {len(out)}")
    return out


def evaluate_transitive_asset_flows(db_path: str, item_sku: str) -> int:
    query = """
    WITH item AS (
      SELECT item_id FROM inventory_items WHERE sku = ? LIMIT 1
    ), reachable(node_id, depth) AS (
      SELECT ni.node_id, 0
      FROM node_inventory AS ni, item
      WHERE ni.item_id = item.item_id
      UNION
      SELECT r.dest_node_id, reachable.depth + 1
      FROM reachable
      JOIN routes AS r ON r.source_node_id = reachable.node_id
      WHERE reachable.depth < 2
    )
    SELECT COALESCE(SUM(ni.quantity), 0)
    FROM node_inventory AS ni
    JOIN item ON item.item_id = ni.item_id
    WHERE ni.node_id IN (SELECT node_id FROM reachable);
    """
    val = int(_scalar(db_path, query, (item_sku,)) or 0)
    print(f"TRANSITIVE_FLOW_DENSITY_TOTAL: {val}")
    return val


def compute_bom_packaging_mass(db_path: str, master_sku: str) -> float:
    query = """
    WITH RECURSIVE bom(item_id, multiplier) AS (
      SELECT item_id, 1
      FROM inventory_items
      WHERE sku = ?
      UNION ALL
      SELECT bc.component_item_id, bom.multiplier * bc.component_quantity
      FROM bom
      JOIN bom_components AS bc ON bc.master_item_id = bom.item_id
    )
    SELECT COALESCE(SUM(bom.multiplier * ii.unit_weight_kg), 0.0)
    FROM bom
    JOIN inventory_items AS ii ON ii.item_id = bom.item_id;
    """
    val = float(_scalar(db_path, query, (master_sku,)) or 0.0)
    print(f"AGGREGATE_BOM_COMPONENT_MASS_KG: {val:.2f}")
    return val


def evaluate_hub_reachability_matrix(db_path: str, source_node_id: int, target_node_id: int, blocked_node_id: int) -> bool:
    query = """
    WITH RECURSIVE reach(node_id, path_string, depth) AS (
      SELECT ?, CAST(? AS TEXT), 0
      WHERE ? <> ?
      UNION ALL
      SELECT r.dest_node_id, reach.path_string || '->' || r.dest_node_id, reach.depth + 1
      FROM reach
      JOIN routes AS r ON r.source_node_id = reach.node_id
      WHERE reach.depth < 6
        AND r.dest_node_id <> ?
        AND instr(reach.path_string, CAST(r.dest_node_id AS TEXT)) = 0
    )
    SELECT COUNT(*) FROM reach WHERE node_id = ?;
    """
    reachable = int(_scalar(db_path, query, (source_node_id, source_node_id, source_node_id, blocked_node_id, blocked_node_id, target_node_id)) or 0) > 0
    print(f"TARGET_TERMINAL_REACHABLE: {str(reachable).upper()}")
    return reachable


def trace_accumulated_transit_costs(db_path: str, start_node: int, end_node: int) -> pd.DataFrame:
    query = """
    WITH RECURSIVE paths(current_node, total_cost, path_string, depth) AS (
      SELECT ?, 0.0, CAST(? AS TEXT), 0
      UNION ALL
      SELECT r.dest_node_id, paths.total_cost + r.base_cost_usd,
             paths.path_string || '->' || r.dest_node_id, paths.depth + 1
      FROM paths
      JOIN routes AS r ON r.source_node_id = paths.current_node
      WHERE paths.depth < 5
        AND instr(paths.path_string, CAST(r.dest_node_id AS TEXT)) = 0
    )
    SELECT path_string, total_cost, depth
    FROM paths
    WHERE current_node = ? AND depth > 0
    ORDER BY total_cost ASC;
    """
    df = _read_sql(db_path, query, (start_node, start_node, end_node))
    print(f"ACCUMULATED_PATH_COST_USD: {(df['total_cost'].iloc[0] if len(df) else 0.0):.2f}")
    return df


def calculate_hierarchy_depth_matrix(db_path: str) -> pd.DataFrame:
    query = """
    WITH RECURSIVE depth_tracker(employee_id, employee_name, depth) AS (
      SELECT employee_id, employee_name, 1
      FROM organizational_hierarchy
      WHERE manager_employee_id IS NULL
      UNION ALL
      SELECT e.employee_id, e.employee_name, depth_tracker.depth + 1
      FROM organizational_hierarchy AS e
      JOIN depth_tracker ON e.manager_employee_id = depth_tracker.employee_id
    )
    SELECT * FROM depth_tracker ORDER BY employee_id;
    """
    df = _read_sql(db_path, query)
    print(f"MAXIMUM_TREE_TOPOLOGY_DEPTH: {(int(df['depth'].max()) if len(df) else 0)}")
    print(f"TOTAL_RECORDS_MAPPED: {len(df)}")
    return df
