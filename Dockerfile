FROM python:3.12-slim

RUN addgroup -S nonroot \
    && adduser -S nonroot -G nonroot

USER nonroot

# set working directory
WORKDIR /app

# set environment variables
ENV APP_ENV=production
# ENV APP_ENV=development

# Install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY bot.py .
COPY utils.py .
COPY config.py .
COPY domain .
COPY infrastructure .
COPY application .

# Copy Configs
COPY google_creds.json .
COPY .env.base .
COPY .env.prod .


# Run the application
CMD ["python", "bot.py"]