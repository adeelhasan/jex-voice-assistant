# JEX Hosting & Deployment Plan

## Overview

This document outlines the strategy for making JEX easily distributable and self-hostable, including hardware requirements, hosting options, and deployment tiers.

---

## Goal: Fully Self-Contained Docker Setup

Package JEX into a Docker container with:
- n8n instance (workflow automation)
- Open source LLM (local inference)
- LiveKit server (optional, for full air-gap)
- Python agent
- Next.js frontend

**Target:** One-command deployment that runs entirely self-hosted.

---

## Feasibility Assessment

### ✅ Highly Feasible Components

**1. n8n Instance - Very Easy**
- Official Docker image: `n8nio/n8n`
- Can run entirely self-hosted
- All workflows and credentials can be bundled
- Zero external dependencies needed

**2. Open Source LLM - Feasible with Trade-offs**
- **Best Options:**
  - Ollama (easiest) - Llama 3.1, Mistral, etc.
  - LocalAI - OpenAI-compatible API
  - Text-generation-webui (Oobabooga)
- **Reality Check:**
  - Requires 8-16GB RAM for decent models
  - CPU inference is slow (5-10s); GPU highly recommended (1-2s)
  - Quality gap vs GPT-4o-mini (but improving rapidly)
  - Llama 3.1 8B or Mistral 7B are reasonable compromises

**3. Python Agent - Very Easy**
- Already containerizable
- Config.py already supports Ollama
- Minimal changes needed

**4. Next.js Frontend - Very Easy**
- Standard Node.js container
- Minimal dependencies

### ⚠️ Challenging Components

**LiveKit Server - Feasible but Complex**
- Open source with official Docker images
- **Challenges:**
  - TURN/STUN requirements for WebRTC across networks
  - Needs public IP or properly configured NAT
  - SSL certificates required for WebRTC in browsers
  - Resource intensive for real-time media processing
  - Complex networking (port forwarding, firewall rules)
- **Recommendation:** Make optional; users can choose cloud or self-hosted

