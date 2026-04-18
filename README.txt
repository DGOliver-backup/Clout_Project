# Edge Caching Proxy System - Artifact Evaluation

Welcome to the artifact repository for our Edge Caching Proxy System. This repository contains the source code, deployment scripts, and automated evaluation suites to reproduce the experiments discussed in our report.

## Repository Structure

Our project is modularized into three main components, reflecting our team's workflow:
* 'Cache-Proxy-Server/': Core FastAPI proxy server, caching engines (LRU, LFU, TTL), and S3 fetch logic.
* 'FileGenerationAndServerSetUp/': S3 dataset generation tools and cloud deployment configurations.
* 'RequestSendingAndVisualization/': Client-side workload generator and automated data visualization scripts.

---

## Prerequisites (For Evaluators)

To run this artifact seamlessly, you will need:
1. Local Environment: Python 3.9+ with `pip` installed. Unix-based OS (Linux/macOS) is recommended for the automation script.
2. AWS EC2 Instance: An active Ubuntu/Amazon Linux EC2 instance as the Origin Server.
3. Connectivity: Ensure the EC2 Security Group allows inbound traffic on the designated port (e.g., 8000) from your local IP.
4. AWS IAM Role (Crucial Security Note): We adhere to AWS security best practices. The proxy server does not use hardcoded Access Keys. Please ensure your EC2 instance is attached to an IAM Role with Amazon S3 Read Access so it can fetch the origin files.

---

## How to Run: Automated CI/CD Workflow (Recommended)

To ensure maximum reproducibility and a fully portable workflow, we have provided an automated master script. This script handles remote deployment, server initialization, and local workload generation automatically.

### Step-by-Step Execution:

1. Clone the repository to your local machine:
   ```bash
   git clone <YOUR_GITHUB_REPO_URL_HERE>
   cd <YOUR_REPO_NAME>

2. Make the script executable:

  ```Bash
  chmod +x run_all.sh
  
3. Run the automation script:

  ```Bash
  ./run_all.sh

4. Follow the on-screen prompts:
  The script will ask for your EC2 Public IP and SSH credentials.
  What happens next?
  Remote Check: The script verifies that the Origin Server is active on your AWS EC2 instance.
  Local Proxy Startup: The script initializes the app.py proxy on your localhost (127.0.0.1:8000), configured to fetch MISSing data from the AWS EC2 IP.
  Automated Testing: It launches the workload.py generator, which sends requests to the Local Proxy to evaluate LRU, LFU, and TTL policies..

5. View Results:
  Once finished, the experiment data will be saved locally in experiment_results.json, and visualization charts (e.g., hit rates, latency) will be generated in the RequestSendingAndVisualization/ folder.
