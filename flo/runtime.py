"""Entities used as part of the runtime
"""
from __future__ import annotations

import asyncio
import socket
import sys
from typing import Any, Union, Tuple

from . import AsyncObservable, Subscriber, AsyncManager, unwrap

class Module:
    def __init__(self, name, **opts):
        self.name = name
        self.locals = {k:("local", opts[k]) for k in opts.keys()}
        self.parent = None

    def _check_is_not_defined(self, name):
        if name in self.locals:
            raise Exception("Variable '{}' is already defined".format(name))

    def declare_local(self, name: str,
        attr: Union[AsyncObservable, Component, Module]):
        self._check_is_not_defined(name)
        self.locals[name] = ("local", attr)

    def declare_public(self, name: str, pipe: AsyncObservable):
        self._check_is_not_defined(name)
        self.locals[name] = ("public", pipe)

    def get_member(self, name):
        return self.locals[name][1]

    def __str__(self):
        return "<Module '{}'>".format(self.name)

    def __repr__(self):
        return str(self)

class Component(Module):
    def __init__(self, name, **opts):
        super().__init__(name, **opts)

    def duplicate(self, **overrides):
        comp = Component(self.name)
        comp.locals = self.locals
        for key in overrides.keys():
            if key in comp.locals:
                access = comp.locals[key][0]
                comp.locals[key] = (access, overrides[key])
            else:
                raise Exception("{} has no local attr '{}'".format(comp, key))
        return comp

    def __str__(self):
        return "<Component '{}'>".format(self.name)

class Filter(Module):
    def __init__(self, name, input_observable: AsyncObservable):
        super().__init__("Anonymous Filter on '{}'".format(name))
        self.declare_public(name, input_observable)


class Runtime(Subscriber[int]):
    SIG_TERMINATE = 0
    def _restart(self):
        pass
    def _exit(self):
        sys.exit(0)
    async def on_next(self, value: int):
        if value == self.__class__.SIG_TERMINATE:
            self._exit()
        # TODO react to value, terminate, restart etc
        pass

def add_file_reader(parent_module):
    """File reader
    - path: str, accepts the path to the file to read from
    - readlines: string: emits the contents of the file, line by line
    """
    reader = Component("reader")
    path = AsyncObservable[str]()
    reader.declare_public("path", path)
    reader_observable = AsyncObservable[str]()
    reader.declare_public("readlines", reader_observable)
    def _reader(path):
        with open(path.peek(), "r") as f:
            for line in f:
                reader_observable.write(line)
    path.subscribe(
        Subscriber(
            on_next = lambda p: _reader(p)
        )
    )
    parent_module.declare_public("reader", reader)

def add_file_writer(parent_module):
    """File writer
    - path: str, accepts the path to the file to write to
    - append: any, binary-encodable data to write to the file
    """
    writer = Component("writer")
    path = AsyncObservable[str]()
    writer.declare_public("path", path)

    parent_module.declare_public("writer", writer)
    write_append_observable = AsyncObservable[str]()
    writer.declare_public("append", write_append_observable)
    def _write_append(data):
        _path = path.peek()
        if _path is not None:
            with open(_path.peek(), "a") as f:
                f.write(data.peek())
    write_append_observable.subscribe(
        Subscriber(
            on_next = lambda data: _write_append(data)
        )
    )

    write_observable = AsyncObservable[str]()
    writer.declare_public("write", write_observable)
    def _write(data):
        _path = path.peek()
        if _path is not None:
            with open(_path.peek(), "w") as f:
                f.write(data.peek())
    write_observable.subscribe(
        Subscriber(
            on_next = lambda data: _write(data)
        )
    )

def compose_file_module(parent_module):
    file = Module("file")
    add_file_reader(file)
    add_file_writer(file)
    parent_module.declare_public("file", file)

def add_socket_server(parent_module):
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
    isRunning = AsyncObservable[bool](False)
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

    parent_module.declare_public("server", server)

def add_socket_client(parent_module):
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
    parent_module.declare_public("client", client)

def compose_socket_module(parent_module):
    socket = Module("socket")
    add_socket_server(socket)
    add_socket_client(socket)
    parent_module.declare_public("socket", socket)


def setup_default_runtime():
    active_runtime = Runtime()

    _builtin_stdout = AsyncObservable[Any]()
    _builtin_stdout.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stdout.write(str(s) + "\n")))

    _builtin_stderr = AsyncObservable[Any]()
    _builtin_stderr.subscribe(
        Subscriber[str](
            on_next = lambda s : sys.stderr.write(str(s) + "\n")))

    #_builtin_stdin = AsyncObservable[Any]()
    # for line in sys.stdin:
        # _builtin_stdin.write(line)

    _builtin_runtime = AsyncObservable[int]()
    _builtin_runtime.subscribe(active_runtime)

    __main_module__ = Module("main", **{
        # "stdin": _builtin_stdin,
        "stdout" : _builtin_stdout,
        "stderr" : _builtin_stderr,
        "rt" : _builtin_runtime
    })

    compose_file_module(__main_module__)
    compose_socket_module(__main_module__)

    return __main_module__
