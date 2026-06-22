# Use a lightweight Python image for ARM architecture
FROM python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy the requirements file and install dependencies
# This is a good practice to leverage Docker's build cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code, including your logo
COPY . .

# Expose the port (Cloud Run defaults to 8080, but can vary)
EXPOSE 8080

# Command to run the Streamlit application, dynamically binding to $PORT for Cloud Run compatibility
CMD ["sh", "-c", "streamlit run streamlit_app.py --server.port=${PORT:-8080} --server.address=0.0.0.0"]
