#!/bin/bash
cd /data/tts-qa/dumps
docker exec -t postgres_container_dev pg_dump -U postgres  dev_tts_db > /data/tts-qa/dumps/dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql
aws s3 sync /data/tts-qa/dumps/ s3://<bucket-name>/tts-qa-dumps/
echo "done"
