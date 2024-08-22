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

# copy project
COPY ../pururu-bot .

# Run the application
CMD ["python", "bot.py"]