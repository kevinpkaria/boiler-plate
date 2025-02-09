# Use the official Python 3.11 Alpine image as a parent image
FROM python:3.11-alpine

# Set the working directory in the container
WORKDIR /app

# Install build dependencies
RUN apk update && apk add git
RUN apk add --update make automake gcc g++ subversion python3-dev musl-dev libffi-dev cmake

# Copy the requirements file into the container
COPY requirements.txt .

# Install the dependencies
RUN pip install --upgrade pip setuptools==70.0.0 psycopg2-binary
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 80

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]