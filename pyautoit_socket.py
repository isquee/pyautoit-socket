import json
import re
import socket
import socketserver
import subprocess
import datetime
import logging
import threading
import time


logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("peewee").setLevel(logging.INFO)


now_str = datetime.datetime.now().strftime(r"%Y-%m-%d_%Hh%Mm%Ss")

Logger = logging.getLogger("AutoItSocketIO")
Logger.setLevel(logging.DEBUG)

# _debug_handler = logging.FileHandler(f"log/{now_str}.debug.log")
# _info_handler = logging.FileHandler(f"log/{now_str}.info.log")

# Set levels for handlers
# _debug_handler.setLevel(logging.DEBUG)
# _info_handler.setLevel(logging.INFO)

# Create formatters and add them to handlers
# formatter = logging.Formatter(
#     "%(asctime)s - %(name)s - %(levelname)s - %(message)s", r"%Y-%m-%d %H:%M:%S"
# )
# _debug_handler.setFormatter(formatter)
# _info_handler.setFormatter(formatter)

# Add handlers to the logger
# Logger.addHandler(_debug_handler)
# Logger.addHandler(_info_handler)


handlers = {}


def server(ip="0.0.0.0", port=5000) -> socketserver.ThreadingTCPServer:
    """
    Instantiate the server

    :param ip: server ip
    :param port: server port
    :returns server: socketserver.ThreadingTCPServer
    """
    return _AisioThreadingServer((ip, port), _AisioRequestHandler)


def connect_and_listen(host="127.0.0.1", port=5000):
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((host, port))
                Logger.info(f"Connected to {host}:{port}")
                loop_thread = threading.Thread(target=_trigger_client_loop_event)
                loop_thread.start()
                while True:
                    data = sock.recv(8192)
                    if not data:
                        Logger.info("Disconnected.")
                        break
                    _handle_recv_package(data.decode(), sock)
                loop_thread.join()
        except (ConnectionRefusedError, ConnectionResetError) as e:
            print(f"Connection error: {e}. Retrying in 5 seconds...")
            time.sleep(5)

def _trigger_client_loop_event():
    while True:
        _trigger_event("loop")
        time.sleep(1)

def on(event, handler=None):
    """Register an event handler.

    :param event: The event name. It can be any string. The event names
                    ``'connect'``, ``'message'`` and ``'disconnect'`` are
                    reserved and should not be used. The ``'*'`` event name
                    can be used to define a catch-all event handler.
    :param handler: The function that should be invoked to handle the
                    event. When this parameter is not given, the method
                    acts as a decorator for the handler function.

    Example usage::

        # as a decorator:
        @sio.on('connect', namespace='/chat')
        def connect_handler(sid, environ):
            Logger.debug('Connection request')
            if environ['REMOTE_ADDR'] in blacklisted:
                return False  # reject

        # as a method:
        def message_handler(sid, msg):
            Logger.debug('Received message: ', msg)
            sio.send(sid, 'response')
        socket_io.on('message', namespace='/chat', handler=message_handler)

    The arguments passed to the handler function depend on the event type:

    - The ``'connect'`` event handler receives the (socket, addr) for the client.
    - The ``'disconnect'`` handler receives the socket for the client.
    """

    def set_handler(handler):
        global handlers
        handlers[event] = handler
        return handler

    if handler is None:
        return set_handler
    return set_handler(handler)


def event(*args, **kwargs):
    """Decorator to register an event handler.

    This is a simplified version of the ``on()`` method that takes the
    event name from the decorated function.

    Example usage::

        @sio.event
        def my_event(data):
            Logger.debug('Received data: ', data)

    The above example is equivalent to::

        @sio.on('my_event')
        def my_event(data):
            Logger.debug('Received data: ', data)
    """
    if len(args) == 1 and len(kwargs) == 0 and callable(args[0]):
        # the decorator was invoked without arguments
        # args[0] is the decorated function
        return on(args[0].__name__)(args[0])
    else:
        # the decorator was invoked with arguments
        def set_handler(handler):
            return on(handler.__name__, *args, **kwargs)(handler)

        return set_handler


