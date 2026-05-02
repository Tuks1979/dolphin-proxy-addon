ARG BUILD_FROM=ghcr.io/hassio-addons/base:14.0.0
FROM ${BUILD_FROM}

# Install Python and required packages
RUN apk add --no-cache python3 py3-pip

# Copy add-on files
COPY run.sh /run.sh

# Ensure run.sh is executable
RUN chmod a+x /run.sh

CMD [ "/run.sh" ]
