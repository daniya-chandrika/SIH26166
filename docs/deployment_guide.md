# Scientific Lunar Image Registration (SIH26166) - Deployment Guide

This comprehensive guide covers deploying the **Scientific Lunar Image Registration System & Interactive Dashboard** across multiple environments:
1. **Local / On-Premise Host** (Windows, Linux, macOS)
2. **Containerized with Docker & Docker Compose**
3. **Cloud PaaS Platforms** (Render, Railway, Hugging Face Spaces)
4. **Cloud Linux VPS** (AWS EC2, DigitalOcean, GCP, Azure with Systemd & Nginx SSL)
5. **Database & Cloud Storage Configuration** (Supabase / PostgreSQL)

---

## 1. System Requirements & Architecture

- **Backend**: Python 3.9+ HTTP/REST server (`dashboard_server.py`) serving API endpoints and 12-stage registration orchestrator.
- **Frontend**: Lightweight, single-page application (`frontend/index.html`, `frontend/style.css`, `frontend/app.js`).
- **Core Dependencies**: `numpy`, `opencv-python`, `scipy`, `matplotlib`, `pydantic`, `pandas`, `tqdm`.
- **System Libraries**: `libgl1`, `libglib2.0-0` (required for headless OpenCV processing).
- **Default Port**: `8080` (or dynamically defined via `PORT` environment variable).

---

## 2. Option 1: Local / On-Premise Deployment

### Step 1: Clone and Set Up Virtual Environment
```bash
# Clone the repository
git clone https://github.com/your-username/SIH26166.git
cd SIH26166

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# Windows (CMD):
.\venv\Scripts\activate.bat
# Linux / macOS:
source venv/bin/activate
```

### Step 2: Install Dependencies
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*(Optionally populate Supabase credentials if syncing metrics to cloud database).*

### Step 4: Launch the Server
```bash
python dashboard_server.py 8080
```
Open your web browser at **`http://localhost:8080`**.

---

## 3. Option 2: Docker & Docker Compose Deployment (Recommended)

### Using Docker Compose (Zero Setup):
```bash
# Build and start the container in detached mode
docker compose up -d --build

# View real-time logs
docker compose logs -f

# Stop the container
docker compose down
```

### Using Standalone Docker:
```bash
# Build the Docker image
docker build -t lunar-registration:latest .

# Run container with volume persistence
docker run -d \
  --name lunar-dashboard \
  -p 8080:8080 \
  -v "$(pwd)/experiments/runs:/app/experiments/runs" \
  --env-file .env \
  lunar-registration:latest
```

---

## 4. Option 3: Cloud PaaS Deployment (Render / Railway / HF Spaces)

### A. Deploying to Render (Free / Starter Tier)
1. Push repository to GitHub/GitLab.
2. Sign in to [Render.com](https://render.com) and click **New +** -> **Web Service**.
3. Select your repository.
4. Set the following settings:
   - **Environment**: `Python` (or `Docker`)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python dashboard_server.py`
   - **Environment Variables**:
     - `PORT` = `8080` (Render sets this automatically)
     - `PYTHONUNBUFFERED` = `1`
5. Click **Create Web Service**.

### B. Deploying to Railway
1. Sign in to [Railway.app](https://railway.app) and click **New Project** -> **Deploy from GitHub repo**.
2. Select your repository.
3. Railway will detect the `Dockerfile` automatically.
4. In **Settings** -> **Networking**, click **Generate Domain** to get a public URL.

### C. Deploying to Hugging Face Spaces
1. Create a new Space at [huggingface.co/spaces](https://huggingface.co/spaces).
2. Select SDK: **Docker**.
3. Push your repository code to the Hugging Face repository remote.
4. Hugging Face builds and hosts the container on port `7860` (or `8080`).

---

## 5. Option 4: Linux VPS Deployment (AWS EC2 / Ubuntu Server)

### Step 1: System Packages Installation
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git libgl1 libglib2.0-0 nginx curl
```

### Step 2: Clone & Install Codebase
```bash
sudo mkdir -p /var/www/lunar-registration
sudo chown -R $USER:$USER /var/www/lunar-registration
git clone https://github.com/your-username/SIH26166.git /var/www/lunar-registration
cd /var/www/lunar-registration

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Create Systemd Background Service
Create `/etc/systemd/system/lunar-dashboard.service`:
```ini
[Unit]
Description=SIH26166 Lunar Registration Dashboard
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/var/www/lunar-registration
ExecStart=/var/www/lunar-registration/venv/bin/python /var/www/lunar-registration/dashboard_server.py 8080
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable lunar-dashboard
sudo systemctl start lunar-dashboard
sudo systemctl status lunar-dashboard
```

### Step 4: Configure Nginx Reverse Proxy with SSL
Create `/etc/nginx/sites-available/lunar-dashboard`:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site and obtain free SSL via Let's Encrypt:
```bash
sudo ln -s /etc/nginx/sites-available/lunar-dashboard /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Install SSL certificate
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## 6. Verification & Health Check Endpoints

Verify your deployment using cURL or a browser:
- `GET /api/health` -> Returns `{"status": "healthy", "timestamp": "...", "runs_count": N}`
- `GET /api/scenarios` -> Returns list of supported orbital benchmark scenarios
- `GET /api/summary` -> Returns aggregate statistics of all completed registration runs
- `POST /api/experiments/run` -> Triggers background asynchronous 12-stage registration
