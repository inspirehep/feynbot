# Use the official Python 3.12 image as the base
FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# Copy only requirements.txt first to leverage Docker cache
COPY requirements.txt .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port that Gradio will run on (default is 7860)
EXPOSE 7860

# Run the application
CMD ["python", "src/demo.py"]