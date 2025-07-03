#!/bin/bash

# QA-Genius Complete Automation Setup Script
# This script completely sets up QA-Genius from scratch in any fresh environment
# Usage: ./setup-qa-genius.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Get the MODEL_NAME from llm_wrapper.py
get_model_name() {
    local model_name=""
    if [ -f "llm/llm_wrapper.py" ]; then
        # Extract MODEL_NAME from Python file using awk for better reliability
        model_name=$(grep -E '^MODEL_NAME\s*=' llm/llm_wrapper.py | awk -F'"' '{print $2}')
        if [[ -n "$model_name" && "$model_name" != "MODEL_NAME"* ]]; then
            echo "$model_name"
            return 0
        fi
    fi
    
    # Fallback to default if not found
    print_warning "Could not read MODEL_NAME from llm/llm_wrapper.py, using default"
    echo "mistral:7b-instruct-q4_0"
    return 1
}

# Setup Python and pip commands globally
setup_python_commands() {
    print_info "Setting up Python and pip commands..."
    
    # Determine the correct Python command
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        print_error "No Python installation found"
        print_error "Please install Python 3 first"
        exit 1
    fi
    
    # Determine the correct pip command
    if command -v pip3 &> /dev/null; then
        PIP_CMD="pip3"
    elif $PYTHON_CMD -m pip --version &> /dev/null; then
        PIP_CMD="$PYTHON_CMD -m pip"
    elif command -v pip &> /dev/null; then
        PIP_CMD="pip"
    else
        print_error "No pip installation found"
        print_error "Please install pip first"
        exit 1
    fi
    
    # Export for use in other functions
    export PYTHON_CMD
    export PIP_CMD
    
    print_info "Using Python: $PYTHON_CMD ($(${PYTHON_CMD} --version))"
    print_info "Using pip: $PIP_CMD"
}

# Detect operating system
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            OS_TYPE="debian"
        elif command -v yum &> /dev/null; then
            OS_TYPE="redhat"
        elif command -v dnf &> /dev/null; then
            OS_TYPE="fedora"
        elif command -v pacman &> /dev/null; then
            OS_TYPE="arch"
        elif command -v zypper &> /dev/null; then
            OS_TYPE="suse"
        else
            OS_TYPE="linux-unknown"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        OS_TYPE="macos"
        
        # Quick fix for common homebrew issues
        if command -v brew &> /dev/null; then
            # Remove problematic taps that cause update failures
            brew untap homebrew/homebrew-cask-versions 2>/dev/null || true
            brew untap homebrew/cask-versions 2>/dev/null || true
        fi
    elif [[ "$OSTYPE" == "cygwin" ]] || [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
        # Windows
        OS_TYPE="windows"
    else
        OS_TYPE="unknown"
    fi
    
    print_info "Detected OS: $OS_TYPE"
}

# Install packages based on OS
install_package() {
    local package_name="$1"
    
    case $OS_TYPE in
        "debian")
            apt-get install -y "$package_name"
            ;;
        "redhat")
            yum install -y "$package_name"
            ;;
        "fedora")
            dnf install -y "$package_name"
            ;;
        "arch")
            pacman -S --noconfirm "$package_name"
            ;;
        "suse")
            zypper install -y "$package_name"
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                # Check if already installed first
                if brew list "$package_name" &> /dev/null; then
                    print_info "$package_name is already installed"
                else
                    brew install "$package_name" 2>/dev/null || {
                        print_warning "Failed to install $package_name via brew, trying alternative..."
                        # Try alternative names for some packages
                        case "$package_name" in
                            "mysql-client")
                                brew install mysql || print_warning "Could not install MySQL client"
                                ;;
                            *)
                                print_warning "Could not install $package_name"
                                ;;
                        esac
                    }
                fi
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
                exit 1
            fi
            ;;
        *)
            print_error "Unsupported OS: $OS_TYPE"
            print_error "Please install the following manually: $package_name"
            exit 1
            ;;
    esac
}

