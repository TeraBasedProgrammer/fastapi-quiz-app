FROM python:3.10.6-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1 

WORKDIR /code

COPY ["./requirements.txt", "./pyproject.toml", "./alembic.ini",  "./"]

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app ./app

COPY ./tests ./tests

COPY ./migrations ./migrations 

EXPOSE 8000