
FROM python:3.11-slim

# Install Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install fastapi cli tool if not already in requirements.txt
RUN pip install fastapi[all]

# Copy the full project
COPY . .

# Expose port (default FastAPI run port)
EXPOSE 8000

# Run the app using FastAPI CLI
CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8000"]
