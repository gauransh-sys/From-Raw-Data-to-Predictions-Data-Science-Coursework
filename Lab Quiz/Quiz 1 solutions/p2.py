QUERY = """
SELECT
    i.instructor_id,
    i.instructor_name,
    d.department_name,
    i.salary_usd
FROM instructors AS i
JOIN departments AS d
    ON i.department_id = d.department_id
WHERE d.department_name IN (
    'Computer Science and Engineering',
    'Electrical Engineering',
    'Mechanical Engineering'
)
AND i.salary_usd >= 120000
ORDER BY d.department_name ASC, i.instructor_id ASC;
"""