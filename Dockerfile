FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p templates output data

EXPOSE 8100

CMD ["python", "run.py", "serve", "--host", "0.0.0.0", "--port", "8100"]
