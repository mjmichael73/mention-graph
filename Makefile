clean:
	@docker compose down --remove-orphans --volumes
	@docker compose up --build -d
ps:
	@docker compose ps
create-migration:
	alembic revision --autogenerate -m "migration"
migrate:
	alembic upgrade head
downgrade:
	alembic downgrade -1