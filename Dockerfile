# STAGE 1: Build the React Frontend
# ------------------------------------
FROM node:18-alpine AS builder

# Set the working directory for the frontend
WORKDIR /app/frontend

# Copy package.json and package-lock.json to leverage Docker cache
COPY frontend/package*.json ./

# Install frontend dependencies
RUN npm install

# Copy the rest of the frontend source code
COPY frontend/ ./

# Build the frontend application
RUN npm run build


# STAGE 2: Build the Python Backend and Serve the Frontend
# ---------------------------------------------------------
FROM python:3.10-slim

# Set the working directory for the backend
WORKDIR /app

# Install system dependencies required for libraries like pdfplumber
RUN apt-get update && apt-get install -y \
    build-essential \
    libpoppler-cpp-dev \
    pkg-config \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY poetry.lock pyproject.toml /app/

# Install project dependencies (excluding dev dependencies)
RUN poetry install --no-root --no-dev

# Copy the application source code
COPY src/ /app/src/

# Copy the built frontend from the 'builder' stage
COPY --from=builder /app/frontend/build /app/frontend/build

# Expose the port the app runs on
EXPOSE 8000

# Command to run the application
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
