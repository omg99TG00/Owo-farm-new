#!/bin/bash
pip uninstall discord.py-self -y --quiet 2>/dev/null || true
pip install -r requirements.txt --quiet
exec python3 -u main.py
