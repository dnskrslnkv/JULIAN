FROM python:3.10-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=julian.settings

# Set work directory
WORKDIR /app

# Install system dependencies with error handling
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    libpq-dev \
    python3-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN for pkg in $(cat requirements.txt); do pip install $pkg || true; done

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /app/static /app/media /app/media/models /app/media/reports /app/media/yolo_datasets /app/media/yolo_training

# Collect static files
RUN python manage.py collectstatic --noinput

# Make entrypoint script executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Run entrypoint
CMD ["./entrypoint.sh"]