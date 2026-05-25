FROM python:3.11-slim

RUN apt-get update && apt-get install -y curl git

RUN curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | sh
RUN mv /root/bin/arduino-cli /usr/local/bin/

RUN arduino-cli config init
RUN arduino-cli config add board_manager.additional_urls https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
RUN arduino-cli core update-index
RUN arduino-cli core install esp32:esp32
RUN arduino-cli lib install "Adafruit SSD1306" "Adafruit GFX Library" "Adafruit ADS1X15" "Adafruit BusIO"

WORKDIR /app
COPY server.py .
RUN pip install flask flask-cors

CMD ["python3", "server.py"]