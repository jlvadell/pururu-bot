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
COPY src/pururu/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY src/pururu ./


# Run the application
CMD ["python", "pururu/bot.py"]