# Update package manager
update_packages() {
    case $OS_TYPE in
        "debian")
            apt-get update -qq
            ;;
        "redhat")
            yum update -y
            ;;
        "fedora")
            dnf update -y
            ;;
        "arch")
            pacman -Sy
            ;;
        "suse")
            zypper refresh
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                print_info "Updating Homebrew (this may take a moment)..."
                # Clean up any stale taps first
                brew cleanup 2>/dev/null || true
                brew untap homebrew/homebrew-cask-versions 2>/dev/null || true
                brew untap homebrew/cask-versions 2>/dev/null || true
                
                # Try to update, but don't fail if it has issues
                if ! brew update 2>/dev/null; then
                    print_warning "Homebrew update had some issues, but continuing..."
                    # Try to fix common issues
                    brew doctor --list-checks | grep -v check_for_link_up_keg_only_uses | xargs brew doctor 2>/dev/null || true
                fi
            else
                print_error "Homebrew not found. Please install Homebrew first: https://brew.sh/"
                exit 1
            fi
            ;;
        *)
            print_warning "Cannot update packages for OS: $OS_TYPE"
            ;;
    esac
}

print_header() {
    echo -e "${GREEN}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│                                                         │" 
    echo "│              🧠 QA-Genius Auto Setup 🧠               │"
    echo "│                                                         │"
    echo "│         Complete automated setup for fresh GPU         │"
    echo "│                                                         │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

# Check if script is run from QA-Genius directory
check_directory() {
    if [ ! -f "app.py" ] || [ ! -f "requirements.txt" ]; then
        print_error "Please run this script from the QA-Genius directory"
        print_error "Current directory: $(pwd)"
        exit 1
    fi
    print_success "✅ Running from QA-Genius directory"
}

# Install system dependencies
install_system_deps() {
    print_info "🔧 Installing system dependencies..."
    
    # Update package list
    update_packages
    
    # Install essential packages based on OS
    case $OS_TYPE in
        "debian")
            install_package "python3-pip"
            install_package "curl"
            install_package "wget"
            install_package "gnupg"
            install_package "software-properties-common"
            install_package "mysql-client"
            ;;
        "redhat"|"fedora")
            install_package "python3-pip"
            install_package "curl"
            install_package "wget"
            install_package "gnupg2"
            install_package "mysql"
            ;;
        "arch")
            install_package "python-pip"
            install_package "curl"
            install_package "wget"
            install_package "gnupg"
            install_package "mysql-clients"
            ;;
        "macos")
            # Check if Python 3 is installed
            if ! command -v python3 &> /dev/null; then
                print_info "Installing Python 3..."
                install_package "python@3.11" || install_package "python3" || install_package "python"
            else
                print_info "Python 3 is already installed: $(python3 --version)"
            fi
            
            # Install other dependencies
            install_package "curl"
            install_package "wget"
            install_package "mysql-client"
            
            # Install pip if not available
            if ! command -v pip3 &> /dev/null && ! python3 -m pip --version &> /dev/null; then
                print_info "Installing pip..."
                python3 -m ensurepip --upgrade 2>/dev/null || {
                    curl https://bootstrap.pypa.io/get-pip.py | python3 - || {
                        print_warning "Could not install pip automatically. Please install pip manually."
                    }
                }
            else
                print_info "pip is already available"
            fi
            ;;
        *)
            print_warning "Please install manually: python3-pip, curl, wget, mysql-client"
            ;;
    esac
    
    print_success "✅ System dependencies installed"
}