def emit(socket: socket.socket, event: str, *args):
    """
    Serialize and emit event to an autoit socketio connected socket

    :params socket: socket connection
    :params event: event name
    :params *args: args
    """
    package = _prep_package(event, args)
    Logger.debug(f"sent package:  {package}")
    try:
        socket.sendall(package)
    except Exception as err:
        Logger.error(
            f"couldn't send package, socket: {socket}, event: {event}, args: {args}"
        )


def _prep_package(event: str, args):
    if not args:
        package = _Serialize([event, 0])
    else:
        package = _Serialize([event, args])
    decoded = package.decode()
    decoded += "#"
    package = decoded.encode()
    return package


def _handle_recv_package(package: str, sock: socket.socket):
    # Remove last strap of package load (Can be 1 to n)
    package = re.sub(r"(?s)(.*)\#$", r"\1", package)
    packages = package.split("#")

    for package in packages:
        unserialized = _Unserialize(package)
        if not unserialized:
            Logger.error(f"Tried to unserialize nonetype: {package}")
            return
        # here autoitsocketio handle emiting events when there is no parameters kind weirdly, so I will handle both (with no args and with args set to 0)
        # if len(unserialized) == 1:
        #     (event_name,) = unserialized
        #     _trigger_event(event_name, sock)
        #     return
        event_name, event_args = unserialized
        if not event_args:
            _trigger_event(event_name, sock)
        else:
            _trigger_event(event_name, sock, *event_args)


def _trigger_event(event, *args):
    """Invoke an application event handler."""
    # first see if we have an explicit handler for the event
    handler = _get_event_handler(event)
    if not handler:
        Logger.error("Tried to trigger event handler that not exists or found")
        return object()
    return handler(*args)


def _get_event_handler(event):
    global handlers
    # Return the appropriate application event handler
    handler = handlers.get(event)
    return handler


class _AisioRequestHandler(socketserver.BaseRequestHandler):
    # def setup(self) -> None:
    #     Logger.info("Start request.")

    def handle(self) -> None:
        sock = self.request
        client_addr = self.client_address
        while True:
            try:
                data = sock.recv(8192)
            except Exception as err:
                Logger.debug(err)
                _trigger_event("disconnect", sock)
                break
            else:
                if not data:
                    _trigger_event("disconnect", sock)
                    break
                package = data.decode()
                _handle_recv_package(package, sock)

    # def finish(self) -> None:
    #     Logger.info("Finish request.")


class _AisioThreadingServer(socketserver.ThreadingTCPServer):
    def server_activate(self) -> None:
        Logger.info("Server started on %s:%s", *self.server_address)
        super().server_activate()

    def get_request(self) -> tuple[socket.socket, str]:
        conn, addr = super().get_request()
        Logger.debug("Connection from %s:%s", *addr)
        _trigger_event("connect", conn, addr)
        return conn, addr

    def service_actions(self) -> None:
        _trigger_event("loop")


def _Serialize(a: list) -> bytes:
    try:
        # Run the JavaScript file
        toJson = json.dumps(a)
        process = subprocess.Popen(
            [
                "node",
                r"topper/pythontoautoitsocket/external_scripts/AutoItSerialize/serialize.js",
                toJson,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        # Handle errors
        if stderr:
            Logger.error("Errors: %s", stderr.decode())
        return stdout
    except Exception as e:
        Logger.error("Exception occurred: %s", str(e))
        return b""


def _Unserialize(s: str) -> list[str]:
    try:
        # Run the JavaScript file
        process = subprocess.Popen(
            [
                "node",
                r"topper/pythontoautoitsocket/external_scripts/AutoItSerialize/unserialize.js",
                s,
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        # Handle errors
        if stderr:
            Logger.error("Errors: %s", stderr.decode())
        # Parse the JSON output
        unserialized = json.loads(stdout)
        return unserialized
    except Exception as e:
        Logger.error("Exception occurred: %s", str(e))
        return []
