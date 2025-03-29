import logging
import os

from config import LOG_FILE
from core.server import WebSocketServer

# Set up logging directory
log_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../server/logs"))
os.makedirs(log_dir, exist_ok=True)
log_file_path = os.path.join(log_dir, LOG_FILE)

# Configure logging settings
logging.basicConfig(
    filename=log_file_path,
    filemode='a',
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s [%(name)s] - %(message)s"
)

# Start WebSocket server
if __name__ == "__main__":
    server = WebSocketServer()
    server.run()