# Install Python dependencies
install_python_deps() {
    print_info "🐍 Installing Python dependencies..."
    
    # Upgrade pip
    print_info "Upgrading pip..."
    $PIP_CMD install --upgrade pip --user 2>/dev/null || $PIP_CMD install --upgrade pip
    
    # Install requirements with explicit error checking
    print_info "Installing requirements from requirements.txt..."
    if $PIP_CMD install -r requirements.txt --user 2>/dev/null || $PIP_CMD install -r requirements.txt; then
        print_success "✅ Requirements installed successfully"
    else
        print_error "Failed to install requirements, trying individual packages..."
        # Try installing each package individually
        while IFS= read -r package; do
            if [[ ! -z "$package" && ! "$package" =~ ^[[:space:]]*# ]]; then
                print_info "Installing $package..."
                $PIP_CMD install "$package" --user 2>/dev/null || $PIP_CMD install "$package" || print_warning "Failed to install $package"
            fi
        done < requirements.txt
    fi
    
    # Verify critical packages are installed
    print_info "Verifying critical packages..."
    
    # Test each critical import
    critical_packages=("mysql.connector" "yaml" "streamlit" "pandas" "ollama" "openpyxl")
    for pkg in "${critical_packages[@]}"; do
        if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
            print_success "✅ $pkg is available"
        else
            print_error "❌ $pkg is not available"
            # Try to install the package based on common mappings
            case $pkg in
                "mysql.connector")
                    print_info "Attempting to install mysql-connector-python..."
                    $PIP_CMD install mysql-connector-python --user 2>/dev/null || $PIP_CMD install mysql-connector-python
                    ;;
                "yaml")
                    print_info "Attempting to install PyYAML..."
                    $PIP_CMD install PyYAML --user 2>/dev/null || $PIP_CMD install PyYAML
                    ;;
                *)
                    print_info "Attempting to install $pkg..."
                    $PIP_CMD install "$pkg" --user 2>/dev/null || $PIP_CMD install "$pkg"
                    ;;
            esac
            
            # Test again after installation attempt
            if $PYTHON_CMD -c "import $pkg" 2>/dev/null; then
                print_success "✅ $pkg is now available"
            else
                print_warning "⚠️  $pkg may still not be available"
            fi
        fi
    done
    
    print_success "✅ Python dependencies setup completed"
}

# Verify all critical modules are available
verify_all_modules() {
    print_info "🔍 Final verification of all required modules..."
    
    # All required modules for QA-Genius
    required_modules=(
        "mysql.connector"
        "yaml" 
        "streamlit"
        "pandas"
        "ollama"
        "openpyxl"
    )
    
    local all_good=true
    
    for module in "${required_modules[@]}"; do
        if $PYTHON_CMD -c "import $module" 2>/dev/null; then
            print_success "✅ $module"
        else
            print_error "❌ $module - MISSING"
            all_good=false
        fi
    done
    
    if [[ "$all_good" == "true" ]]; then
        print_success "🎉 All required modules are available!"
        return 0
    else
        print_error "❌ Some required modules are missing. Installing missing modules..."
        
        # Try to install missing modules
        for module in "${required_modules[@]}"; do
            if ! $PYTHON_CMD -c "import $module" 2>/dev/null; then
                case $module in
                    "mysql.connector")
                        $PIP_CMD install mysql-connector-python --user 2>/dev/null || $PIP_CMD install mysql-connector-python
                        ;;
                    "yaml")
                        $PIP_CMD install PyYAML --user 2>/dev/null || $PIP_CMD install PyYAML
                        ;;
                    *)
                        $PIP_CMD install "$module" --user 2>/dev/null || $PIP_CMD install "$module"
                        ;;
                esac
            fi
        done
        
        # Final check
        local final_check=true
        for module in "${required_modules[@]}"; do
            if ! $PYTHON_CMD -c "import $module" 2>/dev/null; then
                print_error "❌ Still missing: $module"
                final_check=false
            fi
        done
        
        if [[ "$final_check" == "true" ]]; then
            print_success "🎉 All modules are now available!"
            return 0
        else
            print_error "❌ Could not install all required modules."
            print_error "Please manually install missing modules using: $PIP_CMD install <module_name>"
            return 1
        fi
    fi
}

