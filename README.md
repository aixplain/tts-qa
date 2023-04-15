
# TTS QA - Quality Assessment Text to Speech Data Annotation Tool

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
docker exec -t your-db-container pg_dumpall -c -U postgres > dump_`date +%d-%m-%Y"_"%H_%M_%S`.sql

cat dump_14-04-2023_19_51_42.sql | docker exec -i postgres_container_dev  psql -U postgres dev_tts_db

```
