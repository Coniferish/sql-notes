## JOINs

These examples use a simplified version of the bookshelf schema from the [README](./README.md): `users`, `books`, and the `user_books` junction table. Sample data:

| users     | user_books (user_id, book_id, status) |
| --------- | ------------------------------------- |
| 1 · Maya  | 1, 1 · finished                       |
| 2 · Omar  | 1, 2 · started                        |
| 3 · Priya | 2, 1 · want to read                   |

Priya hasn't saved any books, so she's the row to watch in every example below.

#### Which table is "left"?

"Left" and "right" refer to where a table sits in the query. It is **not** the table named after `LEFT JOIN`.

- **Left** = the table in `FROM` (written first)
- **Right** = the table after `JOIN`

So `FROM users LEFT JOIN user_books` favors `users`, even though the words read "left join user_books."

#### INNER JOIN vs. LEFT JOIN

- `JOIN` (same as `INNER JOIN`) keeps only rows that have a match on **both** sides.
- `LEFT JOIN` keeps **every row from the left table**. When a left row has no match, the right table's columns come back as `NULL`.

```sql
SELECT u.name, ub.status
FROM users u
LEFT JOIN user_books ub ON u.id = ub.user_id;
```

| `users JOIN user_books` | `users LEFT JOIN user_books` | `user_books LEFT JOIN users` |
| ----------------------- | ---------------------------- | ---------------------------- |
| Maya · finished         | Maya · finished              | Maya · finished              |
| Maya · started          | Maya · started               | Maya · started               |
| Omar · want to read     | Omar · want to read          | Omar · want to read          |
|                         | **Priya · NULL**             |                              |

- The middle column is the only one with Priya, because `users` is on the left and every user survives.
- Flipping the order (right column) drops her again. Here it gives exactly the INNER result: the foreign key guarantees every `user_books` row points to a real user, so there's never a left row without a match.
- `RIGHT JOIN` is the mirror image (keep every row of the right table). It's rarely used in practice, because people just swap the table order and write a `LEFT JOIN`. `FULL OUTER JOIN` keeps unmatched rows from both sides.

#### Trap: filtering the right table in `WHERE`

A `WHERE` condition on a right-table column quietly turns a `LEFT JOIN` back into an `INNER JOIN`. The `NULL` rows that the `LEFT JOIN` kept fail the condition (`NULL = 'finished'` isn't true), so they get filtered out.

```sql
-- "Every user, with their finished books if any"? No: returns only Maya.
SELECT u.name, ub.status
FROM users u
LEFT JOIN user_books ub ON u.id = ub.user_id
WHERE ub.status = 'finished';

-- Put the right-table filter in ON instead: Maya · finished, Omar · NULL, Priya · NULL.
SELECT u.name, ub.status
FROM users u
LEFT JOIN user_books ub ON u.id = ub.user_id AND ub.status = 'finished';
```

Rule of thumb: conditions on the **left** table go in `WHERE`, and conditions on the **right** table go in `ON`.

#### Pattern: find rows with no match ("anti-join")

`LEFT JOIN`, then keep only the rows where the right side came back `NULL`. This lists users who haven't saved any books:

```sql
SELECT u.name
FROM users u
LEFT JOIN user_books ub ON u.id = ub.user_id
WHERE ub.user_id IS NULL;   -- returns Priya
```

Here `WHERE` on a right-table column is the point, not a bug: it keeps exactly the rows the `LEFT JOIN` padded with `NULL`. Test a column that can't be `NULL` in a real match (a key column like `ub.user_id`) so a genuine `NULL` value can't be mistaken for "no match."