# Setup MySQL if not running
setup_mysql() {
    print_info "🗄️  Setting up MySQL database..."
    
    # Install MySQL server based on OS
    case $OS_TYPE in
        "debian")
            if ! dpkg -l | grep -q "mysql-server"; then
                print_info "Installing MySQL server..."
                DEBIAN_FRONTEND=noninteractive install_package "mysql-server"
            fi
            # Start MySQL service
            service mysql start || systemctl start mysql
            ;;
        "redhat"|"fedora")
            if ! rpm -qa | grep -q "mysql-server\|mariadb-server"; then
                print_info "Installing MySQL/MariaDB server..."
                install_package "mariadb-server"
            fi
            # Start MySQL/MariaDB service
            systemctl start mariadb || service mariadb start
            systemctl enable mariadb || true
            ;;
        "arch")
            if ! pacman -Qi mariadb &> /dev/null; then
                print_info "Installing MariaDB server..."
                install_package "mariadb"
            fi
            # Initialize and start MariaDB
            mysql_install_db --user=mysql --basedir=/usr --datadir=/var/lib/mysql &> /dev/null || true
            systemctl start mariadb
            systemctl enable mariadb
            ;;
        "macos")
            if ! brew list mysql &> /dev/null; then
                print_info "Installing MySQL server..."
                install_package "mysql"
            fi
            # Start MySQL service
            brew services start mysql
            ;;
        *)
            print_warning "MySQL installation not automated for $OS_TYPE"
            print_warning "Please install MySQL server manually"
            return 1
            ;;
    esac
    
    # Wait for MySQL to be ready
    sleep 3
    
    # Check if MySQL is configured with our password
    if ! mysqladmin ping -h localhost -u root -pKdata@2025 --silent 2>/dev/null; then
        print_info "Configuring MySQL root password..."
        
        case $OS_TYPE in
            "debian")
                # Use sudo to connect as root initially (auth_socket plugin)
                sudo mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Kdata@2025';" 2>/dev/null || \
                mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY 'Kdata@2025';" 2>/dev/null || \
                mysql -u root -e "SET PASSWORD FOR 'root'@'localhost' = PASSWORD('Kdata@2025');" 2>/dev/null || true
                ;;
            "macos"|"redhat"|"fedora"|"arch")
                # Try different methods to set password
                mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY 'Kdata@2025';" 2>/dev/null || \
                mysql -u root -e "SET PASSWORD FOR 'root'@'localhost' = PASSWORD('Kdata@2025');" 2>/dev/null || \
                mysqladmin -u root password 'Kdata@2025' 2>/dev/null || true
                ;;
        esac
        
        # Flush privileges
        mysql -u root -pKdata@2025 -e "FLUSH PRIVILEGES;" 2>/dev/null || \
        mysql -u root -e "FLUSH PRIVILEGES;" 2>/dev/null || true
        
        print_success "✅ MySQL password configured"
    fi
    
    print_success "✅ MySQL is running and configured"
    
    # Verify Python dependencies before database initialization
    print_info "Verifying database dependencies..."
    
    # Test database dependencies
    if ! $PYTHON_CMD -c "import mysql.connector" 2>/dev/null; then
        print_error "mysql.connector not available. Attempting to install..."
        
        $PIP_CMD install mysql-connector-python --user 2>/dev/null || $PIP_CMD install mysql-connector-python
        
        # Test again
        if ! $PYTHON_CMD -c "import mysql.connector" 2>/dev/null; then
            print_error "Failed to install mysql.connector. Please install manually: $PIP_CMD install mysql-connector-python"
            exit 1
        fi
    fi
    
    # Create database and tables
    print_info "Initializing database..."
    if $PYTHON_CMD -c "
import sys
sys.path.append('.')
try:
    from database.db_utils import initialize_database
    initialize_database()
    print('Database initialized successfully')
except ImportError as e:
    print(f'Import error: {e}')
    sys.exit(1)
except Exception as e:
    print(f'Database initialization error: {e}')
    sys.exit(1)
"; then
        print_success "✅ Database initialized successfully"
    else
        print_error "Failed to initialize database. Please check your Python dependencies."
        print_info "You can try running: $PIP_CMD install -r requirements.txt"
        exit 1
    fi
}

