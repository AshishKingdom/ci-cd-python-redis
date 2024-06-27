# Use an official lightweight Python image.
# 3.8-slim is chosen here to keep the image small.
FROM python:3.10-slim

# Set the working directory in the container to /app.
WORKDIR /app

# Copy the current directory contents into the container at /app.
COPY . /app

# Install pip requirements.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Uvicorn for ASGI support.
RUN pip install uvicorn gunicorn

# Expose the port the app runs on.
EXPOSE 8000

# Use gunicorn as the entry point to manage the app.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]