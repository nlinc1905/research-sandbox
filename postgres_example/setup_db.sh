#!/bin/bash

# sudo apt-get -y install --no-install-recommends libpq-dev
export ENVIRONMENT=dev

# Run PostgreSQL container
docker run --name work-postgres -d \
  -e POSTGRES_USER=XXXXX \
  -e POSTGRES_PASSWORD=XXXXX \
  -e POSTGRES_DB=postgres \
  -p 5432:5432 \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:latest

# Wait for PostgreSQL to start
echo "Waiting for PostgreSQL to start..."
until docker exec work-postgres pg_isready -U postgres; do
  sleep 1
done

# Run schema.py
python schema.py
pytest test.py  # Will fail when ENVIRONMENT is not set to dev

# Remove the container
docker stop work-postgres
docker rm work-postgres

# Remove the volume
docker volume rm postgres_data
