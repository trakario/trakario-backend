import logging

from pydantic.env_settings import BaseSettings

from .logs import setup_logging


class Settings(BaseSettings):
    debug: bool = False

    frontend_url: str

    imap_server: str
    imap_email: str
    imap_password: str
    imap_folder: str

    auth_token: str

    db_url = "postgres://trakario:trakario@localhost:5432/trakario"

    class Config:
        env_file = ".env"


config = Settings()
setup_logging(logging.DEBUG if config.debug else logging.INFO)
