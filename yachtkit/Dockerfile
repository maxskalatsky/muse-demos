FROM python:3.12-slim
WORKDIR /app
COPY app.py ./
COPY static ./static
ENV YACHTKIT_BIND=0.0.0.0
EXPOSE 10000
CMD ["python3", "app.py"]
