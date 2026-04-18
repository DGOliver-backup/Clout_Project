#!/bin/bash

# Configuration
read -p "1. Enter EC2 Public IP (Origin): " EC2_IP
read -p "2. Enter EC2 Username: " SSH_USER
read -p "3. Enter path to .pem key: " PEM_KEY

# [Step 1] Ensure Remote Origin Server is running on EC2
echo "[Step 1] Checking Remote Origin Server on EC2..."
ssh -i "$PEM_KEY" -o StrictHostKeyChecking=no "$SSH_USER@$EC2_IP" << EOF
    pkill -f uvicorn || true
    # Start the origin service (assuming code exists on EC2)
    # nohup python3 -m uvicorn origin_app:app --host 0.0.0.0 --port 8000 > origin.log 2>&1 &
EOF

# [Step 2] Start Local Proxy
echo "[Step 2] Starting Local Proxy Server..."
export ORIGIN_IP="$EC2_IP"

nohup python3 -m uvicorn app:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 60 > proxy.log 2>&1 &

sleep 5

# [Step 3] Run Workload and Visualization
echo "[Step 3] Running Local Workload & Visualization..."
cd RequestSendingAndVisualization
python3 workload.py
