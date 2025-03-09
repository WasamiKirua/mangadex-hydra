FROM python:3.12-slim-bullseye

WORKDIR /app

# Install system dependencies for patool and rar
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# Add contrib and non-free repositories
RUN apt-get update && \
    apt-add-repository contrib -y && \
    apt-add-repository non-free -y

# Install rar and 7zip
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    unrar \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Create data directory with proper permissions
RUN mkdir -p /app/data && chmod 777 /app/data

# Don't copy the application code - it will be mounted
# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development
ENV FLASK_DEBUG=1

# Expose the port
EXPOSE 5001

# Use flask run as the default command
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001", "--reload"]