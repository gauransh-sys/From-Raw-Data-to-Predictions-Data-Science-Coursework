QUERY = """
WITH department_avg AS (
    SELECT
        department_id,
        AVG(salary_usd) AS department_average_salary
    FROM instructors
    GROUP BY department_id
),

teaching_instructor_avg AS (
    SELECT
        i.department_id,
        AVG(i.salary_usd) AS teaching_instructor_average_salary
    FROM instructors AS i
    WHERE EXISTS (
        SELECT 1
        FROM courses AS c
        WHERE c.instructor_id = i.instructor_id
          AND c.department_id = i.department_id
    )
    GROUP BY i.department_id
)

SELECT
    i.instructor_id,
    i.instructor_name,
    d.department_name,
    i.salary_usd,
    da.department_average_salary,
    tia.teaching_instructor_average_salary
FROM instructors AS i
JOIN departments AS d
    ON i.department_id = d.department_id
JOIN department_avg AS da
    ON i.department_id = da.department_id
JOIN teaching_instructor_avg AS tia
    ON i.department_id = tia.department_id
WHERE i.salary_usd > da.department_average_salary
  AND i.salary_usd > tia.teaching_instructor_average_salary
ORDER BY
    i.salary_usd DESC,
    i.instructor_id ASC;
"""