FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=julian.settings

# Set work directory
WORKDIR /app

# Install system dependencies including OpenCV and computer vision libraries
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    netcat-traditional \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip
RUN for pkg in $(cat requirements.txt); do pip install $pkg || true; done


# Явно устанавливаем opencv-python-headless чтобы избежать проблем с GUI
RUN pip uninstall -y opencv-python || true
RUN pip install opencv-python-headless==4.10.0.84
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