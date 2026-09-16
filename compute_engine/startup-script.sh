#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip python3-venv git curl
mkdir -p /opt/chatbot/compute_engine
chmod 755 /opt/chatbot
