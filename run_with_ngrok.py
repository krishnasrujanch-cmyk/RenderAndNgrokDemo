import os, subprocess, threading, time, requests
from dotenv import load_dotenv
load_dotenv(override=True)

def start_ngrok(port):
    print(f"\n  Starting ngrok tunnel on port {port}...")
    proc = subprocess.Popen(["ngrok", "http", str(port)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3)
    try:
        resp = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=5)
        tunnels = resp.json().get("tunnels", [])
        https_tunnels = [t for t in tunnels if t["proto"] == "https"]
        public_url = (https_tunnels or tunnels)[0]["public_url"]
        print(f"\n{'='*60}\n  🚀 NGROK TUNNEL IS LIVE!\n  Public URL : {public_url}\n  Swagger UI : {public_url}/docs\n  Health     : {public_url}/health\n  Chat API   : {public_url}/chat\n  Inspector  : http://127.0.0.1:4040\n{'='*60}\n")
    except Exception as e:
        print(f"  Could not read ngrok API: {e}\n  Check http://127.0.0.1:4040 manually.")
    return proc

def start_server(port):
    import uvicorn
    uvicorn.run("financeassist_app:app", host="0.0.0.0", port=port, log_level="info")

if __name__ == "__main__":
    PORT = 8000
    threading.Thread(target=start_server, args=(PORT,), daemon=True).start()
    time.sleep(2)
    proc = start_ngrok(PORT)
    print("Press Ctrl+C to stop.\n")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        proc.terminate()
        print("\n✅ Stopped.")
