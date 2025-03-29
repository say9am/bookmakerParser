import logging
from weakref import WeakSet


class ConnectionManager:
    """
    Manages active WebSocket connections.
    """

    def __init__(self):
        """
        Initializes the connection manager.
        """
        self.active_connections = WeakSet()

    async def connect(self, websocket):
        """
        Adds a new WebSocket connection.

        Args:
            websocket: The WebSocket connection to add.
        """
        self.active_connections.add(websocket)
        try:
            remote_addr_tuple = getattr(websocket, "remote_address", None)
            if remote_addr_tuple:
                client_ip = remote_addr_tuple[0]
                client_port = remote_addr_tuple[1]
                logging.info(f"Client {client_ip}:{client_port} connected.")
            else:
                logging.info("Client address unavailable.")
        except Exception as e:
            logging.warning(f"Failed to retrieve or process client address on connection: {e}", exc_info=True)

    async def disconnect(self, websocket):
        """
        Removes a WebSocket connection.

        Args:
            websocket: The WebSocket connection to remove.
        """
        self.active_connections.discard(websocket)
        try:
            remote_addr_tuple = getattr(websocket, "remote_address", None)
            if remote_addr_tuple:
                client_ip = remote_addr_tuple[0]
                client_port = remote_addr_tuple[1]
                logging.info(f"Client {client_ip}:{client_port} disconnected.")
            else:
                logging.info("Client address unavailable.")
        except Exception as e:
            logging.warning(f"Error retrieving address of disconnected client: {e}", exc_info=True)
