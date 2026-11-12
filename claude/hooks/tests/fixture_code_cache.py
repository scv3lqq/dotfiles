"""Private, content-addressed storage for immutable executable fixture code."""
from __future__ import annotations

import hashlib
import os
import stat
import tempfile
import uuid
from functools import lru_cache
from pathlib import Path


@lru_cache(maxsize=32)
def _interpreter_digest(path: str, device: int, inode: int, size: int, modified: int) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def cached_executable(content: str, directory: Path | None = None) -> Path:
    body = content.encode()
    first_line = body.split(b"\n", 1)[0]
    if not first_line.startswith(b"#!"):
        raise ValueError("fixture code must name its interpreter")
    interpreter = os.fsdecode(first_line[2:].strip().split(b" ", 1)[0])
    info = os.stat(interpreter)
    interpreter_digest = _interpreter_digest(interpreter, info.st_dev, info.st_ino,
                                             info.st_size, info.st_mtime_ns)
    content_digest = hashlib.sha256(body).hexdigest()
    digest = hashlib.sha256(body + b"\0" + interpreter_digest.encode()).hexdigest()
    root = directory or Path(tempfile.gettempdir()) / f"dotfiles-fixture-code-{os.getuid()}"
    try:
        root.mkdir(mode=0o700)
    except FileExistsError:
        pass
    info = root.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700:
        raise RuntimeError("fixture code cache must be a private owned directory")
    directory_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    name = digest
    temporary = f".{digest}.{uuid.uuid4().hex}"
    try:
        try:
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        except FileNotFoundError:
            fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
                         0o500, dir_fd=directory_fd)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(body)
                try:
                    os.link(temporary, name, src_dir_fd=directory_fd, dst_dir_fd=directory_fd,
                            follow_symlinks=False)
                except FileExistsError:
                    pass
            finally:
                os.unlink(temporary, dir_fd=directory_fd)
            fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
        with os.fdopen(fd, "rb") as stream:
            info = os.fstat(stream.fileno())
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                    or stat.S_IMODE(info.st_mode) != 0o500
                    or hashlib.sha256(stream.read()).hexdigest() != content_digest):
                raise RuntimeError("invalid fixture code cache entry")
    finally:
        os.close(directory_fd)
    return root / name
