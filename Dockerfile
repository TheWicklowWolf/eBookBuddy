
FROM python:3.12-alpine

# Set build arguments
ARG RELEASE_VERSION
ENV RELEASE_VERSION=${RELEASE_VERSION}
ENV EBB_PORT=5000

# Create User
ARG UID=1000
ARG GID=1000
RUN addgroup -g $GID general_user && \
    adduser -D -u $UID -G general_user -s /bin/sh general_user

# Create directories and set permissions
COPY . /ebookbuddy
WORKDIR /ebookbuddy
RUN chown -R $UID:$GID /ebookbuddy

RUN apk --no-cache --no-interactive update && apk --no-cache --no-interactive upgrade

# Install Firefox and Xvfb
RUN apk --no-cache add \
    firefox \
    xvfb \ 
    ttf-freefont \
    fontconfig \
    dbus

# Install requirements and run code
RUN pip install --root-user-action=ignore --no-cache-dir --upgrade pip
RUN pip install --root-user-action=ignore --no-cache-dir -r requirements.txt
ENV PYTHONPATH "${PYTHONPATH}:/ebookbuddy/src"
EXPOSE ${EBB_PORT}
USER general_user
CMD exec gunicorn src.eBookBuddy:app -b 0.0.0.0:${EBB_PORT} -c gunicorn_config.py
