#!/bin/bash

cp requirements.txt docker_fastapi/requirements.txt
cp -r src/ docker_fastapi/src/

cp requirements.txt docker_mcp/requirements.txt
cp -r src/ docker_mcp/src/

docker compose up --build
