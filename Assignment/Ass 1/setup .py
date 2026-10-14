"""
COL2010 Module 1: Database Systems setup.
Creates a deterministic SQLite database for SQL-query homework.

Run:
    python setup.py

Output:
    logistics_network.db
"""

from __future__ import annotations

import os
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

DB_FILENAME = "logistics_network.db"
RNG_SEED = 2010


def initialize_database(db_path: str = DB_FILENAME) -> None:
    rng = np.random.default_rng(RNG_SEED)
    path = Path(db_path)
    if path.exists():
        path.unlink()

    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    cur.executescript(
        """
        DROP TABLE IF EXISTS bom_components;
        DROP TABLE IF EXISTS route_edges;
        DROP TABLE IF EXISTS shipment_manifests;
        DROP TABLE IF EXISTS shipments;
        DROP TABLE IF EXISTS node_inventory;
        DROP TABLE IF EXISTS inventory_items;
        DROP TABLE IF EXISTS routes;
        DROP TABLE IF EXISTS organizational_hierarchy;
        DROP TABLE IF EXISTS nodes;

        CREATE TABLE nodes (
            node_id INTEGER PRIMARY KEY,
            node_name TEXT NOT NULL,
            city TEXT NOT NULL,
            region TEXT NOT NULL,
            node_type TEXT NOT NULL CHECK (node_type IN ('Warehouse','Hub','Port','Rail Yard')),
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            capacity_cubic_meters REAL NOT NULL CHECK (capacity_cubic_meters > 0)
        );

        CREATE TABLE routes (
            route_id INTEGER PRIMARY KEY,
            source_node_id INTEGER NOT NULL,
            dest_node_id INTEGER NOT NULL,
            transport_mode TEXT NOT NULL CHECK (transport_mode IN ('Truck','Rail','Air','Ocean')),
            distance_km REAL NOT NULL CHECK (distance_km > 0),
            base_cost_usd REAL NOT NULL CHECK (base_cost_usd > 0),
            seasonal_quarter TEXT NOT NULL CHECK (seasonal_quarter IN ('Q1','Q2','Q3','Q4')),
            route_active INTEGER NOT NULL CHECK (route_active IN (0,1)),
            FOREIGN KEY (source_node_id) REFERENCES nodes(node_id),
            FOREIGN KEY (dest_node_id) REFERENCES nodes(node_id),
            CHECK (source_node_id <> dest_node_id)
        );

        CREATE TABLE inventory_items (
            item_id INTEGER PRIMARY KEY,
            sku TEXT NOT NULL,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_weight_kg REAL NOT NULL CHECK (unit_weight_kg > 0),
            unit_volume_cubic_meters REAL NOT NULL CHECK (unit_volume_cubic_meters > 0),
            hazardous_material_flag INTEGER NOT NULL CHECK (hazardous_material_flag IN (0,1))
        );

        CREATE TABLE node_inventory (
            node_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL CHECK (quantity >= 0),
            last_audit_date TEXT NOT NULL,
            PRIMARY KEY (node_id, item_id),
            FOREIGN KEY (node_id) REFERENCES nodes(node_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES inventory_items(item_id) ON DELETE CASCADE
        );

        CREATE TABLE shipments (
            shipment_id INTEGER PRIMARY KEY,
            route_id INTEGER NOT NULL,
            carrier_name TEXT NOT NULL,
            departure_timestamp TEXT NOT NULL,
            arrival_timestamp TEXT,
            shipment_status TEXT NOT NULL CHECK (shipment_status IN ('Pending','In-Transit','Delivered','Delayed')),
            total_freight_cost_usd REAL NOT NULL CHECK (total_freight_cost_usd >= 0),
            FOREIGN KEY (route_id) REFERENCES routes(route_id)
        );

        CREATE TABLE shipment_manifests (
            shipment_id INTEGER NOT NULL,
            item_id INTEGER NOT NULL,
            manifest_quantity INTEGER NOT NULL CHECK (manifest_quantity > 0),
            PRIMARY KEY (shipment_id, item_id),
            FOREIGN KEY (shipment_id) REFERENCES shipments(shipment_id) ON DELETE CASCADE,
            FOREIGN KEY (item_id) REFERENCES inventory_items(item_id) ON DELETE CASCADE
        );

        CREATE TABLE organizational_hierarchy (
            employee_id INTEGER PRIMARY KEY,
            employee_name TEXT NOT NULL,
            role_title TEXT NOT NULL,
            assigned_node_id INTEGER,
            manager_employee_id INTEGER,
            salary_usd REAL NOT NULL CHECK (salary_usd > 0),
            FOREIGN KEY (assigned_node_id) REFERENCES nodes(node_id) ON DELETE SET NULL,
            FOREIGN KEY (manager_employee_id) REFERENCES organizational_hierarchy(employee_id)
        );

        CREATE TABLE route_edges (
            source_node_id INTEGER NOT NULL,
            dest_node_id INTEGER NOT NULL,
            distance_km REAL NOT NULL,
            cost_usd REAL NOT NULL,
            FOREIGN KEY (source_node_id) REFERENCES nodes(node_id),
            FOREIGN KEY (dest_node_id) REFERENCES nodes(node_id)
        );

        CREATE TABLE bom_components (
            master_item_id INTEGER NOT NULL,
            component_item_id INTEGER NOT NULL,
            component_quantity INTEGER NOT NULL CHECK (component_quantity > 0),
            FOREIGN KEY (master_item_id) REFERENCES inventory_items(item_id),
            FOREIGN KEY (component_item_id) REFERENCES inventory_items(item_id)
        );
        """
    )

    n_nodes = 120
    n_routes = 550
    n_items = 450
    n_shipments = 3500
    n_employees = 620

    node_types = np.array(["Warehouse", "Hub", "Port", "Rail Yard"])
    regions = np.array(["North", "South", "East", "West", "Central"])
    cities = np.array(["Delhi", "Mumbai", "Chennai", "Kolkata", "Bengaluru", "Hyderabad", "Pune", "Ahmedabad"])
    nodes = pd.DataFrame({
        "node_id": np.arange(1, n_nodes + 1),
        "node_name": [f"Logistics_Node_{i:03d}" for i in range(1, n_nodes + 1)],
        "city": rng.choice(cities, n_nodes),
        "region": rng.choice(regions, n_nodes),
        "node_type": rng.choice(node_types, n_nodes, p=[0.45, 0.25, 0.15, 0.15]),
        "latitude": rng.uniform(8.0, 35.0, n_nodes),
        "longitude": rng.uniform(68.0, 98.0, n_nodes),
        "capacity_cubic_meters": rng.uniform(8000.0, 220000.0, n_nodes),
    })
    nodes.to_sql("nodes", conn, if_exists="append", index=False)

    # Ensure network backbone plus random route edges.
    routes = []
    rid = 1
    for src in range(1, n_nodes):
        routes.append((rid, src, src + 1, rng.choice(["Truck", "Rail", "Air", "Ocean"]), float(rng.uniform(50, 1200)), float(rng.uniform(500, 18000)), rng.choice(["Q1","Q2","Q3","Q4"]), 1)); rid += 1
    routes.extend([
        (rid, 10, 25, "Rail", 870.0, 10200.0, "Q2", 1),
        (rid+1, 25, 10, "Truck", 920.0, 11600.0, "Q3", 1),
        (rid+2, 40, 55, "Air", 640.0, 24500.0, "Q4", 1),
        (rid+3, 55, 40, "Rail", 660.0, 9700.0, "Q1", 1),
    ]); rid += 4
    used = {(r[1], r[2]) for r in routes}
    while rid <= n_routes:
        src = int(rng.integers(1, n_nodes + 1)); dst = int(rng.integers(1, n_nodes + 1))
        if src == dst or (src, dst) in used:
            continue
        used.add((src, dst))
        dist = float(rng.uniform(20, 2400))
        mode = rng.choice(["Truck", "Rail", "Air", "Ocean"], p=[0.45, 0.25, 0.15, 0.15])
        cost_multiplier = {"Truck": 9.0, "Rail": 5.0, "Air": 22.0, "Ocean": 3.5}[str(mode)]
        cost = float(dist * cost_multiplier + rng.uniform(50, 2000))
        routes.append((rid, src, dst, str(mode), dist, cost, str(rng.choice(["Q1","Q2","Q3","Q4"])), int(rng.random() > 0.06)))
        rid += 1
    routes_df = pd.DataFrame(routes, columns=["route_id","source_node_id","dest_node_id","transport_mode","distance_km","base_cost_usd","seasonal_quarter","route_active"])
    routes_df.to_sql("routes", conn, if_exists="append", index=False)
    routes_df[["source_node_id","dest_node_id","distance_km","base_cost_usd"]].rename(columns={"base_cost_usd":"cost_usd"}).to_sql("route_edges", conn, if_exists="append", index=False)

    categories = np.array(["Electronics", "Textiles", "Automotive", "Pharma", "Grocery", "Machinery"])
    skus = [f"SKU-{i:05d}-{int(rng.integers(100, 999))}" for i in range(1, n_items + 1)]
    # intentional duplicate structural SKU values for duplicate-query task
    for k in range(5):
        skus[n_items - 1 - k] = skus[k]
    items = pd.DataFrame({
        "item_id": np.arange(1, n_items + 1),
        "sku": skus,
        "product_name": [f"Industrial Component {i:05d}" for i in range(1, n_items + 1)],
        "category": rng.choice(categories, n_items),
        "unit_weight_kg": rng.uniform(0.1, 850.0, n_items),
        "unit_volume_cubic_meters": rng.uniform(0.001, 18.0, n_items),
        "hazardous_material_flag": rng.choice([0, 1], n_items, p=[0.92, 0.08]),
    })
    items.to_sql("inventory_items", conn, if_exists="append", index=False)

    inv_rows = []
    for node_id in range(1, n_nodes + 1):
        subset = rng.choice(np.arange(1, n_items + 1), size=int(rng.integers(18, 55)), replace=False)
        for item_id in subset:
            inv_rows.append((node_id, int(item_id), int(rng.integers(0, 5000)), "2026-06-15"))
    pd.DataFrame(inv_rows, columns=["node_id","item_id","quantity","last_audit_date"]).to_sql("node_inventory", conn, if_exists="append", index=False)

    start = datetime(2024, 1, 1)
    carriers = [f"Global Transit Carrier Line {i}" for i in range(1, 28)]
    ship_rows = []
    for sid in range(1, n_shipments + 1):
        route_id = int(rng.integers(1, n_routes + 1))
        dep = start + timedelta(hours=float(rng.uniform(0, 24 * 365)))
        status = str(rng.choice(["Delivered", "Delayed", "In-Transit", "Pending"], p=[0.82, 0.07, 0.08, 0.03]))
        arr = dep + timedelta(hours=float(rng.uniform(3, 168))) if status == "Delivered" else None
        cost = float(routes_df.loc[routes_df.route_id == route_id, "base_cost_usd"].iloc[0] * rng.uniform(0.85, 1.45))
        ship_rows.append((sid, route_id, str(rng.choice(carriers)), dep.strftime("%Y-%m-%d %H:%M:%S"), arr.strftime("%Y-%m-%d %H:%M:%S") if arr else None, status, cost))
    pd.DataFrame(ship_rows, columns=["shipment_id","route_id","carrier_name","departure_timestamp","arrival_timestamp","shipment_status","total_freight_cost_usd"]).to_sql("shipments", conn, if_exists="append", index=False)

    man_rows = []
    for sid in range(1, n_shipments + 1):
        subset = rng.choice(np.arange(1, n_items + 1), size=int(rng.integers(1, 5)), replace=False)
        for item_id in subset:
            man_rows.append((sid, int(item_id), int(rng.integers(1, 80))))
    pd.DataFrame(man_rows, columns=["shipment_id","item_id","manifest_quantity"]).to_sql("shipment_manifests", conn, if_exists="append", index=False)

    emp_rows = []
    for eid in range(1, n_employees + 1):
        if eid == 1:
            manager = None; role = "Chief Operations Officer"; salary = 310000.0
        elif eid <= 8:
            manager = 1; role = "VP Supply Chain"; salary = float(rng.uniform(210000, 270000))
        elif eid <= 55:
            manager = int(rng.integers(2, 9)); role = "Regional Director"; salary = float(rng.uniform(145000, 220000))
        elif eid <= 180:
            manager = int(rng.integers(9, 56)); role = "Warehouse Manager"; salary = float(rng.uniform(85000, 155000))
        else:
            manager = int(rng.integers(56, 181)); role = "Logistics Analyst"; salary = float(rng.uniform(38000, 90000))
        emp_rows.append((eid, f"Operator_Staff_{eid:04d}", role, int(rng.integers(1, n_nodes + 1)), manager, salary))
    pd.DataFrame(emp_rows, columns=["employee_id","employee_name","role_title","assigned_node_id","manager_employee_id","salary_usd"]).to_sql("organizational_hierarchy", conn, if_exists="append", index=False)

    bom_rows = []
    for master in range(1, 31):
        comps = rng.choice(np.arange(31, n_items + 1), size=3, replace=False)
        for c in comps:
            bom_rows.append((master, int(c), int(rng.integers(1, 6))))
    pd.DataFrame(bom_rows, columns=["master_item_id","component_item_id","component_quantity"]).to_sql("bom_components", conn, if_exists="append", index=False)

    cur.executescript(
        """
        CREATE INDEX idx_routes_source ON routes(source_node_id);
        CREATE INDEX idx_routes_dest ON routes(dest_node_id);
        CREATE INDEX idx_shipments_route ON shipments(route_id);
        CREATE INDEX idx_shipments_status ON shipments(shipment_status);
        CREATE INDEX idx_manifest_item ON shipment_manifests(item_id);
        CREATE INDEX idx_inventory_item ON node_inventory(item_id);
        CREATE INDEX idx_org_manager ON organizational_hierarchy(manager_employee_id);
        CREATE INDEX idx_org_node ON organizational_hierarchy(assigned_node_id);
        """
    )
    conn.commit()
    conn.close()
    print(f"Created {db_path}")
    print(f"Database size: {os.path.getsize(db_path) / (1024 ** 2):.2f} MB")

