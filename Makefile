stream:
	@python -m pricestream.tradovate

build-docker-image:
	@docker build --no-cache --platform=linux/amd64 -t ghcr.io/yasir-khalid/tradovate-price-streaming:latest .

push-docker-image:
	@docker push ghcr.io/yasir-khalid/tradovate-price-streaming:latest