.PHONY: setup test deploy clean start stop

start:
	docker-compose up -d

stop:
	docker-compose down

setup: start
	@echo "Waiting for LocalStack..."
	sleep 5
	bash setup-aws.sh

test:
	PYTHONPATH=src/layer:. pytest tests/ -v

test-services:
	PYTHONPATH=src/layer:. pytest tests/test_services.py -v

deploy:
	@echo "Packaging Lambda layer..."
	cd src/layer && zip -r ../../layer.zip python/
	@echo "Packaging handlers..."
	cd src/handlers && zip -r ../../handlers.zip *.py
	@echo "Deploy artifacts ready."

clean:
	docker-compose down -v
	rm -f layer.zip handlers.zip
	find . -type d -name __pycache__ -exec rm -rf {} +
