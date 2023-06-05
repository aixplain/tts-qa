
# TTS QA - Quality Assessment Text to Speech Data Annotation Tool


## Start Database
```
bash docker-compose.sh start
```

## Start Celery
```
celery -A src.service.tasks worker --loglevel=info
```
## Start Backend
```
uvicorn src.service.api:app --port 8089 --reload
```



## Start Frontend
### 1. Annotator
```
python -m streamlit run ./src/web_app/annotator/🏠_Intro_annotator.py  --server.maxUploadSize 2048
```

### 2. Admin

```
python -m streamlit run ./src/web_app/admin/🏠_Intro_admin.py  --server.maxUploadSize 2048
```


### How to dupp and restore the database

```bash
docker exec -t postgres_container_prod pg_dump -U postgres  prod_tts_db > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql

cat dump_14-04-2023_19_51_42.sql | docker exec -i postgres_container_prod  psql -U postgres prod_tts_db

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
GROUP BY dataset.language
ORDER BY dataset.language;
```
