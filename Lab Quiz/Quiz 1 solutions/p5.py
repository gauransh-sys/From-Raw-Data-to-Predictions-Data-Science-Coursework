QUERY = """
SELECT
    i.instructor_id,
    i.instructor_name,
    d.department_name,
    COUNT(DISTINCT e.student_id) AS distinct_student_count
FROM instructors AS i
JOIN departments AS d ON d.department_id = i.department_id
JOIN courses AS c ON c.instructor_id = i.instructor_id
JOIN enrollments AS e ON e.course_id = c.course_id
GROUP BY i.instructor_id, i.instructor_name, d.department_name
HAVING COUNT(DISTINCT e.student_id) >= 200
ORDER BY distinct_student_count DESC, i.instructor_id ASC;
"""
