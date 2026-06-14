# Backend image: FastAPI served by uvicorn.
FROM python:3.12-slim

# Don't write .pyc files; flush logs straight to the container's stdout.
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1

WORKDIR /code

# Install deps first so this layer is cached unless requirements change.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the app code and the curated word list.
COPY app ./app
COPY words.json .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
