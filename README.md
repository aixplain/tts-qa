
# TTS QA - Quality Assessment Text to Speech Data Annotation Tool


## Start Database
```
bash docker-compose.sh start
```

## Start Celery
```
celery -A src.service.tasks worker --loglevel=info --pool=threads
```
## Start Backend
```
uvicorn src.service.api:app --port 8089 --reload
```

## Start Frontend
### 1. Annotator
```
python -m streamlit run --server.port 8501 /home/ubuntu/repos/tts-qa/src/web_app/annotator/🏠_Intro_annotator.py
```

### 2. Admin

```
python -m streamlit run --server.port 8502  --server.maxUploadSize 8192 /home/ubuntu/repos/tts-qa/src/web_app/admin/🏠_Intro_admin.py
```


### How to dupp and restore the database

```bash
docker exec -t postgres_container_dev pg_dump -U postgres  dev_tts_db > dump_`date +%Y-%m-%d"_"%H_%M_%S`.sql

cat dump_2023-08-08_10_16_24.sql | docker exec -i postgres_container_dev  psql -U postgres dev_tts_db

```


## Get Duration script

```bash
CREATE FUNCTION ROUND(float,int) RETURNS NUMERIC AS $f$
  SELECT ROUND( CAST($1 AS numeric), $2 )
$f$ language SQL IMMUTABLE;
```

```bash
SELECT dataset.name as dataset_name, ROUND(SUM(sample.trimmed_audio_duration) / 60, 2)   AS minutes, ROUND(SUM(sample.trimmed_audio_duration) / 3600, 2)   AS hours
FROM sample
JOIN dataset ON sample.dataset_id = dataset.id
WHERE dataset.name NOT LIKE '%English%' AND dataset.name NOT LIKE '%German%'
GROUP BY dataset.name
ORDER BY dataset.name;
```

Sum of the duration of all the samples in a dataset

```bash
SELECT SUM(sample.trimmed_audio_duration) / 60 / 60 as duration_after_trimming
FROM sample
JOIN dataset ON sample.dataset_id = dataset.id
WHERE dataset.name LIKE '%' || 'English' || '%';
```

Sum of the duration of all the samples for each dataset.language

```bash
SELECT dataset.language as dataset_name, ROUND(SUM(sample.trimmed_audio_duration) / 60, 2)   AS minutes, ROUND(SUM(sample.trimmed_audio_duration) / 3600, 2)   AS hours
FROM sample
JOIN dataset ON sample.dataset_id = dataset.id
WHERE dataset.name NOT LIKE '%English (A%'
GROUP BY dataset.language
ORDER BY dataset.language;
```
