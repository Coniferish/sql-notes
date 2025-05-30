This is a repo for notes on SQL and to practice creating SQL schemas.

The first mock-project is a bookshelf app where users can organize books they've read and want to read.

---
### Designing a schema:
1. Identify entities\*
2. List attributes
3. Define relationships
4. Sketch schema
5. Plan sample queries

\* The first step should probably be to define business requirements, but I just used an iterative process.

### Entities

Using [excalidraw](https://excalidraw.com/), I started sketching the entities and attributes
bookshelf app would require.

![][sketch1]

This is very naive and incomplete, but a starting point as this is a made up project and I
arbitrarily knew I wanted "users" to categorize books according to status and to be able to rate
books. It would be better to start with a defined list of requirements, but... I didn't.

---
![][sketch2]

There are a few changes in this step. I realized "Author" should be its own entity
since it would be nice to browse books by author as well. I also merged "Reading Status" and
"Rating" into a new entity, "User's Books", which contains those concepts as attributes, realizing
that the status would be an enum type and rating would be an int range. I also added in "start",
"finish", and "added" dates as attributes for good measure.

---
![][sketch3]

The main change here is starting to add relationships between the tables and creating primary keys.

---
![][sketch4]

In this step I fix a couple of things after thinking more about the relationships.

First, let's talk about the Genres table. The design before this overlooked the fact that books can
belong to multiple genres, which indicates another many-to-many relationship.

You _could_ create a denormalized `book` table with an attribute for `genres` that is an array of
genres, and this would be easier to set up initially and require fewer joins when displaying book
details but it would make viewing all books in a genre inefficient because the database would have to
scan every book record and check if the target genre exists within each array. Also, enums are
checked at runtime and if you wanted to rename an enum, you'd have to migrate the enum type itself
rather than just updating records.

Many-to-many relationships require a junction table so we can maintain best practices around
[normalization][normalization-link] (we're aiming for 3NF). We _could_ keep the `book_genres` junction table and
maintain 3NF by having it reference an enum `genre_type` like this...

```sql
CREATE TYPE genre_type AS ENUM ('fiction', 'non_fiction', 'mystery', 'romance', 'sci_fi');

CREATE TABLE book_genres (
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    genre genre_type NOT NULL,  -- Use the enum value directly
    PRIMARY KEY (book_id, genre)
);
```

but it's unlikely we will know all of the genres at the beginning and if any changes need to be
made, it'd be safer and easier to change a `genres` table than an enum. _If_ `genres` was an enum, that would mean we'd have to change
the db schema and do a migration instead of simply inserting a row in the `genres` table.

Second, and similar to the issue above, I fixed a many-to-many relationship between the `book` and
`author` tables by creating a `book_authors` table (side note: I decided to adopt the convention of
creating junction table names as a combination of the tables it was connecting. This means I'll end
up changing "User's Book Status" to just `user_books` for the table name since the apostrophe can't
be used in the table name if we want to be consistent in naming conventions, which I've come to
prefer.)

---
### Schema

Below we have the full schema declaration containing the following:

| Tables       | Enums          |
| ------------ | -------------- |
| genres       | reading_status |
| books        |                |
| book_genres  |                |
| authors      |                |
| book_authors |                |
| users        |                |
| user_books   |                |

The order these are declared in matters and note that the primary key for the junction tables is a
combination of the `.id`s from the two tables it's connecting (for an example, see the `book_genres`
declaration). This prevents duplicate table entries and makes searching more efficient than if you
were to create a new `id` attribute just for this table.

```sql
CREATE TABLE genres (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

CREATE TABLE books (
    id SERIAL PRIMARY KEY,
    title VARCHAR(100) NOT NULL,
    publication_year INT NOT NULL
);

CREATE TABLE book_genres (
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    genre_id INT NOT NULL REFERENCES genres(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, genre_id)
);

CREATE TABLE authors (
    id SERIAL PRIMARY KEY,
    f_name varchar(50) NOT NULL,
    l_name varchar(50) NOT NULL
);

CREATE TABLE book_authors (
    author_id INT NOT NULL REFERENCES authors(id) ON DELETE CASCADE,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    PRIMARY KEY (book_id, author_id)
);

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name varchar(100),
    email varchar(100) UNIQUE
);

CREATE TYPE reading_status AS ENUM ('want to read', 'started', 'finished', 'paused');  -- I added a new status, "paused" just because.

CREATE TABLE user_books (
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    status reading_status NOT NULL,
    date_started TIMESTAMP,  -- I modified these attributes so they start with 'date' and are a consistent tense.
    date_finished TIMESTAMP,
    date_added TIMESTAMP,
    date_last_modified TIMESTAMP,
    rating INT CHECK ( rating >= 1 AND rating <= 5),
    PRIMARY KEY (user_id, book_id)
);
```

Some additional notes:

- `REFERENCES` is a foreign key constraint. This means, for example, in the `user_books` table
  `user_id` MUST point to a valid `id` from the `users` table.
- `ON DELETE CASCADE` means that if a book is deleted in the parent table that attribute is
  "referencing", any rows that point to that parent are also deleted. This prevents
  "orphaned" entries. For example, in the `user_books` table, the `user_id` attribute references
  `users(id)`, so when a user in the `users` table is deleted, the deletion "cascades" down to
  `user_books` as well and deletes their saved books.

---
### Queries and indexes

This is a sample list of queries I'll probably want. For more notes on indexes beyond what's
discussed below, [click here][indexes-link].

#### Get all books (in alphabetical order)

```sql
SELECT * FROM books
ORDER BY title ASC;
```

This is probably a query that would happen a lot for displaying books, so it makes sense to have an
index for it:

```sql
CREATE INDEX idx_books_title ON books(title);
```

---
#### Get all user books

```sql
SELECT b.*
FROM books b
JOIN user_books ub ON b.id = ub.book_id
WHERE ub.user_id = 1;
```

Because the `user_books` table has a composite primary key of `(user_id, book_id)`, it would
probably not be beneficial to have an index for this query. The db will efficiently filter by `user_id`, and for each matching row
the db performs a lookup in the `books` table using `book_id`. Since that's also the primary key for
that table (`books.id`), this part is also efficient.

---
#### Get all user's books of a particular reading status

```sql
SELECT b.*
FROM books b
JOIN user_books ub ON b.id = ub.book_id
WHERE ub.user_id = 1
  AND ub.status = 'finished';
```

Without an index, `user_books` is scanned for where both `user_id = 1`
and `status = 'finished'` by using the
primary key `user_id` and then filtering on `status = 'finished'` row by row.
With the index, the db can directly locate only rows where `user = 1` AND `status = 'finished'`.
Once the matches are found, the db planner fetches the corresponding `book_id`
values from `user_books`, joins with the `books` table, and returns the book records.

```sql
CREATE INDEX idx_user_books_user_id_status ON user_books(user_id, status);
```

---
#### Get all books by an author

```sql
SELECT b.*
FROM books b
JOIN book_authors ba ON b.id = ba.book_id
JOIN authors a ON a.id = ba.author_id
WHERE a.l_name = 'Tolkien';
```

The `authors` table is organized by `.id`, so having an index already sorted by `l_name` will speed up
author queries...

```sql
CREATE INDEX idx_authors_l_name ON authors(l_name);
```

and once the `author.id` is found, the `book_authors` table is queries. Though this table uses a
composite primary key, `(book_id, author_id)`, it would be beneficial to have an index on it for
`author_id` since it comes second.

```sql
CREATE INDEX idx_book_authors_author ON book_authors(author_id)
```

Finally, the `books` table is queried using the `book.id`, which won't need an index.

---
#### Get all books in a genre

```sql
SELECT b.*
FROM books b
JOIN book_genres bg ON b.id = bg.book_id
JOIN genres g ON g.id = bg.genre_id
WHERE g.name = 'Fantasy';
```

This query joins books to genres through the book_genres junction table. Although it's similar in
structure to the earlier user_books query, the optimization considerations are different and would probably only benefit from one index. The
`genres` table would probably never exceed 1000 or even 100 rows, so adding an index on
`genres(name)` wouldn't add much efficiency. Once the db has the `genre.id`, it could use an index
to more efficiently look up all the books in that genre...

```sql
CREATE INDEX idx_book_genres_genre ON book_genres(genre_id)
```

For each book, it would then look up the book in the `books` table.


<!-- LINK SOURCES -->

[sketch1]: ./images/sketch1.png
[sketch2]: ./images/sketch2.png
[sketch3]: ./images/sketch3.png
[sketch4]: ./images/sketch4.png
[normalization-link]: ./normalization-notes.md
[indexes-link]: ./indexes-notes.md

<!-- END LINK REFERENCES -->
