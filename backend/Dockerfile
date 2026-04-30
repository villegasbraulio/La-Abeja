FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements/base.txt requirements/base.txt
RUN pip install --no-cache-dir -r requirements/base.txt

COPY . .

FROM base AS development

COPY requirements/development.txt requirements/development.txt
RUN pip install --no-cache-dir -r requirements/development.txt

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

FROM base AS production

COPY requirements/production.txt requirements/production.txt
RUN pip install --no-cache-dir -r requirements/production.txt

CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000"]
