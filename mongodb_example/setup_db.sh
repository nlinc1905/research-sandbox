#!/bin/bash

export ENVIRONMENT=dev

# Run MongoDB container
docker run --name work-mongo -d \
  -e MONGO_INITDB_ROOT_USERNAME=username \
  -e MONGO_INITDB_ROOT_PASSWORD=password \
  -p 27017:27017 \
  -v mongo_data:/data/db \
  mongo:latest

# Wait for MongoDB to start
echo "Waiting for MongoDB to start..."
until [ "`docker inspect -f {{.State.Running}} work-mongo`"=="true" ]; do
    sleep 1;
sleep 2;
done;

# Run schema.py
python schema.py
pytest test.py  # Will fail when ENVIRONMENT is not set to dev

# Remove the container
docker stop work-mongo
docker rm work-mongo

# Remove the volume
docker volume rm mongo_data
