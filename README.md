# QA-Genius Automated Setup

## **One-Command Setup**

Just run:

```bash
./setup-qa-genius.sh
```

This **single command** will:
- ✅ Install all system dependencies
- ✅ Install Python packages  
- ✅ Configure MySQL database
- ✅ Install and configure Ollama with selected LLM model
- ✅ Set up environment variables
- ✅ Create convenient aliases
- ✅ Start all services
- ✅ Test everything works
- ✅ Optimize for GPU acceleration

## **Virtual GPU**

When you **start a virtual GPU** and get a fresh container:

1. **Copy your QA-Genius code** to the new instance
2. **Run one command**: `./setup-qa-genius.sh` 
3. **Done!** Everything is configured and running

## **Convenient Commands**

After setup, you can use these commands:

```bash
qa-start    # Start QA-Genius
qa-stop     # Stop QA-Genius
qa-status   # Check if services are running
qa-setup    # Re-run complete setup
```

## **Usage Examples**

### Fresh GPU Instance
```bash
# 1. Get your code
git clone <your-repo> QA-Genius
cd QA-Genius

# 2. One command setup  
./setup-qa-genius.sh

# 3. Access at http://localhost:8501
```
## **What Gets Installed**

- **System packages**: curl, wget, mysql-server, etc.
- **Python environment**: All requirements.txt packages
- **MySQL database**: Pre-configured with QA-Genius schema
- **Ollama**: Latest version with desired model
- **Environment**: All necessary environment variables
- **Aliases**: Convenient command shortcuts