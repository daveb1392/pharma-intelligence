# Use Apify's Python + Playwright base image
FROM apify/actor-python-playwright:3.11

# Set working directory
WORKDIR /usr/src/app

# Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code (scrapers, storage, utils)
COPY scrapers ./scrapers
COPY storage ./storage
COPY utils ./utils

# Set the entrypoint to run Punto Farma scraper
CMD ["python", "-m", "scrapers.punto_farma"]
