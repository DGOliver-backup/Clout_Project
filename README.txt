# How to Run the Experiment (For TA Evaluation)

Our system is designed with a decoupled architecture. The proxy server runs on AWS EC2, and the workload generator (client) runs locally.

### Step 1: Start the Proxy Server (AWS EC2)
1. Deploy the `Cache-Proxy-Server` on your AWS EC2 instance.(For more detail, please refer to the instructions in the folder "FileGenerationAndServerSetUp")
2. Run the server: `uvicorn main:app --host 0.0.0.0 --port 8000`
3. **Find your IP:** Go to your AWS Management Console, click on "Instances", select your running instance, and copy the **Public IPv4 address**.

### Step 2: Run the Workload Generator (Local Machine)
You do not need to modify any source code. We use environment variables to dynamically route the traffic.

Open your local terminal and run the following command, replacing `<YOUR_EC2_IP>` with the IP you just copied:

#### For Linux/macOS:
```bash
PROXY_IP=<YOUR_EC2_IP> python workload.py
