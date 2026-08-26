FROM python:3.12-slim

WORKDIR /app
ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

ARG INSTALL_RESEARCH=false
COPY backend/requirements-research.txt /tmp/requirements-research.txt
RUN case "$INSTALL_RESEARCH" in \
      1|true|TRUE|yes|YES) pip install --no-cache-dir -r /tmp/requirements-research.txt ;; \
      *) echo "Building without research model dependencies" ;; \
    esac

RUN groupadd --system mds01 && useradd --system --gid mds01 --home-dir /app --no-create-home mds01

COPY --chown=mds01:mds01 backend /app/backend

RUN mkdir -p /app/backend/storage /app/backend/database \
    && chown -R mds01:mds01 /app/backend/storage /app/backend/database

USER mds01

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
