import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from controllers.app import serve

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    host = sys.argv[2] if len(sys.argv) > 2 else "127.0.0.1"
    serve(port, host)
