FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=julian.settings

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    netcat-traditional \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Явно устанавливаем gunicorn на случай, если его нет в requirements.txt
RUN pip install gunicorn==23.0.0

# Проверяем установку
RUN pip show gunicorn && echo "Gunicorn path:" && which gunicorn

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p /app/static /app/media /app/media/models /app/media/reports /app/media/yolo_datasets /app/media/yolo_training

# Make entrypoint script executable
COPY entrypoint.sh .
RUN chmod +x entrypoint.sh

# Expose port
EXPOSE 8000

# Run entrypoint
CMD ["./entrypoint.sh"]