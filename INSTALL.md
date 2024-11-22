# Detailed Installation Instructions

## System Requirements

### Python Version
- Python 3.8 or newer
- tkinter 8.6 or newer (usually included with Python)

### Required Packages
- requests (for API interactions)
- ttkthemes (for GUI theming)
- tkinter (usually included with Python)

## Installation Methods

### 1. GitHub Installation
```bash
pip install git+https://github.com/yourusername/protdomretrieversuite.git
```

### 2. Local Installation
```bash
# Clone repository
git clone https://github.com/yourusername/protdomretrieversuite.git

# Navigate to directory
cd protdomretrieversuite

# Install package
pip install .
```

### 3. Development Installation
For live code updates during development:
```bash
pip install -e .
```

## Virtual Environment Setup

### Creating a Virtual Environment

#### For macOS and Linux
```bash
# Create environment
python3 -m venv .venv

# Activate environment
source .venv/bin/activate
```

#### For Windows
```bash
# Create environment
python -m venv .venv

# Activate environment
.venv\Scripts\activate
```

### Installing Requirements
```bash
# Verify Python version
python --version

# Install requirements
pip install -r requirements.txt
```

### Deactivating Environment
```bash
deactivate
```

## System-Specific Setup

### macOS Setup

#### Finding Python Installation
```bash
# Find Python installations
where python3

# Check version
python3 --version

# For Homebrew users
brew list --versions | grep python
```

#### Installing tkinter (if needed)
```bash
brew install python-tk@3.x  # Replace 3.x with your Python version
```

### Linux Setup

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install python3-tk
```

#### Fedora
```bash
sudo dnf install python3-tkinter
```

## Troubleshooting

### Common Issues

1. **Missing tkinter**
   - Follow system-specific installation instructions above
   - Verify installation: `python -c "import tkinter; tkinter._test()""`

2. **SSL Certificate Errors**
   - Ensure Python installation has SSL support
   - Check system certificates
   - Update certificates if needed

3. **Installation Fails**
   - Check Python version compatibility
   - Verify virtual environment activation
   - Check for system-specific requirements
   - Ensure sufficient permissions

### Getting Help
For additional help:
1. Check the log files
2. Open an issue on GitHub
3. Contact the developer
