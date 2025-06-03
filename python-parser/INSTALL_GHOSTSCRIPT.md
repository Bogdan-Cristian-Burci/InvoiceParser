# Installing Ghostscript for Table Extraction

Ghostscript is required by Camelot (the PDF table extraction library) to properly process PDF tables.

## Current Status
❌ **Ghostscript not installed** - This is why table extraction returns 0 products

## Quick Installation

### macOS (your system):
```bash
# Install using Homebrew (recommended)
brew install ghostscript

# Verify installation
gs --version
```

### Ubuntu/Debian:
```bash
sudo apt-get update
sudo apt-get install ghostscript
```

### Windows:
1. Download from: https://www.ghostscript.com/download/gsdnld.html
2. Run the installer
3. Add to PATH if needed

## What This Fixes

**Before Ghostscript:**
- ✅ Delivery extraction works (9 deliveries found)
- ❌ Table extraction fails (0 products found)  
- ❌ Error: "Ghostscript is not installed"

**After Ghostscript:**
- ✅ Delivery extraction works
- ✅ Table extraction works (should find 5+ products per delivery)
- ✅ Your table extraction improvements will be testable

## Test After Installation

```bash
cd python-parser
python3 test_fix.py
```

You should see actual products extracted instead of empty results.

## Docker Alternative

If you prefer not to install Ghostscript locally, the Docker environment already includes it:

```bash
# Use Docker instead - Ghostscript is pre-installed
docker-compose up -d
# Test through Docker API endpoints
```

## Verification

Run this to confirm Ghostscript is working:
```bash
gs --version
# Should show: GPL Ghostscript 10.x.x
```

Once installed, your table extraction fixes should work properly!