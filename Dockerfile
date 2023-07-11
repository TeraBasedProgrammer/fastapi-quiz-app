FROM python:3.10.6-alpine

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1 

WORKDIR /code

COPY ["./requirements.txt", "pyproject.toml", "./"]

RUN pip install --no-cache-dir -r requirements.txt

COPY ./app .

COPY ./tests ./tests

EXPOSE 8000

CMD ["uvicorn", "main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]