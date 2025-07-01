# Dockerfile
# Use a slim Python image for smaller size
FROM python:3.10-slim

ARG API_KEY
ENV API_KEY=$API_KEY

WORKDIR /app_root 
# Copy only the requirements file first for caching
COPY ./requirements.txt .
# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

COPY app /app_root/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
