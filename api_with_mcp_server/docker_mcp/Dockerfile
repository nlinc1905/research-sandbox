FROM python:3.11-slim

# Create a non-root user
RUN adduser --disabled-password --gecos '' appuser

WORKDIR /app

# Install system dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

# Change ownership to appuser
RUN chown -R appuser:appuser /app

# Switch to non-root user to run the application
USER appuser
