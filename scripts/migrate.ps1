# PowerShell helper to create DB and run migrations inside the web container

docker compose exec web python src/manage.py migrate
