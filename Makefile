.PHONY: tidy format lint type-check clean

tidy: format lint type-check

type-check:
	uv run mypy src/ --strict

format:
	uv run ruff format src/ tests/

lint:
	uv run ruff check --fix src/

clean:
	rm -rf .venv
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf .pytest_cache

test:
	$(MAKE) -C tests/regressions
