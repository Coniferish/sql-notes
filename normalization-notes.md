##### Normalization ("Normal Forms")

###### 1NF (eliminates repeating groups)

- There must be a primary key for identification
- A single cell must not contain more than one value (atomicity)
- Each column contains values of the same type
- No duplicated rows or columns

###### 2NF (eliminates redundancy)

- 1NF is met
- All non-key attributes are fully dependent on a primary key (This mainly affects tables with composite primary keys and means there is no partial dependency on multiple primary keys. What this means in practice is that data is stored in multiple, appropriate tables).
  ```
  Student_ID | Student_Name |  Course_ID | Course_Name | Grade
  1          | John         | 101        | Math        | A
  1          | John         | 102        | Physics     | B
  2          | Sarah        | 101        | Math        | A+
  ```

###### 3NF (eliminates transitive partial dependency)

- 2NF is met
- No non-key attribute depends on another non-key attribute (no transitive dependencies)
  ```
  Student_ID | Student_Name | Advisor_ID | Advisor_Name
  1          | John         | 201        | Mr. Smith
  2          | Sarah        | 202        | Ms. Jones
  3          | Patty        | 201        | Mr. Smith
  ```
