# 05. Docker

Install Docker Engine and the Compose plugin from Docker's official repository, and configure it for an always-on
server. Why Docker on a single host: [0001](decisions/0001-docker-on-single-host.md).

## 1. Install from the official Docker repository

Ubuntu's own `docker.io` package works too, but lags behind. Docker's repository has current releases and the
Compose v2+ plugin (`docker compose`, not the old `docker-compose`).

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings                                                   # directory for repository keys
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc  # Docker's signing key
sudo chmod a+r /etc/apt/keyrings/docker.asc
gpg --show-keys --with-fingerprint /etc/apt/keyrings/docker.asc   # must show 9DC8 5822 9FC7 DD38 854A  E2D8 8D81 803C 0EBF CD88
```

Add the repository (deb822 format). The codename and architecture are filled in automatically:

```bash
sudo tee /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "$VERSION_CODENAME")
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
docker --version && docker compose version
```

The service is enabled and started automatically, and it starts at every boot.

Docker packages come from Docker's repository, so the automatic security updates
([04, step 2](04-base-setup.md#2-updates)) **don't** upgrade them. Upgrade Docker deliberately with `sudo apt upgrade`.

## 2. Daemon settings

```bash
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "log-driver": "local",
  "log-opts": {
    "max-size": "50m",
    "max-file": "3"
  },
  "live-restore": true
}
EOF
sudo systemctl restart docker
docker info --format 'logging={{.LoggingDriver}} live-restore={{.LiveRestoreEnabled}}'   # local, true
```

| Setting | Why |
|---------|-----|
| `log-driver: local` + `max-size` / `max-file` | By default, container logs grow **without limit** and can fill the disk. This keeps at most 3 × 50 MB per container, in a compact (compressed) format. `docker logs` works as usual. Applies to containers created after the change. |
| `live-restore: true` | Containers keep running while the Docker daemon restarts, e.g. during a Docker upgrade. Home Assistant isn't interrupted. |

## 3. Run Docker without sudo

```bash
sudo usermod -aG docker "$USER"     # add your user to the docker group
```

Log out and back in (or open a new SSH session) for the group to take effect. Check with `id -nG`.

> Membership in the `docker` group is effectively **root access**: anyone in it can start a container that mounts
> the host's filesystem. Only add users who are trusted with root anyway. With passwordless sudo
> ([03, step 8](03-ubuntu-install.md#8-passwordless-sudo-optional)), this changes nothing.

## 4. Test

```bash
docker run --rm hello-world         # pulls a tiny image and prints "Hello from Docker!"
docker image rm hello-world         # clean up
```

## 5. Docker and the firewall

> ⚠️ **Published container ports bypass ufw.** Docker inserts its own firewall rules, which take effect before
> ufw's. A container started with `ports: ["8080:80"]` is reachable from **everywhere the server is reachable**,
> even though ufw has no rule for port 8080.

Verified on the reference server: a container published as `-p 18080:8080` answered from the LAN with no ufw rule,
and a container published as `-p 127.0.0.1:18081:8080` didn't.

Rules for this repository's compose files:

| Container needs | Do this |
|-----------------|---------|
| Access only from the server itself, or from other containers | Bind to localhost: `ports: ["127.0.0.1:8080:80"]`, or publish nothing and use a shared Docker network |
| Access from the LAN | Bind to localhost and put it behind a reverse proxy, or use `network_mode: host` and open the port in ufw |
| Discovery protocols (mDNS, SSDP, Bluetooth), e.g. Home Assistant | `network_mode: host`. The container uses the host's network stack directly, so **ufw applies** to it. |

**Never** use bare `"8080:80"` port mappings.

## Useful commands

```bash
docker ps                          # running containers
docker compose up -d               # start/update the stack in the current directory (detached)
docker compose logs -f <service>   # follow a service's logs
docker compose pull                # download newer images (only when the compose file changed)
docker system df                   # disk space used by images, containers, volumes
docker image prune                 # delete unused images
```
