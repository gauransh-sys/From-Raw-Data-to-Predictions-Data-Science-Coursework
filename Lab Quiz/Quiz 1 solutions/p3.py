QUERY = """
SELECT
    d.department_id,
    d.department_name,
    COUNT(c.course_id) AS course_count
FROM departments AS d
JOIN instructors AS i
    ON d.department_id = i.department_id
JOIN courses AS c
    ON i.instructor_id = c.instructor_id
WHERE i.salary_usd >= 120000
GROUP BY d.department_id, d.department_name
ORDER BY course_count DESC, d.department_id ASC;
"""