-- Initialize test database and PostGIS extension
CREATE DATABASE workforce_test_test;
\c workforce_test_test;
CREATE EXTENSION IF NOT EXISTS postgis;

\c workforce_test;
CREATE EXTENSION IF NOT EXISTS postgis;
