# Use Apify's Python + Playwright base image
FROM apify/actor-python-playwright:3.11

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy all source code
COPY . ./

# Set the entrypoint to run main script
CMD ["python", "-m", "main"]
