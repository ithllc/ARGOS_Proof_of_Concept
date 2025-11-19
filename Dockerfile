# Stage 1: Build the React frontend
FROM node:18-alpine AS build-step

WORKDIR /app/frontend

COPY frontend/package.json frontend/package-lock.json ./
RUN npm install
COPY frontend/ .
RUN npm run build

# Stage 2: Build the Python application
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the built frontend from the build-step stage
COPY --from=build-step /app/frontend/build /app/frontend/build

# Copy the rest of the application code into the container at /app
COPY . .

# Set the PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Make port 8000 available to the world outside this container
EXPOSE 8080

# Run the FastAPI application with Gunicorn, a production-ready server
CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker -w 4 --bind 0.0.0.0:${PORT:-8080} src.main:app"]
