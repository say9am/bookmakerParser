import logging


class MessageHandler:
    """
    Handles incoming messages from WebSocket clients.
    """

    async def process_message(self, websocket, message):
        """
        Processes a received message from a WebSocket client.

        Args:
            websocket: The WebSocket connection that sent the message.
            message: The received message (typically a string or JSON-encoded data).
        """
        logging.info(f"Received message: {message}")
