-- Azadexa local PostgreSQL provisioning (native install)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'azadexa') THEN
    CREATE ROLE azadexa LOGIN PASSWORD 'azadexa_dev';
  END IF;
END
$$;
ALTER ROLE azadexa WITH PASSWORD 'azadexa_dev';

SELECT 'CREATE DATABASE azadexa_dev OWNER azadexa'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'azadexa_dev')\gexec

SELECT 'CREATE DATABASE azadexa_test OWNER azadexa'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'azadexa_test')\gexec

GRANT ALL PRIVILEGES ON DATABASE azadexa_dev TO azadexa;
GRANT ALL PRIVILEGES ON DATABASE azadexa_test TO azadexa;
