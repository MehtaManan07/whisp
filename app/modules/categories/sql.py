GET_RECENT_CATEGORIES = """
SELECT c.*
FROM categories c
JOIN (
    SELECT category_id, MAX(created_at) AS last_used
    FROM expenses
    WHERE user_id = :user_id AND deleted_at IS NULL
    GROUP BY category_id
) recent_expenses ON c.id = recent_expenses.category_id
WHERE c.deleted_at IS NULL
ORDER BY recent_expenses.last_used DESC
LIMIT :limit
"""

GET_CATEGORY_TREE = """
WITH RECURSIVE category_tree AS (
    -- Base case: top-level categories (parent_id is NULL)
    SELECT id, name, description, parent_id, name as full_path, 0 as level
    FROM categories
    WHERE parent_id IS NULL
    
    UNION ALL
    
    -- Recursive case: subcategories
    SELECT c.id, c.name, c.description, c.parent_id, 
           ct.full_path || ' > ' || c.name as full_path, ct.level + 1
    FROM categories c
    JOIN category_tree ct ON c.parent_id = ct.id
)
SELECT * FROM category_tree ORDER BY level, name;
"""

GET_CATEGORIES_WITH_USAGE_COUNT = """
SELECT 
    c.id,
    c.name,
    c.description,
    c.parent_id,
    p.name as parent_name,
    COUNT(e.id) as usage_count
FROM categories c
LEFT JOIN categories p ON c.parent_id = p.id
LEFT JOIN expenses e ON c.id = e.category_id AND e.user_id = :user_id AND e.deleted_at IS NULL
GROUP BY c.id, c.name, c.description, c.parent_id, p.name
ORDER BY usage_count DESC, c.name;
"""
