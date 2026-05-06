import logging
import os
import sys

from pydantic_settings import BaseSettings


env_settings = dict()
is_local_env = os.environ.get("ENV") == "local"

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
if "AUTH_JWKS_URL" in os.environ:
    env_settings["auth_jwks_url"] = os.environ.get("AUTH_JWKS_URL")
if "AUTH_ISSUER" in os.environ:
    env_settings["auth_issuer"] = os.environ.get("AUTH_ISSUER")
if "AUTH_AUDIENCE" in os.environ:
    env_settings["auth_audience"] = os.environ.get("AUTH_AUDIENCE")
if "AUTH_JWT_ALGORITHMS" in os.environ:
    env_settings["auth_jwt_algorithms"] = os.environ.get("AUTH_JWT_ALGORITHMS")
if "AUTH_GROUPS_CLAIM" in os.environ:
    env_settings["auth_groups_claim"] = os.environ.get("AUTH_GROUPS_CLAIM")
if "AUTH_USER_ID_CLAIM" in os.environ:
    env_settings["auth_user_id_claim"] = os.environ.get("AUTH_USER_ID_CLAIM")
if "AUTH_USER_NAME_CLAIM" in os.environ:
    env_settings["auth_user_name_claim"] = os.environ.get("AUTH_USER_NAME_CLAIM")
if "AUTH_LOGIN_URL" in os.environ:
    env_settings["auth_login_url"] = os.environ.get("AUTH_LOGIN_URL")
if "AUTH_ENABLE_MOCK_LOGIN" in os.environ:
    env_settings["auth_enable_mock_login"] = os.environ.get("AUTH_ENABLE_MOCK_LOGIN")
if "AUTH_MOCK_USERS_FILE" in os.environ:
    env_settings["auth_mock_users_file"] = os.environ.get("AUTH_MOCK_USERS_FILE")
if "SESSION_COOKIE_NAME" in os.environ:
    env_settings["session_cookie_name"] = os.environ.get("SESSION_COOKIE_NAME")
if "SESSION_TTL_SECONDS" in os.environ:
    env_settings["session_ttl_seconds"] = os.environ.get("SESSION_TTL_SECONDS")
if "SESSION_COOKIE_SECURE" in os.environ:
    env_settings["session_cookie_secure"] = os.environ.get("SESSION_COOKIE_SECURE")
if "SESSION_COOKIE_SAMESITE" in os.environ:
    env_settings["session_cookie_samesite"] = os.environ.get("SESSION_COOKIE_SAMESITE")
if "SESSION_COOKIE_DOMAIN" in os.environ:
    env_settings["session_cookie_domain"] = os.environ.get("SESSION_COOKIE_DOMAIN")
if "CORS_ALLOW_ORIGINS" in os.environ:
    env_settings["cors_allow_origins"] = os.environ.get("CORS_ALLOW_ORIGINS")


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
    auth_jwks_url: str = env_settings.get("auth_jwks_url", "")
    auth_issuer: str = env_settings.get("auth_issuer", "")
    auth_audience: str = env_settings.get("auth_audience", "")
    auth_jwt_algorithms: str = env_settings.get("auth_jwt_algorithms", "RS256")
    auth_groups_claim: str = env_settings.get("auth_groups_claim", "groups")
    auth_user_id_claim: str = env_settings.get("auth_user_id_claim", "sub")
    auth_user_name_claim: str = env_settings.get("auth_user_name_claim", "preferred_username")
    auth_login_url: str = env_settings.get("auth_login_url", "")
    auth_enable_mock_login: bool = str(env_settings.get("auth_enable_mock_login", "false")).lower() == "true"
    auth_mock_users_file: str = env_settings.get("auth_mock_users_file", "dev/auth/mock_users.json")
    session_cookie_name: str = env_settings.get("session_cookie_name", "dds_session")
    session_ttl_seconds: int = int(env_settings.get("session_ttl_seconds", 28800))
    session_cookie_secure: bool = str(env_settings.get("session_cookie_secure", "false" if is_local_env else "true")).lower() == "true"
    session_cookie_samesite: str = env_settings.get("session_cookie_samesite", "lax" if is_local_env else "none")
    session_cookie_domain: str = env_settings.get("session_cookie_domain", "")
    cors_allow_origins: str = env_settings.get("cors_allow_origins", "")


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