def generate_task_inputs(db_path: str = DB_FILENAME):
    """
    Generate deterministic parameters for every homework task.
    These are written to hw1_query_inputs.json and consumed by
    load_task_inputs()/run_task().
    """

    rng = np.random.default_rng(RNG_SEED)

    conn = sqlite3.connect(db_path)

    def scalar(query, params=()):
        return conn.execute(query, params).fetchone()[0]

    inputs = {
        "database": {
            "db_path": db_path
        },
        "task_01": {}
    }

    # --------------------------
    # Tasks 2–4
    # --------------------------
    # --------------------------
    # Task 02
    # --------------------------

    capacities = pd.read_sql_query(
        """
        SELECT capacity_cubic_meters
        FROM nodes
        ORDER BY capacity_cubic_meters
        """,
        conn,
    )["capacity_cubic_meters"].to_numpy()

    # Pick two different capacities as bounds
    i = rng.integers(0, len(capacities) - 10)
    j = rng.integers(i + 5, len(capacities))

    min_cap = float(capacities[i])
    max_cap = float(capacities[j])

    inputs["task_02"] = {
        "db_path": db_path,
        "min_cap": round(min_cap, 2),
        "max_cap": round(max_cap, 2),
    }
        
    # --------------------------
    # Task 03
    # --------------------------

    valid_statuses = pd.read_sql_query(
        """
        SELECT DISTINCT shipment_status
        FROM shipments
        WHERE arrival_timestamp IS NOT NULL
        ORDER BY shipment_status
        """,
        conn,
    )["shipment_status"].tolist()

    status_flag = rng.choice(valid_statuses)

    inputs["task_03"] = {
        "db_path": db_path,
        "status_flag": str(status_flag),
    }

    baseline = scalar(
        "SELECT AVG(base_cost_usd) FROM routes"
    )

    #------------------------------------
    # Task 04
    #------------------------------------
    costs = pd.read_sql_query(
        """
        SELECT base_cost_usd
        FROM routes
        ORDER BY base_cost_usd
        """,
        conn,
    )["base_cost_usd"].to_numpy()

    # Choose a random percentile between the 40th and 80th percentile
    percentile = int(rng.integers(40, 81))

    baseline_limit = float(np.percentile(costs, percentile))

    inputs["task_04"] = {
        "db_path": db_path,
        "baseline_limit": round(baseline_limit, 2),
    }

    # --------------------------
    # Task 05
    # --------------------------

    valid_pairs = pd.read_sql_query(
        """
        SELECT ii.sku, ni.node_id
        FROM node_inventory AS ni
        JOIN inventory_items AS ii
            ON ii.item_id = ni.item_id
        """,
        conn,
    )

    selected = valid_pairs.sample(
        n=1,
        random_state=int(rng.integers(0, 2**32 - 1))
    ).iloc[0]

    inputs["task_05"] = {
        "db_path": db_path,
        "sku_id": str(selected["sku"]),
        "node_id": int(selected["node_id"]),
    }

    # --------------------------
    # Task 06
    # --------------------------

    shipment_ids = pd.read_sql_query(
        """
        SELECT DISTINCT shipment_id
        FROM shipment_manifests
        ORDER BY shipment_id
        """,
        conn,
    )["shipment_id"].to_numpy()

    shipment_id = int(rng.choice(shipment_ids))

    inputs["task_06"] = {
        "db_path": db_path,
        "shipment_id": shipment_id,
    }

    # --------------------------
    # Tasks 7–25
    # --------------------------

    inputs["task_07"] = {"db_path": db_path}

    # --------------------------
    # Task 08
    # --------------------------

    sku = pd.read_sql_query(
        """
        SELECT sku
        FROM inventory_items
        ORDER BY item_id
        """,
        conn,
    )["sku"].to_numpy()

    chosen_sku = str(rng.choice(sku))

    prefix = chosen_sku.split("-")[1][:3]

    regex = rf"^SKU-{prefix}\d{{2}}-\d{{3}}$"

    inputs["task_08"] = {
        "db_path": db_path,
        "exact_regex": regex,
    }

    inputs["task_09"] = {"db_path": db_path}

    # --------------------------
    # Task 10
    # --------------------------

    inventory_totals = pd.read_sql_query(
        """
        SELECT SUM(quantity) AS total_inventory
        FROM node_inventory
        GROUP BY node_id
        ORDER BY total_inventory
        """,
        conn,
    )["total_inventory"].to_numpy()

    # Choose a threshold between the 40th and 80th percentile
    percentile = int(rng.integers(40, 81))

    asset_threshold = int(np.percentile(inventory_totals, percentile))

    inputs["task_10"] = {
        "db_path": db_path,
        "asset_threshold": asset_threshold,
    }

        # --------------------------
    # Task 11
    # --------------------------

    node_types = pd.read_sql_query(
        """
        SELECT DISTINCT node_type
        FROM nodes
        ORDER BY node_type
        """,
        conn,
    )["node_type"].tolist()

    # Randomly choose between 1 and all available node types
    num_types = int(rng.integers(1, len(node_types)))

    valid_source_types = rng.choice(
        node_types,
        size=num_types,
        replace=False,
    ).tolist()

    inputs["task_11"] = {
        "db_path": db_path,
        "valid_source_types": valid_source_types,
    }

    # --------------------------
    # Task 12
    # --------------------------

    carrier_run_counts = pd.read_sql_query(
        """
        SELECT COUNT(*) AS run_count
        FROM shipments
        GROUP BY carrier_name
        ORDER BY run_count
        """,
        conn,
    )["run_count"].to_numpy()

    # Choose a threshold between the 30th and 80th percentile
    percentile = int(rng.integers(30, 81))

    minimum_runs = int(np.percentile(carrier_run_counts, percentile))

    # Ensure the threshold is at least 1
    minimum_runs = max(1, minimum_runs)

    inputs["task_12"] = {
        "db_path": db_path,
        "minimum_runs": minimum_runs,
    }


    inputs["task_13"] = {"db_path": db_path}
    inputs["task_14"] = {"db_path": db_path}
    inputs["task_15"] = {"db_path": db_path}

    # --------------------------
    # Task 16
    # --------------------------

    timestamps = pd.read_sql_query(
        """
        SELECT departure_timestamp
        FROM shipments
        ORDER BY departure_timestamp
        """,
        conn,
    )["departure_timestamp"].to_numpy()

    n = len(timestamps)

    # Choose a random time window spanning roughly 20–60% of the timeline
    start_idx = int(rng.integers(0, max(1, n // 2)))
    end_idx = int(rng.integers(start_idx + max(1, n // 5), n))

    start_bound = str(timestamps[start_idx])
    end_bound = str(timestamps[end_idx])

    inputs["task_16"] = {
        "db_path": db_path,
        "start_bound": start_bound,
        "end_bound": end_bound,
    }

    for t in range(17,26):
        inputs[f"task_{t:02d}"] = {
            "db_path": db_path
        }

    # --------------------------
    # Recursive tasks
    # --------------------------

    # --------------------------
    # Task 26
    # --------------------------

    employee_ids = pd.read_sql_query(
        """
        SELECT employee_id
        FROM organizational_hierarchy
        WHERE manager_employee_id IS NOT NULL
        ORDER BY employee_id
        """,
        conn,
    )["employee_id"].to_numpy()

    start_employee_id = int(rng.choice(employee_ids))

    inputs["task_26"] = {
        "db_path": db_path,
        "start_employee_id": start_employee_id,
    }

    # --------------------------
    # Task 27
    # --------------------------

    manager_ids = pd.read_sql_query(
        """
        SELECT DISTINCT manager_employee_id
        FROM organizational_hierarchy
        WHERE manager_employee_id IS NOT NULL
        ORDER BY manager_employee_id
        """,
        conn,
    )["manager_employee_id"].to_numpy()

    manager_id = int(rng.choice(manager_ids))

    inputs["task_27"] = {
        "db_path": db_path,
        "manager_id": manager_id,
    }

        # --------------------------
    # Task 28
    # --------------------------

    node_ids = pd.read_sql_query(
        """
        SELECT node_id
        FROM nodes
        ORDER BY node_id
        """,
        conn,
    )["node_id"].to_numpy()

    # Choose an origin such that there are at least two hops ahead
    origin_idx = int(rng.integers(0, len(node_ids) - 2))

    # Choose a terminal at least two hops away
    terminal_idx = int(rng.integers(origin_idx + 2, len(node_ids)))

    origin_id = int(node_ids[origin_idx])
    terminal_id = int(node_ids[terminal_idx])

    inputs["task_28"] = {
        "db_path": db_path,
        "origin_id": origin_id,
        "terminal_id": terminal_id,
    }

    inputs["task_29"] = {
        "db_path": db_path,
        "origin_id": int(origin_id),
        "terminal_id": int(terminal_id)
    }

    inputs["task_30"] = {
        "db_path": db_path
    }

        # --------------------------
    # Task 31
    # --------------------------

    sku_list = pd.read_sql_query(
        """
        SELECT DISTINCT ii.sku
        FROM inventory_items AS ii
        JOIN node_inventory AS ni
            ON ii.item_id = ni.item_id
        ORDER BY ii.item_id
        """,
        conn,
    )["sku"].to_numpy()

    item_sku = str(rng.choice(sku_list))

    inputs["task_31"] = {
        "db_path": db_path,
        "item_sku": item_sku,
    }

        # --------------------------
    # Task 32
    # --------------------------

    master_skus = pd.read_sql_query(
        """
        SELECT ii.sku
        FROM inventory_items AS ii
        JOIN (
            SELECT DISTINCT master_item_id
            FROM bom_components
        ) AS bom
            ON ii.item_id = bom.master_item_id
        ORDER BY ii.item_id
        """,
        conn,
    )["sku"].to_numpy()

    master_sku = str(rng.choice(master_skus))

    inputs["task_32"] = {
        "db_path": db_path,
        "master_sku": master_sku,
    }

        # --------------------------
    # Task 33
    # --------------------------

    node_ids = pd.read_sql_query(
        """
        SELECT node_id
        FROM nodes
        ORDER BY node_id
        """,
        conn,
    )["node_id"].to_numpy()

    # Source and target are guaranteed to be connected by the backbone.
    source_idx = int(rng.integers(0, len(node_ids) - 2))
    target_idx = int(
        rng.integers(
            source_idx + 2,
            min(source_idx + 7, len(node_ids))
        )
    )

    source_node_id = int(node_ids[source_idx])
    target_node_id = int(node_ids[target_idx])

    # Pick any node except source and target.
    blocked_candidates = node_ids[
        (node_ids != source_node_id) &
        (node_ids != target_node_id)
    ]

    blocked_node_id = int(rng.choice(blocked_candidates))

    inputs["task_33"] = {
        "db_path": db_path,
        "source_node_id": source_node_id,
        "target_node_id": target_node_id,
        "blocked_node_id": blocked_node_id,
    }

        # --------------------------
    # Task 34
    # --------------------------

    node_ids = pd.read_sql_query(
        """
        SELECT node_id
        FROM nodes
        ORDER BY node_id
        """,
        conn,
    )["node_id"].to_numpy()

    # Choose two nodes connected by the backbone
    start_idx = int(rng.integers(0, len(node_ids) - 2))

    end_idx = int(
        rng.integers(
            start_idx + 2,
            min(start_idx + 6, len(node_ids))
        )
    )

    start_node = int(node_ids[start_idx])
    end_node = int(node_ids[end_idx])

    inputs["task_34"] = {
        "db_path": db_path,
        "start_node": start_node,
        "end_node": end_node,
    }

    inputs["task_35"] = {
        "db_path": db_path
    }

    conn.close()

    return inputs


def write_task_inputs(inputs,
                      filename="hw1_query_inputs.json"):
    with open(filename, "w") as f:
        json.dump(inputs, f, indent=2)

if __name__ == "__main__":

    initialize_database(DB_FILENAME)

    inputs = generate_task_inputs(DB_FILENAME)

    write_task_inputs(inputs)

    print("Created hw1_query_inputs.json")
