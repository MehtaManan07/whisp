GET_RECENT_CATEGORIES = """
SELECT c.*
FROM categories c
JOIN (
    SELECT category_id, MAX(created_at) AS last_used
    FROM expenses
    WHERE user_id = :user_id
    GROUP BY category_id
) e ON c.id = e.category_id
ORDER BY e.last_used DESC
LIMIT :limit
"""