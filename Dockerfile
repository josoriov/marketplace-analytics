# Start from a slim Python base image to keep the container smaller.
FROM python:3.12-slim

# Prevent Python from creating `.pyc` bytecode files inside the container.
ENV PYTHONDONTWRITEBYTECODE=1
# Force stdout and stderr to flush immediately so logs appear in real time.
ENV PYTHONUNBUFFERED=1

# Set the working directory used by all following Docker instructions.
WORKDIR /app

# Copy dependency definitions first so Docker can cache the install layer.
COPY requirements.txt .

# Upgrade `pip` and install the project dependencies without leaving pip cache files behind.
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copy the FastAPI application source code into the image.
COPY app ./app

# Document that the application listens on port 8000.
EXPOSE 8000

# Start the FastAPI app with Uvicorn when the container launches.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
