# Menggunakan image Python resmi sebagai base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Menyalin file requirements.txt ke dalam container
COPY requirements.txt .

# Menginstal dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Menyalin semua file yang ada di direktori saat ini ke dalam container
COPY . .

# Menjalankan bot
CMD ["python", "main.py"]
