FROM python:3.12-alpine

# Set build arguments
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}

# Install Firefox, Xvfb and su-exec
RUN apk --no-cache add \
    firefox \
    xvfb \ 
    ttf-freefont \
    fontconfig \
    dbus \
    su-exec    

# Create directories and set permissions
COPY . /ebookbuddy
WORKDIR /ebookbuddy

# Install requirements
RUN pip install --no-cache-dir -r requirements.txt

# Set Environmental Variables
ENV PYTHONPATH=/ebookbuddy/src

# Make the script executable
RUN chmod +x thewicklowwolf-init.sh

# Expose port
EXPOSE 5000

# Start the app
ENTRYPOINT ["./thewicklowwolf-init.sh"]
