## Quick schema design (for interviews)

In a system design question you get a couple of minutes for the data model, not an afternoon like the bookshelf schema in the [README](./README.md). The trick is to start from the same skeleton every time and then add only what the prompt names.

#### The skeleton

Most "workflow" features (something gets created, moves through states, and someone acts on it) fit this shape:

1. **`id`**: primary key.
2. **Owner FK**: the parent record this row lives under (`account_id`, `application_id`, `ticket_id`). Ask "belongs to what?", and test it: which screen lists these rows? Do they go away when the parent does? Could two people share it? It's often not the user. Transactions belong to an account, because a joint account has two customers. And the owner isn't always the author: a ticket message belongs to its ticket, even though a person wrote it.
3. **Type**: what kind of thing it is (`document_type_id`, `category`). Use a lookup table if the business will add types, or an enum if the list is fixed. This is the same enum-vs-table trade-off as `genres` in the README.
4. **Status, with the states named**: e.g. `pending_review`, `approved`, `rejected`. Saying the states out loud shows you've thought about the workflow.
5. **Timestamps**: `created_at` and `updated_at`. Add **`<actor>_by` / `<actor>_at`** (`reviewed_by`, `reviewed_at`) when a person acts on the record.
6. **Whatever the prompt names explicitly**: an amount, a note, a threshold, a due date.

Then check four things quickly:

- **Many-to-many?** If yes, it needs a junction table (like `book_authors`).
- **Money?** Store it as integer cents or `NUMERIC`, never as a float.
- **Files?** Keep them in object storage (e.g. S3). The table holds the key and metadata, not the file.
- **History matters?** Insert a new row instead of overwriting the old one (for example, a resubmission points to the row it replaces).

Example, a mortgage document upload:

```
documents
  id
  application_id      -- owner FK
  document_type_id    -- type (lookup table: pay stub, tax return, ID...)
  status              -- pending_review | approved | needs_resubmission
  created_at, updated_at
  reviewed_by, reviewed_at
  s3_key, review_note -- what the prompt named
```

---

#### Practice

Set a 2-minute timer for each one. Sketch the main table (or tables) as a column list like the example above, then open the sample answer to compare. The sample isn't the only right answer: if yours covers the skeleton and the prompt's nouns, it's good.

##### 1. Expense reports

> Employees submit expenses with a receipt photo. Their manager approves or rejects each one, and approved expenses get reimbursed in the next payroll.

<details><summary>Sample answer</summary>

```
expenses
  id
  employee_id            -- owner FK
  category               -- travel | meals | supplies (enum, or a lookup table)
  status                 -- submitted | approved | rejected | reimbursed
  amount_cents, currency, spent_on (date), description
  receipt_s3_key         -- file in object storage
  created_at, updated_at
  reviewed_by, reviewed_at, rejection_reason
  reimbursed_at, payroll_run_id
```

The manager comes from the employee record (`employees.manager_id`), so you don't store it on each expense.

</details>

##### 2. Library holds

> Patrons place holds on books. When a copy is returned, the next patron in line is notified and has 3 days to pick it up before the hold expires.

<details><summary>Sample answer</summary>

```
holds
  id
  patron_id              -- owner FK
  book_id                -- FK to the title (not a specific copy)
  status                 -- waiting | ready_for_pickup | picked_up | expired | cancelled
  created_at, updated_at -- created_at doubles as queue order
  ready_at, pickup_deadline
  copy_id                -- set once a specific copy is held for them
```

"Next in line" is a query: the oldest `waiting` hold for that `book_id`. That suggests a composite index on `(book_id, status, created_at)`.

</details>

##### 3. Support tickets

> Customers open support tickets. Agents get assigned, set a priority, and reply in a conversation thread until the ticket is resolved.

<details><summary>Sample answer</summary>

```
tickets
  id
  customer_id            -- owner FK
  category, priority     -- priority: low | normal | high | urgent
  status                 -- open | in_progress | waiting_on_customer | resolved
  subject
  assigned_agent_id
  created_at, updated_at, resolved_at

ticket_messages          -- the "thread" is a second table
  id
  ticket_id              -- owner FK
  author_type, author_id -- customer or agent
  body
  created_at
```

The trap: putting the conversation in a single text column on `tickets`. Anything that repeats gets its own table.

</details>

##### 4. Restaurant reservations

> Guests book a table for a date, time and party size. The restaurant can confirm, the guest can cancel, and staff mark no-shows.

<details><summary>Sample answer</summary>

```
reservations
  id
  guest_id               -- owner FK
  restaurant_id
  party_size
  reserved_for           -- timestamp (date + time)
  status                 -- requested | confirmed | cancelled | seated | no_show
  special_requests
  created_at, updated_at
  confirmed_by, cancelled_at
```

A good clarifying question: are specific tables assigned at booking time? If so, add `table_id`, and double-booking becomes a uniqueness or overlap problem worth mentioning.

</details>

##### 5. Wire transfer approvals (bank)

> Staff create outgoing wire transfers for customers. Any wire over $10,000 needs a second employee to approve it before it's sent.

<details><summary>Sample answer</summary>

```
wire_transfers
  id
  account_id             -- owner FK (the account the money leaves from)
  amount_cents, currency
  beneficiary_name, beneficiary_account, beneficiary_bank_routing
  status                 -- draft | pending_approval | approved | rejected | sent | failed
  created_by, created_at
  approved_by, approved_at   -- CHECK (approved_by <> created_by)
  sent_at, external_reference
  updated_at
```

The interview point: the four-eyes rule (two different people) can be enforced in the database with a `CHECK` constraint, not only in application code. Beneficiary account numbers are sensitive, so mention encryption.

</details>

##### 6. Job application tracker

> Candidates apply to job postings. Each application moves through stages (screen, interview, offer), and interviewers leave a score and notes after each interview.

<details><summary>Sample answer</summary>

```
applications
  id
  candidate_id           -- owner FK
  job_posting_id         -- unique (candidate_id, job_posting_id): one application per job
  stage                  -- applied | screen | interview | offer | hired | rejected
  resume_s3_key
  created_at, updated_at

interview_feedback       -- several interviewers per application
  id
  application_id         -- owner FK
  interviewer_id
  score                  -- e.g. 1–4
  notes
  submitted_at
```

The many-to-many check: candidates and postings are many-to-many, and `applications` is the junction table with its own extra data.

</details>
