from .. observable import AsyncObservable, Subscriber
from .. module import Module, Component, ModuleBuilder

class File(ModuleBuilder):

    def compose(self):
        file = Module("file")
        self._add_file_reader(file)
        self._add_file_writer(file)
        self.parent_module.declare_public("file", file)

    @staticmethod
    def _add_file_reader(file: Module):
        """File reader
        - path: str, accepts the path to the file to read from
        - readlines: string: emits the contents of the file, line by line
        """
        reader = Component("reader")
        path = AsyncObservable[str]()
        reader.declare_public("path", path)
        encoding = AsyncObservable[str]("utf-8")
        reader.declare_public("encoding", encoding)
        reader_observable = AsyncObservable[str]()
        reader.declare_public("readlines", reader_observable)
        def _reader(path):
            with open(path.peek(), "r", encoding=encoding.peek()) as f:
                for line in f:
                    reader_observable.write(line)
        path.subscribe(
            Subscriber(
                on_next = _reader
            )
        )
        file.declare_public("reader", reader)

    @staticmethod
    def _add_file_writer(file: Module):
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
        encoding = AsyncObservable[str]("utf-8")
        writer.declare_public("encoding", encoding)
        def _write_append(data):
            _path = path.peek()
            if _path is not None:
                with open(_path.peek(), "a", encoding=encoding.peek()) as f:
                    f.write(data.peek())
        write_append_observable.subscribe(
            Subscriber(
                on_next = _write_append
            )
        )

        write_observable = AsyncObservable[str]()
        writer.declare_public("write", write_observable)
        def _write(data):
            _path = path.peek()
            if _path is not None:
                with open(_path.peek(), "w", encoding=encoding.peek()) as f:
                    f.write(data.peek())
        write_observable.subscribe(
            Subscriber(
                on_next = _write
            )
        )
