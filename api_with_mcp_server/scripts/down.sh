#!/bin/bash

docker compose down

rm -rf docker_fastapi/src
rm -rf docker_mcp/src
rm docker_fastapi/requirements.txt
rm docker_mcp/requirements.txt
