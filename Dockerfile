# Dockerfile
FROM python:3.13.1-slim

WORKDIR /app

# Copy only necessary files
COPY * /app/

# Install dependencies
RUN pip install -r requirements.txt

# Copy only necessary files from the builder stage
COPY . /app

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Expose port and specify the command to run the application
EXPOSE 9300
CMD ["python", "main.py"]