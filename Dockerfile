FROM python:3.10-slim

WORKDIR /app
COPY main.py /app
COPY requirements/ /app/requirements/

RUN pip install -r requirements/base.txt

CMD ["python", "/app/main.py"]
