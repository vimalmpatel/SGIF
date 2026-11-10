FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv/sgif
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
COPY application ./application

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "application.api:app", "--host", "0.0.0.0", "--port", "8000"]