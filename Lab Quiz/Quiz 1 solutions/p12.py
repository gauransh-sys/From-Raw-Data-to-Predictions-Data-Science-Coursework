QUERY = """
WITH RECURSIVE subordinates(manager_id, subordinate_id, depth) AS (
    -- Anchor: direct reports of each manager
    SELECT i.manager_id, i.instructor_id, 1
    FROM instructors AS i
    WHERE i.manager_id IS NOT NULL
    UNION ALL
    -- Recursive: find reports of current subordinates
    SELECT s.manager_id, i.instructor_id, s.depth + 1
    FROM subordinates AS s
    JOIN instructors AS i ON i.manager_id = s.subordinate_id
    WHERE s.depth < 50
)
SELECT
    mgr.instructor_id,
    mgr.instructor_name,
    COUNT(*) AS subordinate_count,
    MAX(s.depth) AS maximum_subordinate_depth,
    COUNT(DISTINCT sub.department_id) AS subordinate_department_count
FROM subordinates AS s
JOIN instructors AS mgr ON mgr.instructor_id = s.manager_id
JOIN instructors AS sub ON sub.instructor_id = s.subordinate_id
GROUP BY mgr.instructor_id, mgr.instructor_name
ORDER BY subordinate_count DESC, mgr.instructor_id ASC;
"""
