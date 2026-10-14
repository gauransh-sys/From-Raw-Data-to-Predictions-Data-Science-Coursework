QUERY = """
WITH department_avg AS (
    SELECT
        department_id,
        AVG(cgpa) AS department_average_cgpa
    FROM students
    GROUP BY department_id
),

course_avg AS (
    SELECT
        course_id,
        AVG(marks) AS course_average_marks
    FROM enrollments
    GROUP BY course_id
),

student_stats AS (
    SELECT
        s.student_id,
        s.student_name,
        s.department_id,
        s.cgpa,
        AVG(e.marks) AS student_average_marks,
        da.department_average_cgpa,
        AVG(ca.course_average_marks) AS course_group_average_marks
    FROM students AS s
    JOIN department_avg AS da
        ON s.department_id = da.department_id
    JOIN enrollments AS e
        ON s.student_id = e.student_id
    JOIN course_avg AS ca
        ON e.course_id = ca.course_id
    GROUP BY
        s.student_id,
        s.student_name,
        s.department_id,
        s.cgpa,
        da.department_average_cgpa
)

SELECT
    ss.student_id,
    ss.student_name,
    d.department_name,
    ss.cgpa,
    ss.student_average_marks,
    ss.department_average_cgpa,
    ss.course_group_average_marks
FROM student_stats AS ss
JOIN departments AS d
    ON ss.department_id = d.department_id
WHERE ss.cgpa > ss.department_average_cgpa
  AND ss.student_average_marks > ss.course_group_average_marks
ORDER BY ss.student_id ASC;
"""