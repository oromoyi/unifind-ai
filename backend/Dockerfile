FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn
COPY . .
ENV PORT=5000 UPLOAD_DIR=/app/uploads
EXPOSE 5000
CMD ["sh", "-c", "python seed.py $SEED_ARGS && gunicorn -b 0.0.0.0:5000 -w 2 run:app"]
