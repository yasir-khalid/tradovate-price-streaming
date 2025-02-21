freeze:
	@pip install pipreqs
	@pipreqs sportscanner/ --savepath "requirements.txt" --force --encoding=utf-8


setup: version
	@pip install --no-cache-dir -r requirements.txt
	@playwright install chromium

local-streaming:
	@python -m pricestream.tradovate

docker-build-image:
	@docker build --no-cache --platform=linux/amd64 -t ghcr.io/yasir-khalid/tradovate-price-streaming:latest .

docker-push-image:
	@docker push ghcr.io/yasir-khalid/tradovate-price-streaming:latest

container-streaming:
	@echo "ensure .env file is available in same folder as your docker-compose.yml file"
	@docker compose up -d