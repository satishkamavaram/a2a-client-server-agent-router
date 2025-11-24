

BEGIN;

-- Speed up large inserts for this session only
SET LOCAL synchronous_commit = OFF;

-- Clear existing data in a single statement to satisfy FK constraints
TRUNCATE TABLE sales, address, customers, users RESTART IDENTITY CASCADE;

-- 1) Users: 10,000 rows
-- Columns: (userid SERIAL), firstname, lastname, emailid, gender
INSERT INTO users (firstname, lastname, emailid, gender)
SELECT
  'First' || i AS firstname,
  'Last' || i AS lastname,
  'user' || i || '@example.com' AS emailid,
  CASE WHEN (i % 2) = 0 THEN 'Male' ELSE 'Female' END AS gender
FROM generate_series(1, 10000) AS s(i);

-- 2) Address: 10,000 rows (1 per user)
-- Columns: (addressid SERIAL), userid, street, city, state, zip, country
-- State cycles across 50 US states; City cycles across 100 synthetic names; Zip is 5-digit string
INSERT INTO address (userid, street, city, state, zip, country)
SELECT
  i AS userid,
  (i || ' Main St')::text AS street,
  ('City' || ((i % 100) + 1))::text AS city,
  (ARRAY['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY'])[((i % 50) + 1)] AS state,
  lpad(((10000 + (i % 90000)))::text, 5, '0') AS zip,
  'USA' AS country
FROM generate_series(1, 10000) AS s(i);

-- 3) Customers: 5,000 rows
-- Columns: (customerid SERIAL), name, email, phone, address
INSERT INTO customers (name, email, phone, address)
SELECT
  'Customer ' || i AS name,
  'customer' || i || '@example.com' AS email,
  '555-' || to_char(1000 + (i % 9000), 'FM0000') AS phone,
  (i || ' Customer St, City' || ((i % 100) + 1) || ', ST')::text AS address
FROM generate_series(1, 5000) AS s(i);

-- 4) Sales: 20,000 rows
-- Columns: (saleid SERIAL), userid (1..10000), customerid (1..5000), date, amount
-- Random date between 2020-01-01 and 2025-12-31; amount between 10.00 and 500.00
INSERT INTO sales (userid, customerid, date, amount)
SELECT
  (floor(random() * 10000) + 1)::int AS userid,
  (floor(random() * 5000) + 1)::int AS customerid,
  (
    DATE '2020-01-01'
    + (
        random() * (DATE '2025-12-31' - DATE '2020-01-01')
      )::int
  )::date AS date,
  round((random() * 490 + 10)::numeric, 2) AS amount
FROM generate_series(1, 20000);

-- Optional: update planner stats after bulk load
ANALYZE;

COMMIT;

-- Validation (optional): quick counts
-- SELECT 'users' AS table, count(*) FROM users
-- UNION ALL SELECT 'address', count(*) FROM address
-- UNION ALL SELECT 'customers', count(*) FROM customers
-- UNION ALL SELECT 'sales', count(*) FROM sales;
