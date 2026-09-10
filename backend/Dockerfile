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

ARG INSTALL_VIDEO_DETECTION=false
COPY backend/requirements-video-detection.txt /tmp/requirements-video-detection.txt
RUN case "$INSTALL_VIDEO_DETECTION" in \
      1|true|TRUE|yes|YES) pip install --no-cache-dir -r /tmp/requirements-video-detection.txt ;; \
      *) echo "Building without VSViG video model dependencies" ;; \
    esac

# MediaPipe also installs OpenCV's contrib wheel, which needs these shared libraries.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Fail the build if the video runtime cannot load in a clean installation.
RUN python -c "import cv2; import mediapipe as mp; assert hasattr(mp, 'solutions')"

RUN groupadd --system mds01 && useradd --system --gid mds01 --home-dir /app --no-create-home mds01

COPY --chown=mds01:mds01 backend /app/backend

RUN mkdir -p /app/backend/storage /app/backend/database \
    && chown -R mds01:mds01 /app/backend/storage /app/backend/database

USER mds01

RUN python -m backend.scripts.verify_video_runtime

CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
