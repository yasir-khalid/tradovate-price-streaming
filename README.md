### Tradovate price streamer
Scraps instrument tick-data from Tradovate and then publishes as messages to Redis pub/sub so multiple consumers don't have to spin up their own versions of scrapers and can connect to a central stream

<img width="1054" alt="image" src="https://github.com/user-attachments/assets/85cc1a17-bb95-4bf5-8838-7c9292decbcb" />

Make sure you have installed **Playwright** and other dependencies listed in `Makefile` or `requirements.txt`
```bash
make setup
```

You can launch the streamer using a docker compose file part of the repo using:
```bash
docker compose up
```

**Important:** Make sure you have a .env file in the folder where repo is cloned with the following variables (should be self-explanatory):
- TRADOVATE_USERNAME
- TRADOVATE_PASSWORD
- REDIS_HOST
- REDIS_PORT
- REDIS_PASSWORD

You can additionally configure logging levels using env. variable: `LOGGING_LEVEL` (default: `DEBUG`)
