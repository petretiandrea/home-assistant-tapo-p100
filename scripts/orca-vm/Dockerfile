ARG BASE_IMAGE=orca-tapo-devcontainer:base
FROM ${BASE_IMAGE}

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-server \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd /home/vscode/.ssh \
    && install -d -o vscode -g vscode /workspaces \
    && chown -R vscode:vscode /home/vscode/.ssh \
    && chmod 700 /home/vscode/.ssh \
    && printf '\nPasswordAuthentication no\nPermitRootLogin no\nAllowUsers vscode\n' >> /etc/ssh/sshd_config \
    && npm install -g @openai/codex \
    && rm -f /etc/ssh/ssh_host_*

USER vscode
RUN git clone https://github.com/petretiandrea/home-assistant-tapo-p100.git /workspaces/home-assistant-tapo-p100
WORKDIR /workspaces/home-assistant-tapo-p100
ENV REMOTE_CONTAINERS=1 HA_INSTALL_HACS=1 PYTHONASYNCIODEBUG=1 PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 APT_UPDATE=0
RUN bash .devcontainer/setup-shell.sh && script/setup/setup

USER root
COPY scripts/orca-vm/entrypoint.sh /usr/local/bin/orca-docker-ssh-entrypoint
RUN chmod +x /usr/local/bin/orca-docker-ssh-entrypoint

EXPOSE 22 8123
ENTRYPOINT ["/usr/local/bin/orca-docker-ssh-entrypoint"]
