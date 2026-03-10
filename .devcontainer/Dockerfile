FROM mcr.microsoft.com/devcontainers/python:dev-3.14-bookworm

# Install uv (official binary via install script)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv /root/.local/bin/uv /usr/local/bin/uv \
    && mv /root/.local/bin/uvx /usr/local/bin/uvx

RUN rm -f /etc/apt/sources.list.d/yarn.list \
    && rm -f /usr/share/keyrings/yarn-archive-keyring.gpg

RUN apt-get update
RUN apt-get install -y --no-install-recommends \
        libudev-dev \
        libavformat-dev \
        libavcodec-dev \
        libavdevice-dev \
        libavutil-dev \
        libswscale-dev \
        libswresample-dev \
        libavfilter-dev \
        libpcap-dev \
        libturbojpeg0 \
        libyaml-dev \
        libxml2 \
        git \
        cmake