# Install and setup Ollama
setup_ollama() {
    print_info "🤖 Setting up Ollama..."
    
    # Install Ollama if not present
    if ! command -v ollama &> /dev/null; then
        print_info "Installing Ollama..."
        curl -fsSL https://ollama.ai/install.sh | sh
        print_success "✅ Ollama installed"
    else
        print_success "✅ Ollama already installed"
    fi
    
    # Start Ollama service with GPU acceleration
    print_info "Starting Ollama service with GPU acceleration..."
    export OLLAMA_GPU_LAYERS=999
    ollama serve &
    OLLAMA_PID=$!
    sleep 5
    
    # Get the model name from llm_wrapper.py
    MODEL_NAME=$(get_model_name)
    print_info "Using model: $MODEL_NAME"
    
    # Check if the configured model is available
    if ! ollama list | grep -q "$MODEL_NAME"; then
        print_info "Downloading model '$MODEL_NAME' (this may take several minutes)..."
        ollama pull "$MODEL_NAME"
        print_success "✅ Model '$MODEL_NAME' downloaded"
    else
        print_success "✅ Model '$MODEL_NAME' already available"
    fi
}

# Setup environment variables
setup_environment() {
    print_info "⚙️  Setting up environment..."
    
    # Create .env file if it doesn't exist
    if [ ! -f ".env" ]; then
        cp env.example .env
        print_success "✅ Environment file created"
    fi
    
    # Export environment variables
    export DB_HOST=localhost
    export DB_USER=root
    export DB_PASSWORD=Kdata@2025
    export DB_NAME=qa_genius
    export DB_ROOT_PASSWORD=Kdata@2025
    
    print_success "✅ Environment configured"
}

# Setup bash aliases permanently
setup_aliases() {
    print_info "🔗 Setting up command aliases..."
    
    # Get current directory
    CURRENT_DIR=$(pwd)
    
    # Determine shell config file
    if [[ "$OS_TYPE" == "macos" ]]; then
        SHELL_CONFIG="$HOME/.zshrc"
        # Also add to .bash_profile for compatibility
        SHELL_CONFIG2="$HOME/.bash_profile"
    else
        SHELL_CONFIG="$HOME/.bashrc"
    fi
    
    # Remove existing aliases to avoid duplicates
    sed -i '/alias qa-/d' "$SHELL_CONFIG" 2>/dev/null || true
    if [[ -n "$SHELL_CONFIG2" ]]; then
        sed -i '/alias qa-/d' "$SHELL_CONFIG2" 2>/dev/null || true
    fi
    
    # Add new aliases
    cat >> "$SHELL_CONFIG" << EOF

# QA-Genius aliases
alias qa-start="cd $CURRENT_DIR && export DB_HOST=localhost && export DB_USER=root && export DB_PASSWORD=Kdata@2025 && export DB_NAME=qa_genius && export DB_ROOT_PASSWORD=Kdata@2025 && export OLLAMA_GPU_LAYERS=999 && (pgrep -f 'ollama serve' > /dev/null || ollama serve &) && sleep 3 && python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &"
alias qa-stop="echo '🛑 Stopping QA-Genius services...'; pkill -f streamlit 2>/dev/null || true; pkill -f 'streamlit run' 2>/dev/null || true; pkill -f app.py 2>/dev/null || true; echo '  ✅ Streamlit stopped'; pkill -f 'ollama serve' 2>/dev/null || true; killall ollama 2>/dev/null || true; osascript -e 'quit app \"Ollama\"' 2>/dev/null || true; echo '  ✅ Ollama stopped'; echo '🎯 All QA-Genius services stopped'"
alias qa-status="echo \"🔍 Checking QA-Genius status...\"; ps aux | grep -E \"(streamlit|ollama)\" | grep -v grep; echo; echo \"📱 Streamlit:\"; curl -s http://localhost:8501 | grep -o \"<title>.*</title>\" || echo \"Not responding\"; echo \"🤖 Ollama:\"; curl -s http://localhost:11434/api/tags | head -c 50 || echo \"Not responding\""
alias qa-setup="$CURRENT_DIR/setup-qa-genius.sh"
EOF

    # Add to second config file if it exists (macOS)
    if [[ -n "$SHELL_CONFIG2" ]]; then
        cat >> "$SHELL_CONFIG2" << EOF

# QA-Genius aliases
alias qa-start="cd $CURRENT_DIR && export DB_HOST=localhost && export DB_USER=root && export DB_PASSWORD=Kdata@2025 && export DB_NAME=qa_genius && export DB_ROOT_PASSWORD=Kdata@2025 && export OLLAMA_GPU_LAYERS=999 && (pgrep -f 'ollama serve' > /dev/null || ollama serve &) && sleep 3 && python3 -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &"
alias qa-stop="echo '🛑 Stopping QA-Genius services...'; pkill -f streamlit 2>/dev/null || true; pkill -f 'streamlit run' 2>/dev/null || true; pkill -f app.py 2>/dev/null || true; echo '  ✅ Streamlit stopped'; pkill -f 'ollama serve' 2>/dev/null || true; killall ollama 2>/dev/null || true; osascript -e 'quit app \"Ollama\"' 2>/dev/null || true; echo '  ✅ Ollama stopped'; echo '🎯 All QA-Genius services stopped'"
alias qa-status="echo \"🔍 Checking QA-Genius status...\"; ps aux | grep -E \"(streamlit|ollama)\" | grep -v grep; echo; echo \"📱 Streamlit:\"; curl -s http://localhost:8501 | grep -o \"<title>.*</title>\" || echo \"Not responding\"; echo \"🤖 Ollama:\"; curl -s http://localhost:11434/api/tags | head -c 50 || echo \"Not responding\""
alias qa-setup="$CURRENT_DIR/setup-qa-genius.sh"
EOF
    fi
    
    print_success "✅ Aliases configured (qa-start, qa-stop, qa-status, qa-setup)"
    print_info "Aliases added to $SHELL_CONFIG"
}

