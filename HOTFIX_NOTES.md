Hotfix applied:
- Fixed ModuleNotFoundError: No module named 'app' during init_db.py
- Added `ENV PYTHONPATH=/app` in backend/Dockerfile
- Added `backend/scripts/__init__.py`

Run:
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d --build
