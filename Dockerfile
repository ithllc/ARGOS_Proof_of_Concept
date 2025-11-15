# Use an official Python runtime as a parent image
FROM python:3.11-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
COPY . .

# Set the PYTHONPATH to include the src directory
ENV PYTHONPATH=/app/src

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run the FastAPI application
# The command to run the FastAPI app is 'uvicorn src.main:app --host 0.0.0.0 --port 8000'
# The 'src' directory is where main.py is located.
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]