# Use the official Python image as the base image
FROM python:3.10-slim

# Set the working directory inside the container
WORKDIR /app

# Copy the script and requirements into the container
COPY emby_collection_to_library.py .
COPY requirements.txt .

# Install any Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the script on container startup (customize as necessary)
CMD ["python", "emby_collection_to_library.py"]
