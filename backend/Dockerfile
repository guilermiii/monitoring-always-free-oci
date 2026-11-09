FROM python:3.11-alpine

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install runtime dependencies only (curl for container healthcheck)
RUN apk add --no-cache curl

COPY requirements.txt .

# Install dependencies using precompiled musllinux wheels, then clean build tooling to eliminate CVEs
RUN pip install --no-cache-dir -r requirements.txt && \
    pip uninstall -y pip setuptools wheel

# Create non-privileged user and group for Kubernetes Pod Security Standard (Restricted)
RUN addgroup -g 1000 appgroup && \
    adduser -u 1000 -G appgroup -s /bin/sh -D appuser && \
    mkdir -p /app/data /home/appuser/.oci /home/appuser/.ssh && \
    chown -R appuser:appgroup /app /home/appuser

COPY --chown=appuser:appgroup app/ ./app

USER 1000:1000

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/livez || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

