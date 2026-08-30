# 🚀 LTX 2.3 I2V Space - Setup & Deployment Guide

## Quick Start (Hugging Face Spaces)

### Step 1: Create a New Space
1. Go to [huggingface.co/new-space](https://huggingface.co/new-space)
2. Fill in:
   - **Space name**: `ltx-2-3-i2v-space`
   - **License**: Apache 2.0
   - **Visibility**: Public
   - **Space SDK**: Docker

### Step 2: Set Environment Variables
In your Space settings (⚙️ Settings → Variables and secrets):

```
HF_TOKEN=your_huggingface_api_token
ANTHROPIC_API_KEY=your_anthropic_api_key
COMFYUI_SERVER=http://localhost:8188
```

### Step 3: Clone & Deploy
```bash
git clone https://github.com/Goro888/ltx-2-3-i2v-space.git
cd ltx-2-3-i2v-space
git push
```

Your Space will auto-build and launch on Hugging Face!

---

## Local Development Setup

### Prerequisites
- Python 3.10+
- CUDA 12.1+ (for GPU acceleration)
- Docker & Docker Compose (for full stack)
- 16GB+ VRAM recommended
- 50GB+ free disk space

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone repository
git clone https://github.com/Goro888/ltx-2-3-i2v-space.git
cd ltx-2-3-i2v-space

# 2. Copy environment template
cp .env.template .env

# 3. Update .env with your API keys
nano .env
# Set: HF_TOKEN, ANTHROPIC_API_KEY

# 4. Build and start services
docker-compose up -d

# 5. Wait for services to be healthy
docker-compose ps

# 6. Access Space at http://localhost:7860
```

**Services Started:**
- ComfyUI Backend: `http://localhost:8188`
- LTX Gradio Space: `http://localhost:7860`
- Redis Cache: `localhost:6379`

**Useful Commands:**
```bash
# View logs
docker-compose logs -f ltx-space

# Stop services
docker-compose down

# Restart specific service
docker-compose restart ltx-space

# Clean volumes (WARNING: deletes data)
docker-compose down -v
```

### Option 2: Local Installation

#### 2a. Install Python Dependencies
```bash
# Create virtual environment
python3.10 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install requirements
pip install -r requirements.txt

# Install additional dev tools (optional)
pip install pytest black flake8
```

#### 2b. Setup ComfyUI Backend
```bash
# Clone ComfyUI
git clone https://github.com/comfyanonymous/ComfyUI.git
cd ComfyUI

# Install ComfyUI dependencies
pip install -r requirements.txt

# Download LTX model
wget https://huggingface.co/Lightricks/LTX-Video/resolve/main/LTX-Video-v2.3-fp8-mixed.safetensors

# Start ComfyUI server
python main.py --listen 127.0.0.1 --port 8188
```

#### 2c. Start LTX Space
```bash
# In new terminal
cd ltx-2-3-i2v-space

# Copy env template
cp .env.template .env

# Update with your keys
nano .env

# Run app
python app.py
```

Access at `http://localhost:7860`

---

## Configuration

### Environment Variables

**Essential:**
```bash
HF_TOKEN=                    # Hugging Face API token
ANTHROPIC_API_KEY=           # For prompt enhancement
COMFYUI_SERVER=http://localhost:8188
```

**Optional:**
```bash
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
ENABLE_POLICY_CHECK=true    # Enable content filtering
STRICT_POLICY_MODE=true     # Stricter policy enforcement
MAX_GENERATIONS=-1          # -1 for unlimited
ENABLE_CACHE=true           # Cache generation results
```

### Model Configuration

Edit preset configurations in `app.py` or environment:

```python
PRESETS = {
    "cinematic": {
        "steps": 50,
        "guidance_scale": 7.5,
        "sigma_min": 0.1,
        "sigma_max": 14.0,
    },
    # ... other presets
}
```

### Hardware Requirements

| Resolution | VRAM | Speed | Quality |
|-----------|------|-------|---------|
| 512x320   | 8GB  | Fast  | Good    |
| 848x480   | 12GB | Medium | Excellent |
| 1280x768  | 16GB | Slow  | Maximum |

---

## Deployment Variations

### A. Hugging Face Spaces (FREE + Unlimited)

**Pros:**
- ✅ Completely free tier available
- ✅ Automatic SSL/HTTPS
- ✅ Auto-scaling
- ✅ Built-in monitoring
- ✅ Easy sharing

**Setup:**
1. Create Space (instructions above)
2. Set environment variables
3. Push code → Auto-deploys

### B. Self-Hosted Server

**Setup on Ubuntu 22.04:**

```bash
# 1. Install dependencies
sudo apt-get update
sudo apt-get install -y python3.10 python3-pip docker.io docker-compose

# 2. Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# 3. Clone and setup
git clone https://github.com/Goro888/ltx-2-3-i2v-space.git
cd ltx-2-3-i2v-space
cp .env.template .env

# 4. Edit environment
nano .env

# 5. Start with docker-compose
docker-compose up -d

# 6. Setup reverse proxy (nginx)
sudo apt-get install -y nginx
sudo nano /etc/nginx/sites-available/ltx
# See nginx config below

# 7. Enable SSL
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot -d your-domain.com
```

**Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws {
        proxy_pass http://localhost:7860/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### C. AWS/GCP/Azure Deployment

**Using AWS EC2:**

```bash
# 1. Launch g4dn.xlarge instance (1x NVIDIA T4)
# Ubuntu 22.04 LTS, 100GB EBS

# 2. SSH and setup
ssh -i your-key.pem ubuntu@instance-ip

# 3. Install NVIDIA drivers
sudo apt-get install -y nvidia-driver-535

# 4. Follow self-hosted setup above

# 5. Get public URL and add domain
```

---

## Testing & Validation

### Run Unit Tests
```bash
# Install test dependencies
pip install pytest pytest-cov

# Run tests
pytest tests/ -v

# Coverage report
pytest --cov=. --cov-report=html
```

### Manual Testing
```bash
# Test ComfyUI backend
python -c "from comfyui_backend import ComfyUIBackend; \
           backend = ComfyUIBackend(); \
           print('✅ Backend OK' if backend.health_check() else '❌ Backend DOWN')"

# Test policy checker
python -c "from policy_checker import PolicyChecker; \
           checker = PolicyChecker(); \
           print(checker.get_policy_summary())"

# Test Gradio app
python app.py --share
```

---

## Troubleshooting

### ComfyUI Connection Failed
```bash
# Check if service is running
docker-compose ps

# Check logs
docker-compose logs comfyui

# Restart service
docker-compose restart comfyui
```

### Out of Memory
```bash
# Reduce resolution in UI
# Or use "Fast" preset
# Or restart Docker to clear cache
docker restart comfyui
```

### Slow Generations
- ✅ Use "Fast" or "Smooth Motion" preset
- ✅ Reduce resolution (848x480 → 512x320)
- ✅ Lower step count (50 → 25)
- ✅ Reduce motion scale

### API Key Errors
```bash
# Verify keys are set
docker-compose logs ltx-space | grep "API\|TOKEN"

# Check .env file
cat .env

# Re-create containers
docker-compose down
docker-compose up -d
```

---

## Monitoring & Logging

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f ltx-space

# With timestamps
docker-compose logs -f --timestamps ltx-space
```

### Health Check
```bash
# Check service status
curl http://localhost:7860

# Check ComfyUI
curl http://localhost:8188/system_stats

# Check Redis
redis-cli ping
```

### Performance Monitoring
```bash
# GPU usage
docker exec comfyui nvidia-smi

# Container stats
docker stats ltx-space comfyui redis
```

---

## Updates & Maintenance

### Update to Latest Version
```bash
# Pull latest changes
git pull origin main

# Rebuild containers
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Database Cleanup (Optional)
```bash
# Clear cache
rm -rf volumes/ltx-cache/*

# Clear Redis
redis-cli FLUSHALL

# Restart services
docker-compose restart
```

---

## Production Checklist

- [ ] Environment variables configured
- [ ] SSL certificate installed (HTTPS)
- [ ] Firewall rules configured (port 443)
- [ ] Backup strategy in place
- [ ] Monitoring alerts setup
- [ ] Logs rotated regularly
- [ ] Rate limiting configured
- [ ] Policy compliance verified
- [ ] Load testing completed
- [ ] Documentation updated

---

## Support & Resources

- 📚 [Gradio Docs](https://gradio.app)
- 🎬 [LTX Video Paper](https://arxiv.org/abs/2404.01204)
- 🔧 [ComfyUI Docs](https://github.com/comfyanonymous/ComfyUI)
- 🤖 [Hugging Face Docs](https://huggingface.co/docs)
- 💬 [GitHub Issues](https://github.com/Goro888/ltx-2-3-i2v-space/issues)

---

## License

Apache 2.0 - See LICENSE file

## Contributing

Contributions welcome! Please submit pull requests with:
- Clear description of changes
- Tests for new features
- Updated documentation

---

**Happy generating! 🎉**

*For questions or issues, open a GitHub issue or start a discussion.*
