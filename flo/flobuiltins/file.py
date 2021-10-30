from .. observable import AsyncObservable, Subscriber
from .. module import Module, Component, ModuleBuilder

class File(ModuleBuilder):

    def compose(self):
        file = Module("file")
        self._add_file_reader(file)
        self._add_file_writer(file)
        self.parent_module.declare_public("file", file)

    def _add_file_reader(self, file: Module):
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
        file.declare_public("reader", reader)

    def _add_file_writer(self, file: Module):
        """File writer
        - path: str, accepts the path to the file to write to
        - append: any, binary-encodable data to write to the file
        """
        writer = Component("writer")
        path = AsyncObservable[str]()
        writer.declare_public("path", path)

        file.declare_public("writer", writer)
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