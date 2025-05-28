This is a repo for notes on SQL and to practice creating SQL schemas.

The first mock-project is a bookshelf app where users can catalog books they've read or want to read.

---

### Entities

Using [excalidraw](https://excalidraw.com/), I started sketching the entities and tables this project would require.

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

First, let's talk about the Genre table. The design before this overlooked the fact that books can
belong to multiple genres, which indicates another many-to-many relationship.

You could create a denormalized `book` table with an attribute for `genres` that was an array of
genres and this would be easier to set up initially and require fewer joins when displaying book
details, but would make viewing all books in a genre inefficient because the database would have to
scan every book record and check if the target genre exists within each array. Also, enums are
checked at runtime and if you wanted to rename an enum, you'd have to migrate the enum type itself
rather than just updating records.

Many-to-many relationships require a junction table so we can maintain best practices around
[normalization][normalization-link] (3NF). We _could_ keep the `book_genres` junction table and
maintain 3NF by having it reference an enum `genre_type` like this:

```sql
CREATE TYPE genre_type AS ENUM ('fiction', 'non_fiction', 'mystery', 'romance', 'sci_fi');

CREATE TABLE book_genres (
    book_id INT NOT NULL REFERENCES books(id) ON DELETE CASCADE,
    genre genre_type NOT NULL,  -- Use the enum value directly
    PRIMARY KEY (book_id, genre)
);
```

But it's unlikely we will know all of the genres at the beginning and if any changes need to be
made, it'd be safer and easier to change a `genres` table than an enum. Again, there could be
new genres that get added over time and if `genres` was an enum, that would mean we'd have to change
the db schema and do a migration instead of simply inserting a row in the `genres` table.

Second, and similar to the issue above, I fixed a many-to-many relationship between the `book` and
`author` tables by creating a `book_authors` table (side note: I decided to adopt the convention of
creating junction table names as a combination of the tables it was connecting. This means I'll end
up changing "User's Book Status" to just `user_books` for the table name since the apostrophe can't
be used in the table name if we want to be consistent in naming conventions, which I've come to prefer.)

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


<!-- LINK SOURCES -->

[sketch1]: ./images/sketch1.png
[sketch2]: ./images/sketch2.png
[sketch3]: ./images/sketch3.png
[sketch4]: ./images/sketch4.png
[normalization-link]: ./normalization-notes.md

<!-- END LINK REFERENCES -->
