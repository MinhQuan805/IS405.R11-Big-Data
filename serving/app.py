"""Compatibility entry point for the installed HTTP service."""
from admission_core.http_api import create_server, start_server

if __name__ == "__main__":
    start_server()
