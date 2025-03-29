import asyncio
import logging
import os
import json
import random

import websockets

from config import HOST, PORT
from core.connections import ConnectionManager
from core.handler import MessageHandler


class WebSocketServer:
    def __init__(self):
        """
        Initializes the WebSocket server.
        """
        self.handler = MessageHandler()
        self.connection_manager = ConnectionManager()
        self.track_commands = os.path.abspath("../server/track_commands")  # Use relative path for better portability

    async def send_random_json_file(self, websocket):
        """
        Selects a random JSON file from the directory and sends it to the client.

        Args:
            websocket: The WebSocket connection to send the file to.
        """
        try:
            if not os.path.isdir(self.track_commands):
                logging.warning(f"Directory not found: {self.track_commands}")
                return

            json_files = [f for f in os.listdir(self.track_commands) if f.endswith('.json')]
            if not json_files:
                logging.warning("No JSON files found in the directory.")
                return

            selected_file = random.choice(json_files)
            file_path = os.path.join(self.track_commands, selected_file)

            with open(file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)

            await self.send_message(websocket, json_data)
            logging.info(f"Sent file: {selected_file}")
        except Exception as e:
            logging.error(f"Error sending random JSON file: {e}", exc_info=True)

    async def send_message(self, websocket, message):
        """
        Sends a JSON message to the WebSocket client.

        Args:
            websocket: The WebSocket connection.
            message: The message to send (dict or list).
        """
        try:
            await websocket.send(json.dumps(message))
            logging.info(f"Message sent to client: {message}")
        except Exception as e:
            logging.error(f"Error sending message: {e}", exc_info=True)

    async def client_handler(self, websocket):
        """
        Handles a connected WebSocket client.

        Args:
            websocket: The WebSocket connection.
        """
        await self.connection_manager.connect(websocket)

        try:
            await self.send_random_json_file(websocket)

            async for message in websocket:
                await self.handler.process_message(websocket, message)
        except websockets.exceptions.ConnectionClosedOK:
            logging.info("Connection closed normally by client.")
        except websockets.exceptions.ConnectionClosedError as e:
            logging.warning(f"Connection closed with error: {e}")
        except Exception as e:
            logging.error(f"Error in client_handler: {e}", exc_info=True)
        finally:
            await self.connection_manager.disconnect(websocket)

    async def start_server(self):
        """
        Starts the WebSocket server.
        """
        async with websockets.serve(self.client_handler, HOST, PORT):
            logging.info(f"Server started on {HOST}:{PORT}")
            await asyncio.Future()  # Keep the server running indefinitely

    def run(self):
        """
        Runs the WebSocket server.
        """
        try:
            asyncio.run(self.start_server())
        except KeyboardInterrupt:
            logging.info("Server manually stopped (KeyboardInterrupt).")
        except Exception as e:
            logging.critical(f"Critical error in server execution: {e}", exc_info=True)
