## Indexes ([reference video](https://www.youtube.com/watch?v=HubezKbFL7E))

#### What is an index?

A phone book is an index. Instead of a collection of names and addresses organized simply by who moved to a place first (i.e. a table that auto-increments an `id` attribute as people are randomly added/move to an area), entries are ordered alphabetically. So, instead of scanning a (seemingly unorganized) list to find "Smith," there's an order and you can jump directly to the "S" section because the data is pre-sorted by last name.

#### TLDR;

Indexes are database structures (trees) that improve query performance by creating ordered representations of data.

_However_, they come with storage/time tradeoffs. They increase your storage costs because you're basically creating a new table (duplicating existing data). This also make data changes (writing and deleting) slower because they create more _places_ where data needs to be updated (_and_ indexes might need to be rebalanced after an entry is added or changed, but more on that later). ALL THAT SAID, indexes decrease costs for queries since the queries are _much_ more efficient (i.e. faster), so your application operates more smoothly.

#### Why do _I_ (a software developer) need to know about indexes?

Indexes should be created in tandem with/for queries (to make them more efficient), and the developer is querying the db, so it's their concern.

Tip: Queries with `WHERE` filters or `JOIN`s on foreign keys benefit most, as indexes reduce table scans.

#### Technical concepts

A significant factor in database cost and speed is the number of **pages** queried:

- Database **tables** are actually a sequence of pages.
- Every table (and index) is stored as an array of pages of a fixed size (usually 8 kB, although a different page size can be selected when compiling the server).
- In a table, all the pages are logically equivalent, so a particular item (i.e. row) can be stored on any page. For indexes, the first page is generally reserved as a metapage holding control information, and there can be different types of pages within the index, depending on the index access method. ([source](https://www.postgresql.org/docs/current/storage-page-layout.html))

Indexes are B-trees (_balanced_ tree, not binary):

- Left branch is always less than the parent node
- Right branch is always equal to or greater than the parent node
- The leaf nodes are all at the same depth!
  - This is how you guarantee it takes the same time to search for any value and why indexes are so efficient!
- Leaf nodes are also doubly linked (point to the value to the right and left of themselves) so the db can scan the leaves, which is still more efficient than a regular scan of a table that's not sorted in a way that helps your query.
- Because of this tree structure and the requirement that all leaf nodes are at the same depth, the index could need to be rebalanced after a change in the data it contains. This costs time/resources, so it is a drawback.

An index only contains the values of the column(s) the index is created on _plus_ the `row_id` (it doesn't contain the additional columns of the original table it's based on unless you tell it to).

- The `row_id` is a database attribute that identifies something's place in the database (it is not the primary key or anything like that).
- So, a query will use the index to find the correct value very quickly since it's a tree structure, but it then goes back to the place where that's stored to find the rest of the data.
- Note: If you create an index for a query, **check the execution plan to make sure it's actually used by your query**. If you have a function in your query, the index might not be used. You may need to modify your `WHERE` clause or `SELECT` statement, or you may need to modify your index and add additional column data to it.
- The column order also matters on an index. Indexes are sorted left to right—-each column is ordered within the context of the ones before it. So only queries that match that order can benefit from the index. E.g. AB != BA

#### Composite (multi-column) indexes

A composite index is one index on more than one column, sorted by the first column, then by the second within each value of the first, and so on. A phone book is really a composite index on `(last_name, first_name)`:

- Finding "Smith" is fast: jump to the S section.
- Finding "Smith, John" is faster still: the Johns are already in order among the Smiths.
- Finding everyone named "John" gets **no help**: Johns are scattered across every last name, so you'd read the whole book.

That last point is the **leftmost-prefix rule**: an index on `(A, B)` helps queries on `A`, or on `A` and `B`, but not on `B` alone. (This is the "AB != BA" point above.)

Rule of thumb for column order: put the column you filter with `=` first, then the column you sort or range on (`ORDER BY`, `>`, `BETWEEN`).

Examples already in these notes:

- `idx_user_books_user_id_status ON user_books(user_id, status)` in the [README](./README.md) is a composite index: it jumps to one user, and their rows are already grouped by status.
- The composite primary key `(book_id, author_id)` on `book_authors` doesn't help lookups by `author_id` because it's second, which is why the README adds a separate index on `author_id`.

##### Example: "the 10 most recent transactions for an account"

```sql
SELECT * FROM transactions
WHERE account_id = 42
ORDER BY posted_at DESC
LIMIT 10;
```

SQLite's `EXPLAIN QUERY PLAN` for this query, as the indexes change:

| Index                     | Plan                                                                   | What it means                                                                                    |
| ------------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------ |
| none                      | `SCAN transactions` + `USE TEMP B-TREE FOR ORDER BY`                   | Read every row in the table, then sort the matches                                               |
| `(account_id)`            | `SEARCH … USING INDEX (account_id=?)` + `USE TEMP B-TREE FOR ORDER BY` | Jump to the account, but still sort all of its rows                                              |
| `(account_id, posted_at)` | `SEARCH … USING INDEX (account_id=?)`                                  | Jump to the account; rows are already in date order, so read the newest 10 off the end. No sort. |

And with only the composite index, a query on `posted_at` alone (`WHERE posted_at > '2026-10-01'`) falls back to `SCAN transactions`: the leftmost-prefix rule in action.

Why it matters: without the composite index, this query gets slower every day as the table grows. With it, the work stays about the same no matter how many transactions exist.

#### Execution plan

The execution plan will look different for each sql vendor

```sql
EXPLAIN  -- Add this to any query to also get the execution plan in postgresql
SELECT *
FROM users
WHERE id = 1;
```

Access Types:

When you execute an `EXPLAIN` query, it will return a column called `type` that has one of these values explaining what kind of query it performed:

- `const` or `eq_ref`
  - These use a binary search approach to find a single value.
- `ref` or `range`
  - These limit the number of rows we have to look at to a particular subset.
- `index`
  - Scan through every value of the index (relies on the tree being a doubly-linked list).
- `all`
  - Full table scan (not using the index... bad.)

The execution plan also returns columns called `possible_keys` and `key`. These are the possible indexes it considered using and the index it actually used for the query.