**Speech-to-Text (STT)**
- Deepgram requires API (not self-hostable)
- **Alternatives:**
  - Whisper.cpp (OpenAI's Whisper running locally)
  - Vosk (lightweight, offline)
  - Coqui STT (open source)
- **Trade-off:** Slower, less accurate than Deepgram

**Text-to-Speech (TTS)**
- OpenAI TTS requires API
- **Alternatives:**
  - Coqui TTS (open source, decent quality)
  - Piper TTS (fast, lightweight)
  - XTTS (very good quality but slow)
- **Trade-off:** Voice quality not as natural

---

## Hardware Requirements

### Minimum Specs (Hybrid - Cloud APIs)
```
CPU:     2 cores
RAM:     4GB
Storage: 20GB
Network: Decent bandwidth for voice streaming

What runs locally:
- n8n: ~500MB RAM
- Python agent: ~500MB RAM
- Next.js: ~300MB RAM
- PostgreSQL: ~200MB RAM
Total: ~1.5GB + system overhead

Note: LLM/STT/TTS still use cloud APIs
```

### Realistic Specs (Local LLM - Small Models)
```
CPU:     4 cores minimum
RAM:     8-12GB (for Llama 3.1 8B or Mistral 7B)
Storage: 40GB SSD (model files are 4-7GB each)
GPU:     None required but VERY helpful

Breakdown:
- Ollama + Llama 3.1 8B: ~6-8GB RAM
- n8n: ~500MB
- Agent: ~500MB
- Frontend: ~300MB
- System: ~1GB
Total: ~8-10GB

Reality: CPU inference is SLOW (5-10 seconds per response)
```

### Comfortable Specs (Good Experience)
```
CPU:     6-8 cores
RAM:     16GB minimum, 32GB ideal
Storage: 60GB SSD
GPU:     NVIDIA GPU with 6GB+ VRAM (game changer)

With GPU:
- Response time: 1-2 seconds (vs 5-10 on CPU)
- Can run larger models (13B+)
- Better quality responses
```

---

## Hosting Options Comparison

### 🏠 Hostinger VPS

**Pros:**
- ✅ Cheap ($8-20/month for 8GB RAM)
- ✅ Root access for Docker
- ✅ Fixed pricing
- ✅ European data centers (good for privacy)

**Cons:**
- ❌ No GPU support
- ❌ CPU-only = slow LLM inference
- ❌ Shared CPU (noisy neighbors)
- ❌ Limited to smaller models

**Recommended Plan:**
- **VPS 2:** 8GB RAM, 4 cores, 200GB SSD (~$12/month)
  - Can run small LLM (Llama 3.1 8B)
  - Expect 5-10 second response times
  - Workable for personal use

---

### ☁️ AWS EC2

**Pros:**
- ✅ Wide range of instance types
- ✅ GPU instances available (g4dn, g5)
- ✅ Pay-as-you-go (can stop when not using)
- ✅ Better performance/scaling
- ✅ Spot instances = 70-90% cheaper

**Cons:**
- ❌ More expensive (on-demand)
- ❌ Complex pricing (can get expensive fast)
- ❌ Requires more AWS knowledge

**Recommended Options:**

**Option A - CPU Only (Budget):**
```
Instance: t3.xlarge
Specs:    4 vCPU, 16GB RAM
Price:    ~$120/month (on-demand)
          ~$75/month (1-year reserved)
          ~$10-15/month (spot instance, can be interrupted)

Good for: Testing, personal use with spot instances
```

**Option B - GPU (Best Performance):**
```
Instance: g4dn.xlarge
Specs:    4 vCPU, 16GB RAM, NVIDIA T4 GPU (16GB)
Price:    ~$380/month (on-demand)
          ~$240/month (1-year reserved)
          ~$120/month (spot instance)

Best for: Production use, fast responses
```

---

### 🌊 DigitalOcean

**Pros:**
- ✅ Simple pricing
- ✅ Good documentation
- ✅ GPU droplets available
- ✅ Better than Hostinger for compute

**Cons:**
- ❌ GPU instances expensive (~$700/month)
- ❌ More expensive than Hostinger for basic VPS

**Recommended Plan:**
```
CPU-Optimized: 8GB RAM, 4 vCPU
Price: ~$84/month
Better CPU than Hostinger, still no GPU
```

---

### 🎮 Vast.ai / RunPod (GPU Specialists)

**Pros:**
- ✅ Cheapest GPU access
- ✅ Purpose-built for AI workloads
- ✅ $0.20-0.50/hour for GPU instances
- ✅ Can pause/resume to save costs

**Cons:**
- ❌ Less polished than AWS
- ❌ Variable availability
- ❌ Not traditional hosting

**Example Pricing:**
```
RTX 3060 (12GB): ~$0.25/hour = ~$180/month
RTX 4090 (24GB): ~$0.60/hour = ~$430/month
(But you can stop it when not using!)
```

---

### 🏡 Self-Hosted (Your Own Hardware)

**Best if you have:**
- Spare desktop/laptop with 16GB+ RAM
- Raspberry Pi 5 (8GB) - can run tiny models
- Old gaming PC with GPU

**Pros:**
- ✅ Free hosting (aside from electricity)
- ✅ Full control
- ✅ No monthly fees
- ✅ Can use existing GPU

**Cons:**
- ❌ Power costs (~$5-10/month)
- ❌ Uptime management
- ❌ Network setup (port forwarding, SSL)

---

## Recommended Deployment Tiers

### Tier 1: "Just Get It Running" - Hostinger
```
Cost:       $12/month
Hardware:   8GB RAM, 4 cores
Config:     Hybrid (local n8n, cloud LLM/STT/TTS)
Experience: Good, requires API keys
Setup:      1 hour

Components:
- ✅ n8n (local)
- ✅ Agent (local)
- ✅ Frontend (local)
- ☁️ OpenAI LLM
- ☁️ Deepgram STT
- ☁️ OpenAI TTS
- ☁️ LiveKit Cloud
```

### Tier 2: "Local LLM" - AWS t3.xlarge Spot
```
Cost:       $10-15/month (spot) or $75/month (reserved)
Hardware:   16GB RAM, 4 cores
Config:     Local LLM (Ollama), cloud STT/TTS
Experience: Slower responses (5-10s) but private
Setup:      2 hours

Components:
- ✅ n8n (local)
- ✅ Ollama + Llama 3.1 8B (local)
- ✅ Agent (local)
- ✅ Frontend (local)
- ☁️ Deepgram STT
- ☁️ OpenAI TTS
- ☁️ LiveKit Cloud
```

### Tier 3: "Fast & Private" - AWS g4dn.xlarge Spot
```
Cost:       $120/month (spot) or $240/month (reserved)
Hardware:   16GB RAM, 4 cores, NVIDIA T4 GPU
Config:     Everything local including Whisper + Coqui
Experience: Fast (1-2s responses), fully private
Setup:      4 hours

Components:
- ✅ n8n (local)
- ✅ Ollama + Llama 3.1 8B/13B (local, GPU)
- ✅ Whisper.cpp (local STT)
- ✅ Coqui TTS (local)
- ✅ Agent (local)
- ✅ Frontend (local)
- ☁️ LiveKit Cloud (optional)
```

### Tier 4: "Home Lab" - Self-Hosted
```
Cost:       $0/month + electricity (~$5-10)
Hardware:   Your own machine (16GB+ RAM)
Config:     Everything local
Experience: Best control, no usage limits
Setup:      Half day (network setup)

Components:
- ✅ Everything local
- ✅ Optional LiveKit self-hosted
- ✅ Full air-gap capability
```

---

## Recommended Approach: Phased Implementation

### Phase 1: Hybrid (Easiest Distribution) ⭐ RECOMMENDED START
```yaml
Docker Compose Stack:
  - n8n (workflows)
  - Ollama (LLM) - optional, can use cloud
  - Python agent
  - Next.js frontend
  - PostgreSQL (for n8n persistence)

External Services:
  - LiveKit Cloud (free tier)
  - Deepgram STT (pay-per-use)
  - OpenAI TTS (pay-per-use)
  - OpenAI LLM (optional fallback)

Deployment:
  - One-command startup: docker-compose up -d
  - Pre-configured n8n workflows
  - Ollama model auto-downloaded (Llama 3.1 8B)
  - Template .env with cloud/local toggle

Benefits:
  - 80% self-hosted
  - Users choose cloud or local LLM
  - Easy to get working
  - Good enough for most users
```

### Phase 2: Mostly Self-Hosted
```yaml
Additions:
  - Whisper.cpp for local STT
  - Coqui TTS for local voice
  - LiveKit configuration guide

Trade-offs:
  - 95% self-hosted
  - Some quality reduction on STT/TTS
  - Still recommend LiveKit Cloud
```

### Phase 3: Fully Air-Gapped
```yaml
Complete Stack:
  - Everything including LiveKit server
  - Complex networking configuration
  - SSL certificate management
  - TURN/STUN setup

Target:
  - 100% self-hosted
  - Advanced users only
  - Enterprise/privacy-focused deployments
```

---

## Recommended Initial Setup

### Platform: AWS EC2 t3.xlarge Spot Instance

**Specifications:**
```
Instance:   t3.xlarge Spot
vCPU:       4 cores
RAM:        16GB
Storage:    60GB SSD
Cost:       $10-15/month (spot pricing in us-east-1)
Region:     us-east-1 (cheapest)
OS:         Ubuntu 22.04 LTS
```

**Configuration:**
```yaml
Local Components:
  - n8n
  - Ollama (Llama 3.1 8B)
  - Python agent
  - Next.js frontend
  - PostgreSQL

Cloud Components:
  - Deepgram (STT)
  - OpenAI TTS
  - LiveKit Cloud
```

**Why This Setup:**
- ✅ Cheap enough to experiment ($10-15/month)
- ✅ Enough RAM for decent LLM (8B models)
- ✅ Can upgrade to GPU later if needed
- ✅ Spot pricing = 90% cheaper than on-demand
- ✅ Easy auto-restart if interrupted
- ✅ Accept 5-10 second LLM response times (CPU inference)

**Setup Process:**
1. Launch EC2 t3.xlarge spot instance
2. Configure security group (ports 3000, 7880, 5678)
3. SSH in and clone repository
4. Run: `docker-compose up -d`
5. Ollama downloads model on first run (~5GB)
6. Total setup time: ~30 minutes

---

## Docker Architecture (Phase 1)

```yaml
# docker-compose.yml structure
version: '3.8'

services:
  # PostgreSQL for n8n
  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=n8n
      - POSTGRES_USER=n8n
      - POSTGRES_PASSWORD=n8n
    volumes:
      - postgres_data:/var/lib/postgresql/data

  # n8n - Workflow automation
  n8n:
    image: n8nio/n8n
    ports:
      - "5678:5678"
    environment:
      - DB_TYPE=postgresdb
      - DB_POSTGRESDB_HOST=postgres
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=admin
    volumes:
      - n8n_data:/home/node/.n8n
      - ./n8n-workflows:/import
    depends_on:
      - postgres

  # Ollama - Local LLM (optional)
  ollama:
    image: ollama/ollama
    ports:
      - "11434:11434"
    volumes:
      - ollama_models:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    # Uncomment for GPU support:
    # deploy:
    #   resources:
    #     reservations:
    #       devices:
    #         - driver: nvidia
    #           count: 1
    #           capabilities: [gpu]

  # Python Agent
  agent:
    build: ./agent
    environment:
      - LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
      - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
      - LLM_MODEL=${LLM_MODEL:-llama3.1:8b}
      - OLLAMA_BASE_URL=http://ollama:11434
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - DEEPGRAM_API_KEY=${DEEPGRAM_API_KEY}
      - N8N_WEBHOOK_BASE_URL=http://n8n:5678/webhook
      - N8N_API_KEY=${N8N_API_KEY}
    depends_on:
      - ollama
      - n8n

  # Next.js Frontend
  webapp:
    build: ./webapp
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_LIVEKIT_URL=${LIVEKIT_URL}
      - LIVEKIT_API_KEY=${LIVEKIT_API_KEY}
      - LIVEKIT_API_SECRET=${LIVEKIT_API_SECRET}
    depends_on:
      - agent

volumes:
  postgres_data:
  n8n_data:
  ollama_models:
```

---

## Component Breakdown

### Feasibility Matrix

| Component | Difficulty | Resource Cost | Status | Recommendation |
|-----------|-----------|---------------|--------|----------------|
| n8n | ⭐ Easy | Low | ✅ Ready | Bundle it |
| Local LLM (Ollama) | ⭐⭐⭐ Medium | High (8-16GB RAM) | ✅ Ready | Bundle with cloud fallback |
| Python Agent | ⭐ Easy | Low | ✅ Ready | Bundle it |
| Next.js Frontend | ⭐ Easy | Low | ✅ Ready | Bundle it |
| LiveKit Server | ⭐⭐⭐⭐ Hard | Medium | ⚠️ Complex | Make optional/cloud |
| STT (Deepgram) | N/A | API cost | ☁️ Cloud | Need Whisper.cpp alternative |
| TTS (OpenAI) | N/A | API cost | ☁️ Cloud | Need Coqui TTS alternative |
| PostgreSQL | ⭐ Easy | Low | ✅ Ready | Bundle it |

---

## Cost Comparison (Monthly)

| Tier | Platform | Specs | Cost | LLM Speed | Privacy |
|------|----------|-------|------|-----------|---------|
| 1 | Hostinger VPS 2 | 8GB, 4 cores | $12 | Cloud (fast) | Medium |
| 2 | AWS t3.xlarge Spot | 16GB, 4 cores | $10-15 | CPU (5-10s) | High |
| 2 | AWS t3.xlarge Reserved | 16GB, 4 cores | $75 | CPU (5-10s) | High |
| 3 | AWS g4dn.xlarge Spot | 16GB, GPU | $120 | GPU (1-2s) | Very High |
| 3 | AWS g4dn.xlarge Reserved | 16GB, GPU | $240 | GPU (1-2s) | Very High |
| 4 | Self-hosted | Your hardware | $5-10 | Varies | Complete |

---

## Next Steps (When Ready)

1. ✅ Create `docker-compose.yml` for Phase 1
2. ✅ Create Dockerfiles for agent and webapp
3. ✅ Add initialization scripts for:
   - Ollama model download
   - n8n workflow import
   - Database migrations
4. ✅ Create `.env.template` with all configuration options
5. ✅ Add deployment documentation
6. ✅ Create AWS/Hostinger setup guides
7. ✅ Add monitoring/logging setup
8. ⏸️ Phase 2: Add Whisper.cpp and Coqui TTS (later)
9. ⏸️ Phase 3: Add LiveKit server configuration (advanced)

---

## Notes

- **Current Focus:** Save this plan for later
- **Priority:** Return to feature development
- **Revisit:** When ready to package and distribute
- **Recommendation:** Start with AWS t3.xlarge Spot for best value/performance balance
