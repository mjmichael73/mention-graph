clean:
	@docker compose down --remove-orphans --volumes
	@docker compose up --build -d
ps:
	@docker compose ps
create-migration:
	@docker compose run --rm app sh -c "alembic revision --autogenerate -m 'migration'"
migrate:
	@docker compose run --rm app sh -c "alembic upgrade head"
downgrade:
	alembic downgrade -1
log-app:
	@docker compose logs -f app
log-db:
	@docker compose logs -f db
log-celery:
	@docker compose logs -f celery
log-redis:
	@docker compose logs -f redis