# Start services
start_services() {
    print_info "🚀 Starting QA-Genius services..."
    
    # Stop any existing Streamlit services (but leave Ollama running if it was already running)
    print_info "Stopping any existing Streamlit services..."
    pkill -f streamlit 2>/dev/null || true
    sleep 2
    
    # Set environment and start services
    export DB_HOST=localhost
    export DB_USER=root
    export DB_PASSWORD=Kdata@2025
    export DB_NAME=qa_genius
    export DB_ROOT_PASSWORD=Kdata@2025
    
    # Start Ollama with GPU acceleration (if not already running)
    export OLLAMA_GPU_LAYERS=999
    if ! pgrep -f "ollama serve" > /dev/null; then
        print_info "Starting Ollama service..."
        ollama serve &
        sleep 5
    else
        print_info "Ollama is already running"
    fi
    
    # Start Streamlit (use python -m streamlit for better compatibility)
    print_info "Starting Streamlit application..."
    $PYTHON_CMD -m streamlit run app.py --server.port 8501 --server.address 0.0.0.0 &
    sleep 3
    
    print_success "✅ Services started successfully"
}

# Test the setup
test_setup() {
    print_info "🧪 Testing the setup..."
    
    # Test Streamlit
    print_info "Testing Streamlit connection..."
    if curl -s http://localhost:8501 | grep -q "Streamlit"; then
        print_success "✅ Streamlit is responding"
    else
        print_error "❌ Streamlit test failed"
        print_info "Checking if Streamlit process is running..."
        if pgrep -f "streamlit" > /dev/null; then
            print_info "Streamlit process is running but not responding on port 8501"
        else
            print_info "No Streamlit process found running"
        fi
        return 1
    fi
    
    # Test Ollama
    MODEL_NAME=$(get_model_name)
    if curl -s http://localhost:11434/api/tags | grep -q "$MODEL_NAME"; then
        print_success "✅ Ollama is responding with configured model: $MODEL_NAME"
    else
        print_error "❌ Ollama test failed - model '$MODEL_NAME' not found"
        print_info "Available models:"
        curl -s http://localhost:11434/api/tags | head -c 200 || echo "Could not list models"
        return 1
    fi
    
    # Test database
    if $PYTHON_CMD -c "
import sys
sys.path.append('.')
try:
    from database.db_utils import get_connection
    conn = get_connection()
    print('DB OK' if conn else 'DB Failed')
except Exception as e:
    print('DB Failed')
    sys.exit(1)
" | grep -q "DB OK"; then
        print_success "✅ Database is accessible"
    else
        print_error "❌ Database test failed"
        return 1
    fi
    
    print_success "🎉 All tests passed!"
}

