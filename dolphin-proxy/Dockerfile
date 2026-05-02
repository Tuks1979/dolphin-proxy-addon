ARG BUILD_FROM=ghcr.io/home-assistant/amd64-addon-base:3.19
FROM ${BUILD_FROM}

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip
RUN apk add --no-cache py3-httpx py3-paho-mqtt

# Copy add-on files
COPY run.sh /run.sh
COPY dolphin_proxy.py /dolphin_proxy.py

# Ensure run.sh is executable
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
