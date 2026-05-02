ARG BUILD_FROM=ghcr.io/home-assistant/amd64-base:3.15
FROM ${BUILD_FROM}

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache py3-paho-mqtt

# Install HTTPX via pip (Alpine 3.15 allows this)
RUN pip3 install --no-cache-dir httpx

# Copy add-on files
COPY run.sh /run.sh
COPY dolphin_proxy.py /dolphin_proxy.py

# Ensure run.sh is executable
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
