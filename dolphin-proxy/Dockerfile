ARG BUILD_FROM=ghcr.io/home-assistant/amd64-addon-debian-base:latest
FROM ${BUILD_FROM}

# Install Python and required packages
RUN apt-get update && \
    apt-get install -y python3 python3-pip && \
    pip3 install httpx paho-mqtt && \
    apt-get clean

# Copy add-on files
COPY run.sh /run.sh
COPY dolphin_proxy.py /dolphin_proxy.py

# Ensure run.sh is executable
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
