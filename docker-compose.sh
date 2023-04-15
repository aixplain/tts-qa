#!/bin/bash

# Load environment variables from .env file
set -o allexport
source vars.env
set +o allexport


# print POSTGRES_DB
echo "POSTGRES_DB: ${POSTGRES_DB}"
# Start PostgreSQL container for the specified environment
docker-compose -f docker-compose.postgresql.${ENV}.yml up --remove-orphans -d db
