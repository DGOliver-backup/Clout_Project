#!/bin/bash

echo "Note: This script requires an AWS EC2 environment with an IAM Role for S3 access."
echo "To automatically deploy to your AWS EC2 instance, please provide the following:"
read -p "1. Enter your EC2 Public IP: " EC2_IP
read -p "2. Enter your EC2 Username (e.g., ubuntu or ec2-user): " SSH_USER
read -p "3. Enter the path to your .pem SSH key file (e.g., ~/Downloads/key.pem): " PEM_KEY

echo "[Step 1] Uploading Proxy Server code to EC2 ($EC2_IP)..."
scp -i "$PEM_KEY" -o StrictHostKeyChecking=no -r Cache-Proxy-Server "$SSH_USER@$EC2_IP:~/"

echo "[Step 2] Installing dependencies and starting server on EC2..."
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_IP" << EOF
    cd Cache-Proxy-Server
    sudo apt-get update -y > /dev/null 2>&1
    sudo apt-get install python3-pip -y > /dev/null 2>&1
    pip3 install -r requirements.txt > /dev/null 2>&1
    pkill -f uvicorn || true
    
    nohup python3 -m uvicorn app:app --host 0.0.0.0 --port 8000 > server_log.txt 2>&1 &
    echo "Server successfully started in the background on EC2!"
EOF

sleep 5
echo "[Step 3] Running Local Workload & Visualization..."
export PROXY_IP="$EC2_IP"
cd RequestSendingAndVisualization
pip install httpx numpy matplotlib > /dev/null 2>&1
python workload.py

