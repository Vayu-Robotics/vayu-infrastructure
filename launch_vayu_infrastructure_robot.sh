#!/bin/bash

docker compose down
docker compose -f docker-compose.robot.yml up -d
