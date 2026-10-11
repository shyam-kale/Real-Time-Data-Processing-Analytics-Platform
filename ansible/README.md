# DataFlow Ansible Automation

## Structure
```
ansible/
├── inventory.ini          # Server IPs
├── group_vars/
│   └── webservers.yml     # All config vars
├── site.yml               # Full setup (run once)
├── deploy.yml             # Deploy latest code
├── rollback.yml           # Roll back one commit
└── roles/
    ├── app/               # Python app + systemd service
    ├── nginx/             # Reverse proxy + SSL
    ├── monitoring/        # Grafana Alloy agent
    └── backup/            # Daily DB backup + cron
```

## Quick Start

### 1. Install Ansible
```bash
pip install ansible
```

### 2. Set your server IP
Edit `inventory.ini` and replace `YOUR_SERVER_IP` with your actual server IP.

### 3. Set your domain
Edit `group_vars/webservers.yml` and set `domain: your-domain.com`

### 4. First-time full setup
```bash
ansible-playbook -i inventory.ini site.yml
```

### 5. Deploy latest code (after git push)
```bash
ansible-playbook -i inventory.ini deploy.yml
```

### 6. Rollback
```bash
ansible-playbook -i inventory.ini rollback.yml
```

## What each role does

| Role | What it does |
|------|-------------|
| `app` | Installs Python, Node, clones repo, builds frontend, creates systemd service |
| `nginx` | Installs Nginx, sets up reverse proxy, gets SSL cert via Certbot |
| `monitoring` | Installs Grafana Alloy for log shipping + system metrics |
| `backup` | Daily SQLite + uploads backup at 2am, keeps 7 days |

## Typical workflow
```
git push → ansible-playbook deploy.yml → app live in ~2 min
```
