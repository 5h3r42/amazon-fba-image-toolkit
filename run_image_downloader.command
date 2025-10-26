#!/bin/zsh
# Keep PATH sane when launched from Finder
export PATH="/usr/local/bin:/opt/homebrew/bin:/Library/Frameworks/Python.framework/Versions/3.11/bin:$PATH"

# >>> CHANGE THIS if your python path is different <<<
PY="/usr/bin/env python3.11"

# Go to your project folder
cd "/Users/sherazkhalid/Documents/Apps/Python_Projects/savzix_images" || exit 1

# Run the downloader
$PY download_images_by_product.py

# Keep the window open so you can read output
echo
read -sk 1 "?Done. Press any key to close…"