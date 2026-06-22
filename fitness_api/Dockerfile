# Use an official Python runtime for ARM architecture
FROM arm64v8/python:3.11-slim

# Install necessary build dependencies
RUN apt-get update && apt-get install -y \
    pkg-config \
    default-libmysqlclient-dev \
    gcc

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5001

CMD ["python", "api_app.py"]
