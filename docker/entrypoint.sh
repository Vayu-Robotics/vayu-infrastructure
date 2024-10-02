#!/bin/bash

# Start PostgreSQL
service postgresql start

# Wait for PostgreSQL to be ready
until pg_isready -h localhost; do
  echo "Waiting for PostgreSQL to start..."
  sleep 2
done

# Start Airflow standalone
exec airflow standalone
