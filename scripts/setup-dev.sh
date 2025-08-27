#!/bin/bash
# Development environment setup script

set -e

echo "🚀 Setting up development environment for leaderboard service..."

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
echo "✓ Python version: $PYTHON_VERSION"

# Check if we're in WSL
if grep -qEi "(Microsoft|WSL)" /proc/version &> /dev/null; then
    echo "✓ Detected WSL environment"
    WSL_ENV=true
else
    WSL_ENV=false
fi

# Function to install pip if needed
install_pip() {
    echo "📦 Installing pip..."
    if [ "$WSL_ENV" = true ]; then
        echo "In WSL environment. You may need to run:"
        echo "  sudo apt update && sudo apt install python3-pip python3-venv"
        echo "Or try the following commands manually:"
    fi
    
    # Try to install pip using get-pip.py
    if command -v curl >/dev/null 2>&1; then
        curl https://bootstrap.pypa.io/get-pip.py -o get-pip.py
        python3 get-pip.py --user
        rm get-pip.py
        echo "✓ pip installed using get-pip.py"
    elif command -v wget >/dev/null 2>&1; then
        wget https://bootstrap.pypa.io/get-pip.py
        python3 get-pip.py --user
        rm get-pip.py
        echo "✓ pip installed using get-pip.py"
    else
        echo "❌ Could not install pip automatically. Please install manually:"
        echo "  - Download https://bootstrap.pypa.io/get-pip.py"
        echo "  - Run: python3 get-pip.py --user"
        exit 1
    fi
}

# Check if pip is available
if ! command -v pip3 >/dev/null 2>&1 && ! python3 -m pip --version >/dev/null 2>&1; then
    echo "⚠️  pip not found, attempting to install..."
    install_pip
else
    echo "✓ pip is available"
fi

# Create virtual environment
echo "🔧 Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✓ Virtual environment created"
else
    echo "✓ Virtual environment already exists"
fi

# Function to activate venv and install dependencies
setup_dependencies() {
    echo "📚 Installing dependencies..."
    
    # Try to activate virtual environment
    if [ -f ".venv/bin/activate" ]; then
        source .venv/bin/activate
        echo "✓ Virtual environment activated"
    else
        echo "⚠️  Could not activate virtual environment, installing globally"
    fi
    
    # Install dependencies
    pip install -r requirements.txt
    pip install -r requirements-dev.txt
    
    echo "✓ Dependencies installed"
}

# Install dependencies
setup_dependencies

echo ""
echo "🎉 Development environment setup complete!"
echo ""
echo "To activate the environment manually, run:"
echo "  source .venv/bin/activate"
echo ""
echo "To run tests:"
echo "  pytest -v"
echo ""
echo "To run tests with coverage:"
echo "  pytest -v --cov=src --cov-report=term-missing"
echo ""
echo "To run linting:"
echo "  black src/ tests/ && ruff src/ tests/ && mypy src/"