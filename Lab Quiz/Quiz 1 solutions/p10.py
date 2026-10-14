QUERY = """
WITH RECURSIVE chain(start_id, current_id, depth) AS (
    -- Anchor: every instructor starts from themselves
    SELECT instructor_id, instructor_id, 0
    FROM instructors
    UNION ALL
    -- Recursive: follow manager_id upward
    SELECT chain.start_id, i.manager_id, chain.depth + 1
    FROM chain
    JOIN instructors AS i ON i.instructor_id = chain.current_id
    WHERE i.manager_id IS NOT NULL
      AND chain.depth < 50
),
max_depth AS (
    SELECT start_id, MAX(depth) AS maximum_management_depth
    FROM chain
    GROUP BY start_id
),
root_manager AS (
    SELECT DISTINCT c.start_id, c.current_id AS root_id
    FROM chain AS c
    JOIN max_depth AS md
      ON md.start_id = c.start_id AND md.maximum_management_depth = c.depth
)
SELECT
    i.instructor_id,
    i.instructor_name,
    md.maximum_management_depth,
    i2.instructor_name AS highest_level_manager
FROM instructors AS i
JOIN max_depth AS md ON md.start_id = i.instructor_id
JOIN root_manager AS rm ON rm.start_id = i.instructor_id
JOIN instructors AS i2 ON i2.instructor_id = rm.root_id
ORDER BY md.maximum_management_depth DESC, i.instructor_id ASC;
"""
