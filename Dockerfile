FROM python:3.12-slim-bullseye

WORKDIR /app

# Install system dependencies for patool and rar
RUN apt-get update
RUN apt-get install software-properties-common -y
RUN apt-add-repository contrib -y 
RUN apt-add-repository non-free -y
RUN apt-get update && apt-get install -y \
    unrar \
    p7zip-full \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy requirements first for better caching
COPY requirements.txt .

# Install dependencies using pip, you can use uv if you want
RUN pip install -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables
ENV FLASK_APP=app.py
ENV FLASK_ENV=development

# Expose the port
EXPOSE 5001

# Run the application
CMD ["flask", "run", "--host=0.0.0.0", "--port=5001"]