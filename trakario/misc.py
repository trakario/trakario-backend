import uvicorn
from uvicorn.supervisors import Multiprocess, ChangeReload

from .logs import setup_logging


def run_uvicorn(config: uvicorn.Config):
    """Same as uvicorn.run but injects logging"""
    import logging

    server = uvicorn.Server(config=config)
    setup_logging(logging.INFO)
    supervisor_type = None
    if config.should_reload:
        supervisor_type = ChangeReload
    if config.workers > 1:
        supervisor_type = Multiprocess
    if supervisor_type:
        sock = config.bind_socket()
        supervisor = supervisor_type(config, target=server.run, sockets=[sock])
        supervisor.run()
    else:
        server.run()
