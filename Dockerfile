FROM python:3.11

ARG VERSION=0.1
ENV CONFIG_FILE="/data/config.yaml"

RUN pip install hatch

RUN mkdir /app
COPY ./dist/bot_squared-${VERSION}.tar.gz /
RUN tar -xvf /bot_squared-${VERSION}.tar.gz -C /app
WORKDIR /app/bot_squared-${VERSION}/src/bot_squared
RUN hatch env create

CMD ["hatch", "run", "python", "b2.py", "--config", "/data/config.yaml"]