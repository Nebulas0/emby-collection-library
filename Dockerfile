# Use an official Python image as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PUID=1000
ENV PGID=1000
ENV TZ=Etc/UTC

# Set working directory
WORKDIR /app

# Install necessary system packages for Python and symlink creation
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    bash \
    gcc \
    libc-dev \
    libffi-dev \
    make \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt to the container
COPY requirements.txt /app/

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the script into the container
COPY emby_collection_to_library.py /app/

# Set permissions for Saltbox (ensure PUID and PGID are respected)
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -s /bin/bash appuser && \
    chown -R appuser:appgroup /app

# Switch to non-root user
USER appuser

# Set the default command to run the script
CMD ["python", "/app/emby_collection_to_library.py"]
