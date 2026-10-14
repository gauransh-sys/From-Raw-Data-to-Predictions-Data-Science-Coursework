QUERY = """
WITH ranked_instructors AS (
    SELECT
        i.instructor_id,
        i.instructor_name,
        d.department_name,
        i.salary_usd,
        RANK() OVER (
            PARTITION BY i.department_id
            ORDER BY i.salary_usd DESC
        ) AS salary_rank
    FROM instructors AS i
    JOIN departments AS d
        ON i.department_id = d.department_id
)
SELECT
    instructor_id,
    instructor_name,
    department_name,
    salary_usd,
    salary_rank
FROM ranked_instructors
WHERE salary_rank <= 3
ORDER BY
    department_name ASC,
    salary_rank ASC,
    instructor_id ASC
"""