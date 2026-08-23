import sqlite3
import subprocess

from integrations.adapter import Adapter


def handler():
    database = sqlite3.connect(":memory:")
    return subprocess.run(["echo", Adapter().name()], check=True), database
