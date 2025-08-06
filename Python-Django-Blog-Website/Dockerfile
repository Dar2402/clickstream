# Base image
FROM python:3.9-alpine

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apk update \
    && apk add --virtual build-deps gcc python3-dev musl-dev

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code
COPY . .

# Set the command to run the app with Gunicorn
ENTRYPOINT ["sh", "entrypoint.sh"]

CMD ["gunicorn", "myproject.wsgi:application", "--bind", "0.0.0.0:8000"]