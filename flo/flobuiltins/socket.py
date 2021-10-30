from __future__ import annotations

import asyncio
from typing import Any, Tuple

from .. observable import AsyncObservable, AsyncManager, Subscriber, unwrap
from .. module import Module, Component, ModuleBuilder

class Socket(ModuleBuilder):

    def compose(self):
        socket = Module("socket")
        self._add_socket_server(socket)
        self._add_socket_client(socket)
        self.parent_module.declare_public("socket", socket)

    def _add_socket_server(self, socket: Module):
        """A simple asynchronus socket server
        - bind: tuple[str, int], accepts the hostname and port to bind to
        - bufferSize: int, accepts the request buffer size (default 256 bytes)
        - messages: tuple[str, Any], emits eith a tuple of (request, callback) for
            each request received
        - isRunning: bool: accept the running state of the server (default false)
        """
        server = Component("server")
        bind = AsyncObservable[Tuple[str, int]]()
        server.declare_public("bind", bind)
        isRunning = AsyncObservable[bool]()
        server.declare_public("isRunning", isRunning)
        messages = AsyncObservable[Any]()
        server.declare_public("messages", messages)
        bufferSize = AsyncObservable[int](256)
        server.declare_public("bufferSize", messages)

        async def handle_client(reader, writer):
            while unwrap(isRunning.peek()):
                bs = unwrap(bufferSize.peek())
                # client connected, read request
                request = (await reader.read(bs)).decode('utf8')
                if not request:
                    # client disconnected
                    return

                async def _on_response_ready(_response):
                    writer.write(unwrap(_response).encode('utf8'))
                    await writer.drain()

                handler = AsyncObservable()
                handler.subscribe(
                    Subscriber(
                        on_next = lambda response : _on_response_ready(response)
                    )
                )
                messages.write((request, handler))

            writer.close()

        async def run_server():
            nonlocal server
            addr, port = unwrap(bind.peek())

            server = await asyncio.start_server(handle_client, unwrap(addr), unwrap(port))
            async with server:
                loop = server.get_loop()

                # need to poll in order for interupt signals to be detected
                # TODO probably a better way to do this.
                try:
                    while loop.is_running:
                        await asyncio.sleep(1)
                except KeyboardInterrupt:
                    pass
                finally:
                    loop.close()
                    server.close()

        isRunning.subscribe(
            Subscriber(
                on_next = lambda data:\
                AsyncManager.get_instance().enqueue_async(run_server()) if data else None
            )
        )

        socket.declare_public("server", server)

    def _add_socket_client(self, socket: Module):
        """A simple asynchronus socket client
        - connectTo: tuple[str, int], accepts the hostname and port to connect to
        - bufferSize: int, accepts the request buffer size (default 256 bytes)
        - requests: any, accepts eith a tuple of (payload, callback), or just
            the payload
        """
        client = Component("client")
        connect_to = AsyncObservable[Tuple[str, int]]()
        client.declare_public("connectTo", connect_to)
        requests = AsyncObservable[Any]()
        client.declare_public("requests", requests)
        bufferSize = AsyncObservable[int](256)
        client.declare_public("bufferSize", bufferSize)

        async def _make_request(reader, writer, data):
            try:
                payload, callback = data.peek()
            except TypeError:
                payload = data.peek()
                callback = None
            writer.write(unwrap(payload).encode())
            await writer.drain()
            response = await reader.read(bufferSize.peek())
            if callable is not None:
                callback.write(response)

        async def _connect(data):
            addr, port = unwrap(connect_to.peek())
            reader, writer = await asyncio.open_connection(
                unwrap(addr), unwrap(port))
            await _make_request(reader, writer, data)

        requests.subscribe(
            Subscriber(
                on_next = lambda data: \
                    AsyncManager.get_instance().enqueue_async(_connect(data))
            )
        )
        socket.declare_public("client", client)