# Show final instructions
show_final_info() {
    echo -e "${GREEN}"
    echo "┌─────────────────────────────────────────────────────────┐"
    echo "│                                                         │"
    echo "│                   🎉 SETUP COMPLETE! 🎉                │"
    echo "│                                                         │"
    echo "│  Your QA-Genius is now running and ready to use!       │"
    echo "│                                                         │"
    echo "│  📱 Web Interface: http://localhost:8501               │"
    echo "│  🤖 Ollama API:    http://localhost:11434              │"
    echo "│                                                         │"
    echo "│  💡 Useful Commands:                                    │"
    echo "│     qa-start   - Start the application                 │"
    echo "│     qa-stop    - Stop the application                  │"
    echo "│     qa-status  - Check service status                  │"
    echo "│     qa-setup   - Run this setup again                  │"
    echo "│                                                         │"
    MODEL_NAME=$(get_model_name)
    echo "│  ⚡ AI Model: $MODEL_NAME (GPU accelerated)              │"
    echo "│                                                         │"
    echo "└─────────────────────────────────────────────────────────┘"
    echo -e "${NC}"
}

# Robust stop function for QA-Genius services
stop_qa_services() {
    echo "🛑 Stopping QA-Genius services..."
    
    # Stop Streamlit with multiple methods
    echo "  📱 Stopping Streamlit..."
    pkill -f streamlit 2>/dev/null || true
    pkill -f 'streamlit run' 2>/dev/null || true
    pkill -f app.py 2>/dev/null || true
    pkill -f 'python.*streamlit' 2>/dev/null || true
    
    # Give it a moment
    sleep 1
    
    # Check if Streamlit is actually stopped
    if ! pgrep -f streamlit > /dev/null; then
        echo "    ✅ Streamlit stopped"
    else
        echo "    ⚠️  Some Streamlit processes may still be running"
    fi
    
    # Stop Ollama with multiple methods
    echo "  🤖 Stopping Ollama..."
    pkill -f 'ollama serve' 2>/dev/null || true
    killall ollama 2>/dev/null || true
    osascript -e 'quit app "Ollama"' 2>/dev/null || true
    
    # Give it a moment
    sleep 1
    
    # Check if Ollama serve is actually stopped
    if ! pgrep -f 'ollama serve' > /dev/null; then
        echo "    ✅ Ollama serve stopped"
    else
        echo "    ⚠️  Some Ollama processes may still be running"
    fi
    
    echo "🎯 QA-Genius stop command completed"
}

# Main execution
main() {
    print_header
    
    print_info "Starting complete QA-Genius setup..."
    
    # Detect operating system first
    detect_os
    
    # Setup Python commands early
    setup_python_commands
    
    check_directory
    install_system_deps
    install_python_deps
    verify_all_modules
    setup_mysql
    setup_ollama
    setup_environment
    setup_aliases
    start_services
    test_setup
    
    show_final_info
    
    print_success "🚀 Setup completed successfully!"
    print_info "You can now access QA-Genius at http://localhost:8501"
    
    # Show shell restart instructions based on OS
    case $OS_TYPE in
        "macos")
            print_info "Run 'source ~/.zshrc' or restart your terminal to use the new aliases"
            ;;
        *)
            print_info "Run 'source ~/.bashrc' or restart your terminal to use the new aliases"
            ;;
    esac
}

# Run main function
main "$@" 