QUERY = """
SELECT
    i.instructor_id,
    i.instructor_name,
    d.department_name,
    i.salary_usd,
    ROUND(
        (SELECT AVG(i2.salary_usd)
         FROM instructors AS i2
         WHERE i2.department_id = i.department_id),
        2
    ) AS department_avg_salary
FROM instructors AS i
JOIN departments AS d ON d.department_id = i.department_id
WHERE i.salary_usd > (
    SELECT AVG(i2.salary_usd)
    FROM instructors AS i2
    WHERE i2.department_id = i.department_id
)
ORDER BY i.salary_usd DESC, i.instructor_id ASC;
"""
