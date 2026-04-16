import logging
import os
import sys

from pydantic_settings import BaseSettings


env_settings = dict()

if "INSTANCE_CONNECTION_NAME" in os.environ:
    env_settings["instance_connection_name"] = os.environ.get("INSTANCE_CONNECTION_NAME")
if "IAM_USER" in os.environ:
    env_settings["iam_user"] = os.environ.get("IAM_USER")
if "DB" in os.environ:
    env_settings["db"] = os.environ.get("DB")
if "PROJECT_ID" in os.environ:
    env_settings["project_id"] = os.environ.get("PROJECT_ID")
if "DATA_KEY" in os.environ:
    env_settings["data_key"] = os.environ.get("DATA_KEY")
if "API_WORKERS" in os.environ:
    env_settings["api_workers"] = os.environ.get("API_WORKERS")
if "POSTGRES_KEY" in os.environ:
    env_settings["postgres_key"] = os.environ.get("POSTGRES_KEY")
if "CONNECT_TYPE" in os.environ:
    env_settings["connect_type"] = os.environ.get("CONNECT_TYPE")
if "RUN_BOOTSTRAP_ON_STARTUP" in os.environ:
    env_settings["run_bootstrap_on_startup"] = os.environ.get("RUN_BOOTSTRAP_ON_STARTUP")
if "LOCK_KEY" in os.environ:
    env_settings["lock_key"] = os.environ.get("LOCK_KEY")
if "AUTH_USERINFO_URL" in os.environ:
    env_settings["auth_userinfo_url"] = os.environ.get("AUTH_USERINFO_URL")
if "AUTH_INTROSPECTION_URL" in os.environ:
    env_settings["auth_introspection_url"] = os.environ.get("AUTH_INTROSPECTION_URL")
if "AUTH_JWKS_URL" in os.environ:
    env_settings["auth_jwks_url"] = os.environ.get("AUTH_JWKS_URL")
if "AUTH_ISSUER" in os.environ:
    env_settings["auth_issuer"] = os.environ.get("AUTH_ISSUER")
if "AUTH_AUDIENCE" in os.environ:
    env_settings["auth_audience"] = os.environ.get("AUTH_AUDIENCE")
if "AUTH_JWT_ALGORITHMS" in os.environ:
    env_settings["auth_jwt_algorithms"] = os.environ.get("AUTH_JWT_ALGORITHMS")
if "AUTH_CLIENT_ID" in os.environ:
    env_settings["auth_client_id"] = os.environ.get("AUTH_CLIENT_ID")
if "AUTH_CLIENT_SECRET" in os.environ:
    env_settings["auth_client_secret"] = os.environ.get("AUTH_CLIENT_SECRET")
if "AUTH_GROUPS_CLAIM" in os.environ:
    env_settings["auth_groups_claim"] = os.environ.get("AUTH_GROUPS_CLAIM")
if "AUTH_USER_ID_CLAIM" in os.environ:
    env_settings["auth_user_id_claim"] = os.environ.get("AUTH_USER_ID_CLAIM")
if "AUTH_USER_NAME_CLAIM" in os.environ:
    env_settings["auth_user_name_claim"] = os.environ.get("AUTH_USER_NAME_CLAIM")


class Settings(BaseSettings):
    instance_connection_name: str = env_settings.get("instance_connection_name", "")
    iam_user: str = env_settings.get("iam_user", "")
    db: str = env_settings.get("db", "")
    project_id: str = env_settings.get("project_id", "")
    data_key: str = env_settings.get("data_key", "")
    api_workers: int = int(env_settings.get("api_workers", 1))
    postgres_key: str = env_settings.get("postgres_key", "")
    connect_type: str = env_settings.get("connect_type", "")
    run_bootstrap_on_startup: bool = env_settings.get("run_bootstrap_on_startup", True)
    lock_key: int = env_settings.get("lock_key", 922337203685477580)
    auth_userinfo_url: str = env_settings.get("auth_userinfo_url", "")
    auth_introspection_url: str = env_settings.get("auth_introspection_url", "")
    auth_jwks_url: str = env_settings.get("auth_jwks_url", "")
    auth_issuer: str = env_settings.get("auth_issuer", "")
    auth_audience: str = env_settings.get("auth_audience", "")
    auth_jwt_algorithms: str = env_settings.get("auth_jwt_algorithms", "RS256")
    auth_client_id: str = env_settings.get("auth_client_id", "")
    auth_client_secret: str = env_settings.get("auth_client_secret", "")
    auth_groups_claim: str = env_settings.get("auth_groups_claim", "groups")
    auth_user_id_claim: str = env_settings.get("auth_user_id_claim", "sub")
    auth_user_name_claim: str = env_settings.get("auth_user_name_claim", "preferred_username")


settings = Settings()


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s.%(funcName)s:%(lineno)d %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
