# Single-stage build — this app has no compiled assets or frontend bundling
# step, so there's nothing a multi-stage build would buy beyond the layer
# caching already achieved below. Revisit if that changes.
FROM python:3.11-slim

WORKDIR /app

# Install dependencies before copying the rest of the source so this layer
# is only rebuilt when requirements.txt actually changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
