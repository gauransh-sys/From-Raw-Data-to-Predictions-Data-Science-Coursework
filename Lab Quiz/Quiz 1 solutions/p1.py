QUERY = """
SELECT
    instructor_id,
    instructor_name,
    salary_usd,
    CASE
        WHEN salary_usd >= 150000 THEN 'High'
        WHEN salary_usd >= 120000 THEN 'Medium'
        WHEN salary_usd >= 90000 THEN 'Average'
        ELSE 'Low'
    END AS salary_category
FROM instructors
ORDER BY
    salary_usd DESC,
    instructor_id ASC
"""