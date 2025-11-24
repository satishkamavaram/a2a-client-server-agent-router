-- Create admin user if it doesn't exist
DO $$
BEGIN
   IF NOT EXISTS (
      SELECT FROM pg_catalog.pg_roles
      WHERE  rolname = 'admin') THEN
      CREATE ROLE admin LOGIN PASSWORD 'admin';
   END IF;
END
$$;

-- Grant privileges
ALTER USER admin CREATEDB;
GRANT ALL PRIVILEGES ON DATABASE ai TO admin;
ALTER USER admin SUPERUSER;

-- Verify user creation
\du