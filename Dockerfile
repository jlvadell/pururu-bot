FROM python:3.12-slim

# Create a non-root user and add sudo permision
RUN adduser --no-create-home nonroot
RUN usermod -aG sudo nonroot

# Update the package list and clenaup after the install
RUN apt update \
    && apt upgrade -y \
    && apt-get install -y --no-install-recommends \
    && apt-get clean \
    && apt-get autoclean \
    && apt-get autoremove --purge  -y \
    && rm -rf /var/lib/apt/lists/*

# Set the non-root user as the default user
USER nonroot

# set working directory
WORKDIR /home/nonroot/app

# set environment variables
ENV APP_ENV=production
ENV PYTHONPATH="${PYTHONPATH}:/home/nonroot/app/src"

# Install requirements
COPY src/pururu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY ./src/ ./


# Run the application
CMD ["python", "pururu/bot.py"]