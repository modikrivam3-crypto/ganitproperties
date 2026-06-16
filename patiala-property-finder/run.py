"""
Entry point — run this to start the Patiala Property Finder.

    python run.py

Then open http://127.0.0.1:5050 on your laptop
or http://<your-laptop-ip>:5050 on your phone (same Wi-Fi).
"""
import os
import subprocess
import sys
import socket


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "your-laptop-ip"


if __name__ == "__main__":
    from app import app, init_db

    init_db()

    ip = get_local_ip()
    print("\n" + "=" * 54)
    print("  Patiala Property Finder")
    print("=" * 54)
    print(f"  Laptop:  http://127.0.0.1:5050")
    print(f"  Phone:   http://{ip}:5050  (same Wi-Fi)")
    print("=" * 54)
    print("  Press Ctrl+C to stop\n")

    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
