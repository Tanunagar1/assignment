FROM python:3.11
# Set the working directory in the container
WORKDIR /app

# Copy the requirements file to the working directory
COPY requirements.txt .

# Install any dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code to the working directory
COPY . .

# Expose the port that the Flask app runs on
EXPOSE 5000

# Define the command to run the application
CMD ["python", "main.py"]