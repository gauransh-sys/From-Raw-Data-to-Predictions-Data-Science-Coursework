QUERY = """
SELECT
    i.instructor_id,
    i.instructor_name,
    d.department_name
FROM instructors AS i
JOIN departments AS d ON d.department_id = i.department_id
WHERE i.instructor_id IN (
    SELECT c.instructor_id
    FROM courses AS c
    WHERE c.capacity >= 100
    INTERSECT
    SELECT c.instructor_id
    FROM courses AS c
    JOIN enrollments AS e ON e.course_id = c.course_id
    WHERE e.marks >= 90
)
ORDER BY i.instructor_id ASC;
"""
