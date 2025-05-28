## Indexes ([reference video](https://www.youtube.com/watch?v=HubezKbFL7E))

#### What's an Index?

A phone book is an index. Instead of a collection of names and addresses organized simply by who
moved to a place first (i.e. a table that auto-increments an `id` attribute as people are added),
the phone book is ordered alphabetically. Instead of scanning every entry to find "Smith," you can
jump directly to the "S" section because the data is pre-sorted.

#### TLDR;

Indexes are database structures that improve query performance by creating ordered representations
of data.

_However_, they come with storage/time tradeoffs. They increase your storage costs because you're
basically creating a new table (duplicating existing data). This also also makes data changes (writing
and deleting) slower because they create more places where data needs to change (and indexes might
need to be rebalanced after an insertion or deletion, but more on that later). ALL THAT SAID, indexes
decrease costs for queries since the queries are _much_ more efficient (i.e. faster, which means
your application operates more smoothly).

#### Key concepts

A significant factor in database cost and speed is the number of **pages** queried.

- Database **tables** are actually a sequence of pages.
- Every table (and index) is stored as an array of pages of a fixed size (usually 8 kB, although a
  different page size can be selected when compiling the server). In a table, all the pages are
  logically equivalent, so a particular item (i.e. row) can be stored in any page. In indexes, the
  first page is generally reserved as a metapage holding control information, and there can be
  different types of pages within the index, depending on the index access method.
  ([source](https://www.postgresql.org/docs/current/storage-page-layout.html))

#### Why do _I_ (a software developer) need to know about indexes?

Indexes should be created in tandem with/for queries (to make them more efficient), and the developer is querying the db, so it's their concern.

- Queries with `WHERE` filters or `JOIN`s on foreign keys benefit most, as indexes reduce table scans.

#### Indexes are B-trees (_balanced_ tree, not binary)

- Left branch is always less than the parent node
- Right branch is always equal to or greater than the parent node
- The leaf nodes are all at the same depth! (this is how you guarantee it takes the same time to search for any value)
- Leaf nodes are also doubly linked (point to the value to the right and left of themselves) so you
  can scan the leaves.
- Because of this tree structure and the requirement that all leaf nodes are at the same depth, the
  index could need to be rebalanced after a change.

An index only contains the values of the columns the index is created on _plus_ the `row_id` (it
doesn't contain the additional columns of the original table it's based on unless you tell it to!)

- The `row_id` is a database attribute that identifies something's place in the database (it is not
  the primary key or anything like that)
- So, a query will use the index to find the correct value very quickly since it's a tree structure,
  but it then goes back to the place where that's stored to find the rest of the data.
- Note: If you create an index for a query, **check the execution plan to make sure it's actually
  used**. If you have a function in your query, the index might not be used. You may need to modify
  your WHERE clause or your SELECT statement, or you may need to modify your index and add
  additional column data to it.

The column order also matters on an index. Indexes are sorted left to right—-each column is ordered
within the context of the ones before it. So only queries that match that order can benefit from the
index.
E.g. AB != BA

#### Execution plan

The execution plan will look different for each sql vendor

```sql
EXPLAIN  -- Add this to any query to also get the execution plan
SELECT *
FROM users
WHERE id = 1;
```

#### Access Types

When you execute an `EXPLAIN` query, it will return a column called `type` that has one of these values explaining what kind of query it performed:

- `const` or `eq_ref`
  - These use a binary search approach to find a single value.
- `ref` or `range`
  - These limit the number of rows we have to look at to a particular subset.
- `index`
  - Scan through every value of the index (relies on the tree being a doubly-linked list).
- `all`
  - Full table scan (not using the index... bad.)

The execution plan also returns a column called `possible_keys` and `key`. These are the possible indexes it considered using and the index it actually used for the query.
