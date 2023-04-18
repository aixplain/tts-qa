#!/bin/bash

# Load environment variables from .env file
set -o allexport
source vars.env
set +o allexport

# read a param to start or stop

START_STOP=$1


# print POSTGRES_DB
echo "POSTGRES_DB: ${POSTGRES_DB}"
# Start PostgreSQL container for the specified environment
if [ "$START_STOP" = "start" ]; then
    echo "Starting PostgreSQL container for ${ENV} environment"
    docker-compose -f docker-compose.postgresql.${ENV}.yml up  -d db
elif [ "$START_STOP" = "stop" ]; then
    echo "Stopping PostgreSQL container for ${ENV} environment"
    docker-compose -f docker-compose.postgresql.${ENV}.yml down
else
    echo "Invalid parameter. Use 'start' or 'stop'"
fi
