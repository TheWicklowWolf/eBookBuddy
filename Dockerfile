
FROM python:3.13-alpine

# Set build arguments
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}

# Create User
ARG UID=1000
ARG GID=1000
RUN addgroup -g $GID general_user && \
    adduser -D -u $UID -G general_user -s /bin/sh general_user

# Create directories and set permissions
COPY . /ebookbuddy
WORKDIR /ebookbuddy
RUN chown -R $UID:$GID /ebookbuddy

# Install Firefox and Xvfb
RUN apk --no-cache add \
    firefox \
    xvfb \ 
    ttf-freefont \
    fontconfig \
    dbus

# Install requirements and run code
RUN pip install --no-cache-dir -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/ebookbuddy/src"
EXPOSE 5000
USER general_user
CMD ["gunicorn", "src.eBookBuddy:app", "-c", "gunicorn_config.py"]