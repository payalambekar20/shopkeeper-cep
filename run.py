"""
ShopKeeper — main entry point.

This runs the app with Waitress (a production-grade server) instead of
Flask's built-in development server, and automatically opens the shop
owner's default browser — so there's no terminal command to explain, no
"localhost" URL to type, just a window that opens on its own.
"""
import threading
import webbrowser
import socket
from waitress import serve
from app import create_app

HOST = "0.0.0.0"   # reachable from this PC AND other devices on the same WiFi
PORT = 5000


def get_local_ip():
    """Best-effort guess at this PC's own WiFi/LAN IP, for display only."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))  # doesn't actually send data, just picks a route
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def open_browser():
    webbrowser.open(f"http://127.0.0.1:{PORT}")


app = create_app()

if __name__ == "__main__":
    # Opens the browser 1.5 seconds after starting, giving the server time
    # to actually be ready to accept the first request.
    threading.Timer(1.5, open_browser).start()

    local_ip = get_local_ip()
    print("=" * 60)
    print("  ShopKeeper is starting...")
    print("  Your browser will open automatically.")
    print()
    print(f"  On THIS computer:        http://127.0.0.1:{PORT}")
    print(f"  From a phone (same WiFi): http://{local_ip}:{PORT}")
    print()
    print("  Keep this window open while using ShopKeeper.")
    print("  Close this window to stop the program.")
    print("=" * 60)

    serve(app, host=HOST, port=PORT)
