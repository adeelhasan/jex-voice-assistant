# JEX Hosting & Distribution Plan

## 1. Core Goal: The Private "JEX Appliance"

The primary goal is to package the entire JEX application into a secure, private, single-tenant "appliance." This package should be easy for a user to deploy on a single server, giving them total control and privacy over their data and conversations.

Our philosophy is **privacy-first**, achieved through self-hosting and a security-conscious architecture.

---

## 2. Recommended Architecture: Docker Compose

To achieve this, we will use **Docker Compose**. This is the industry-standard tool for running multi-container applications on a single host machine. It allows us to define all the services JEX needs in one file and manage them with a single command.

This approach is vastly superior to building a single, monolithic Docker image, as it provides isolation, better resource management, and easier maintenance.

The application will be composed of the following services running in separate containers:

*   **`jex-webapp`**: The Next.js user interface.
*   **`jex-agent`**: The core Python agent.
*   **`n8n`**: The workflow automation engine.
*   **`ollama`**: For running the self-hosted LLM.
*   **`livekit`**: The real-time voice server.
*   **`redis`**: A required dependency for the LiveKit server.

#### Example `docker-compose.yml` Structure:

```yaml
version: '3.8'

services:
  webapp:
    build: ./webapp
    ports:
      - "3000:3000"
    # ...

  agent:
    build: ./agent
    # No ports exposed; internal only
    # ...

  n8n:
    image: n8nio/n8n
    # No ports exposed by default; accessed via SSH tunnel
    # ...

  livekit:
    image: livekit/livekit-server:latest
    ports:
      - "7880:7880" # Required for client connection
      # ... plus UDP ports for media
    # ...

  redis:
    image: redis:7-alpine
    # No ports exposed; internal only
    # ...

  ollama:
    image: ollama/ollama
    # No ports exposed; internal only
    # ...
```

---

## 3. The "Appliance" Security Model

This architecture is designed to minimize exposure to the public internet. We achieve this with three layers of security.

#### Layer 1: Inbound Connections (The Cloud Firewall)
The cloud provider's firewall is our first line of defense. It controls what traffic from the internet can reach our server.

*   **Publicly Open Ports:**
    *   `webapp` (Port 3000): Must be open so users can access the web interface.
    *   `livekit` (Port 7880 + a UDP range): Must be open so the user's browser can establish a voice connection.
*   **Private Admin Ports:**
    *   `n8n` (Port 5678): Should **NOT** be exposed to the public. It will be accessed securely via an **SSH Tunnel**, making the admin panel accessible on the developer's local machine without opening a public port.

#### Layer 2: Internal Connections (The Private Docker Network)
Services that only need to talk to each other will not have a `ports` mapping in Docker Compose. They are invisible to the internet.

*   **Internal-Only Services:** `agent`, `ollama`, `redis`.
*   **Communication:** They communicate freely and securely over the private network created by Docker Compose (e.g., the `agent` connects to `http://ollama:11434`).

#### Layer 3: Outbound Connections (To External APIs)
Connections from our server *out* to services like Deepgram or OpenAI are handled differently.

*   **No Firewall Rules Needed:** Outgoing traffic is allowed by default on all servers.
*   **Security:** These connections are secured using **HTTPS**, which encrypts the traffic (including your API keys) between your agent and the third-party service.

---

## 4. Recommended Hosting & Hardware

To run the full, private JEX appliance with a local LLM, a powerful server is required. The LLM is the most demanding component.

#### Hardware Requirements:
*   **GPU (Critical for Performance):** A modern NVIDIA GPU with at least **16-24GB of VRAM** (e.g., RTX 3090, RTX 4090, A100). This is the difference between a 1-2 second response time and a 10-20 second response time.
*   **System RAM:** **32GB minimum** to comfortably run the LLM and all other services.
*   **CPU & Storage:** A modern multi-core CPU and a fast SSD (at least 100GB).

#### Recommended Hosting Provider for Testing:
For testing performance and usability, a specialized GPU cloud provider is the best choice due to simplicity and cost-effectiveness.

*   **Primary Recommendation:** **RunPod** (or Lambda Labs, Vast.ai)
*   **Why:** They offer simple, on-demand access to powerful GPUs at a lower cost than major clouds. Their platforms are Docker-native and designed for this exact use case. The ability to "pause" the instance makes them very cost-effective for experimentation.

---

## 5. The Path Forward & Key Decisions

This plan provides a clear architectural blueprint. Before final implementation, the following strategic decisions need to be made.

#### Deployment Workflow Summary:
A user's deployment process would be:
1.  Rent a suitable GPU server from a provider like RunPod.
2.  Connect via SSH and clone the JEX repository.
3.  Configure the `.env` file with any necessary API keys.
4.  Run `docker-compose up -d`.
5.  Access the web UI and start using their private JEX instance.

#### Key Decisions to be Made:
1.  **Default Components (Local vs. Cloud):**
    *   Should the default setup use the local `ollama` LLM, or should it be configured to use a cloud service like OpenAI out-of-the-box?
    *   **Decision:** We should default to a local LLM to align with the privacy-first philosophy, but allow easy configuration to switch to a cloud provider via the `.env` file.

2.  **Default Local Models:**
    *   Which specific models should be the default for a local setup? This is a trade-off between performance and resource requirements.
    *   **Decision:** We should choose a strong but efficient model as the default (e.g., `Llama-3.1-8B-Instruct`) and document how to switch to larger or smaller models. The same decision is needed for local STT (e.g., Whisper) and TTS (e.g., Piper).

3.  **LiveKit Configuration:**
    *   Should the default `docker-compose.yml` include the self-hosted LiveKit server, or assume the user will start with the free tier of LiveKit Cloud?
    *   **Decision:** For maximum ease of use, the default should rely on **LiveKit Cloud**. We can provide a separate, advanced `docker-compose.livekit.yml` file for users who want to take the extra step of self-hosting the voice infrastructure.

---

## 6. Future Scaling: Kubernetes

It's important to distinguish this single-host plan from a large-scale production system.

*   **Docker Compose:** Is perfect for managing all of JEX's services on a **single server**.
*   **Kubernetes:** Is an orchestration service for deploying and managing applications across a **cluster of multiple servers**.

We would only need to migrate from Docker Compose to Kubernetes if JEX evolved into a multi-tenant SaaS application requiring high availability, fault tolerance, and auto-scaling across many machines. For the private appliance model, Docker Compose remains the right tool for the job.