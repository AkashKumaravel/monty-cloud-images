.PHONY: all up down setup clean test deploy

up:
	docker-compose up -d

down:
	docker-compose down -v

wait:
	@echo "Waiting for LocalStack..."
	@sleep 10

setup: up wait
	@echo "🚀 Running full infra setup..."
	bash setup-aws.sh

all: up wait setup
	@echo "🎉 FULL LOCALSTACK ENV READY"

test:
	PYTHONPATH=src/layer:src pytest tests/ -v

deploy:
	@echo "📦 Packaging Lambda..."
	cd src && zip -r ../function.zip . > /dev/null

clean:
	docker-compose down -v
	rm -f function.zip
	find . -type d -name __pycache__ -exec rm -rf {} +
