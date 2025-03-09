FROM python:3.10

WORKDIR /app

# Cài đặt thư viện
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ dự án vào container
COPY . .

# Copy file .env vào container
COPY .env .env

# Expose port 8000
EXPOSE 8000

# Chạy ứng dụng
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
