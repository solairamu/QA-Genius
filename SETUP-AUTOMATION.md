# 🚀 QA-Genius Automated Setup

This automated setup solves the Docker-in-Docker issues while providing complete automation for fresh GPU instances.

## ✨ **One-Command Setup**

For a **completely fresh GPU instance**, just run:

```bash
./setup-qa-genius.sh
```

This **single command** will:
- ✅ Install all system dependencies
- ✅ Install Python packages  
- ✅ Configure MySQL database
- ✅ Install and configure Ollama with Llama 3.1 8B
- ✅ Set up environment variables
- ✅ Create convenient aliases
- ✅ Start all services
- ✅ Test everything works
- ✅ Optimize for GPU acceleration

## 🎯 **Perfect for Virtual GPU Restarts**

When you **restart your virtual GPU** and get a fresh container:

1. **Copy your QA-Genius code** to the new instance
2. **Run one command**: `./setup-qa-genius.sh` 
3. **Done!** Everything is configured and running

No manual steps, no Docker issues, **complete automation**.

## 💡 **Convenient Commands**

After setup, you get these handy aliases:

```bash
qa-start    # Start QA-Genius (like docker-compose up)
qa-stop     # Stop QA-Genius (like docker-compose down)  
qa-status   # Check if services are running
qa-setup    # Re-run complete setup
```

## 🆚 **vs Docker Approach**

| Feature | Docker (Original) | Automated Script |
|---------|-------------------|------------------|
| **One-command setup** | ✅ `./deploy.sh` | ✅ `./setup-qa-genius.sh` |
| **Works in containers** | ❌ Docker-in-Docker issues | ✅ Always works |
| **GPU optimization** | ✅ | ✅ Better optimization |
| **Persistence** | ✅ Containers + volumes | ✅ Direct installation |
| **Fresh instance setup** | ❌ Need host machine | ✅ Works everywhere |

## 🎮 **Usage Examples**

### Fresh GPU Instance
```bash
# 1. Get your code
git clone <your-repo> QA-Genius
cd QA-Genius

# 2. One command setup  
./setup-qa-genius.sh

# 3. Access at http://localhost:8501
```

### Daily Usage
```bash
qa-start    # Start services
qa-status   # Check everything is running
qa-stop     # Stop when done
```

### Restart After Reboot
```bash
qa-start    # Everything is already installed, just start
```

## 🔧 **What Gets Installed**

- **System packages**: curl, wget, mysql-server, etc.
- **Python environment**: All requirements.txt packages
- **MySQL database**: Pre-configured with QA-Genius schema
- **Ollama**: Latest version with Llama 3.1 8B model
- **Environment**: All necessary environment variables
- **Aliases**: Convenient command shortcuts

## ⚡ **GPU Optimization**

The script automatically:
- ✅ Uses unquantized Llama 3.1 8B model
- ✅ Configures GPU acceleration  
- ✅ Optimizes for RTX 5090 performance
- ✅ Sets up proper CUDA integration

## 🚀 **Benefits Over Docker**

1. **No Docker-in-Docker issues**
2. **Works in any containerized environment**
3. **Better GPU integration**
4. **Faster startup (no container overhead)**
5. **Easier debugging and customization**
6. **Same automation level as Docker**

## 📋 **Requirements**

- Ubuntu/Debian-based system (any container)
- Root access (typical in GPU containers)
- Internet connection
- NVIDIA GPU with drivers

This approach gives you **all the automation benefits of Docker** without any of the containerization complexity! 