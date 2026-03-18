CREATE SCHEMA IF NOT EXISTS tasks;

-- Read-only user for analytics-service (SELECT only, never writes)
CREATE USER analytics_ro WITH PASSWORD 'analytics_ro';
GRANT CONNECT ON DATABASE geofoncier_tasks TO analytics_ro;
GRANT USAGE ON SCHEMA tasks TO analytics_ro;

-- Automatically grant SELECT on every table/sequence created by geofoncier
-- in this schema (covers Alembic migrations without a post-migration step).
ALTER DEFAULT PRIVILEGES FOR ROLE geofoncier IN SCHEMA tasks
    GRANT SELECT ON TABLES TO analytics_ro;
ALTER DEFAULT PRIVILEGES FOR ROLE geofoncier IN SCHEMA tasks
    GRANT SELECT ON SEQUENCES TO analytics_ro;
