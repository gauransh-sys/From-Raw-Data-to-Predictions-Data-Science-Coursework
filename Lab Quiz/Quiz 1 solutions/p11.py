QUERY = """
WITH RECURSIVE prereq_chain(start_course_id, current_course_id, depth) AS (
    -- Anchor: every course starts from itself at depth 0
    SELECT course_id, course_id, 0
    FROM courses
    UNION ALL
    -- Recursive: follow prerequisite_course_id
    SELECT pc.start_course_id, c.prerequisite_course_id, pc.depth + 1
    FROM prereq_chain AS pc
    JOIN courses AS c ON c.course_id = pc.current_course_id
    WHERE c.prerequisite_course_id IS NOT NULL
      AND pc.depth < 50
),
max_depth AS (
    SELECT start_course_id, MAX(depth) AS maximum_prerequisite_depth
    FROM prereq_chain
    GROUP BY start_course_id
),
deepest AS (
    -- Pick the row at max depth (depth > 0 means an actual prerequisite exists)
    SELECT pc.start_course_id, pc.current_course_id
    FROM prereq_chain AS pc
    JOIN max_depth AS md
      ON md.start_course_id = pc.start_course_id
     AND md.maximum_prerequisite_depth = pc.depth
    WHERE pc.depth > 0
)
SELECT
    c.course_id,
    c.course_code,
    c.course_name,
    md.maximum_prerequisite_depth,
    c2.course_code AS deepest_prerequisite_course_code
FROM courses AS c
JOIN max_depth AS md ON md.start_course_id = c.course_id
LEFT JOIN deepest AS d ON d.start_course_id = c.course_id
LEFT JOIN courses AS c2 ON c2.course_id = d.current_course_id
ORDER BY md.maximum_prerequisite_depth DESC, c.course_id ASC;
"""
