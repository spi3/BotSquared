FROM python:3.11

ENV CONFIG_FILE="/data/config.yaml"

COPY ./src/bot_squared /app

WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "b2.py", "--config", "/data/config.yaml"]