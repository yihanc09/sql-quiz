"""Two-variable deployment and private configuration regressions."""

import os
from unittest.mock import MagicMock, Mock

import psycopg
import pytest
from cryptography.fernet import Fernet

import configure_runtime
import database
import runtime_config as config


@pytest.fixture
def private_config(monkeypatch):
    for name in (*config.PRIVATE_SETTINGS, "DATABASE_URL", "DATABASE_PASSWORD"):
        monkeypatch.delenv(name, raising=False)
    config._private_settings.cache_clear()
    values = {"SUPABASE_URL": "https://test.supabase.co", "SUPABASE_ANON_KEY": "public-key",
              "QUIZ_DATABASE_URL": "postgresql://quiz_reader:reader-password@db:5432/postgres",
              "APP_SESSION_KEY": Fernet.generate_key().decode()}
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.return_value = (values,)
    connect = Mock(return_value=conn)
    monkeypatch.setattr(config, "backend_connection", connect)
    yield monkeypatch, values, conn, connect
    config._private_settings.cache_clear()


def test_backend_password_is_a_connection_option(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres.project@pooler:5432/postgres?sslmode=require")
    monkeypatch.setenv("DATABASE_PASSWORD", "p@ss:word/?'special")
    connect = Mock()
    monkeypatch.setattr(config.psycopg, "connect", connect)
    config.backend_connection()
    url = connect.call_args.args[0]
    assert "p@ss" not in url
    assert connect.call_args.kwargs == {"connect_timeout": 10, "password": "p@ss:word/?'special"}


def test_deployment_loads_all_settings_without_extra_environment_variables(private_config):
    _, values, conn, connect = private_config
    for name, value in values.items():
        assert config.get_setting(name) == value
    connect.assert_called_once()
    conn.execute.assert_any_call("SET TRANSACTION READ ONLY")
    conn.execute.assert_any_call(
        "SELECT settings FROM quiz_private.runtime_config WHERE singleton = %s", (True,)
    )


def test_legacy_local_settings_do_not_require_configuration_table(private_config):
    monkeypatch, _, _, connect = private_config
    monkeypatch.setenv("SUPABASE_URL", "https://local.supabase.co")
    assert config.get_setting("SUPABASE_URL") == "https://local.supabase.co"
    connect.assert_not_called()


def test_uninitialized_private_table_returns_actionable_error(private_config):
    _, _, conn, _ = private_config
    conn.execute.return_value.fetchone.return_value = None
    with pytest.raises(config.RuntimeConfigError, match="configure_runtime.py --init"):
        config.get_setting("SUPABASE_URL")


def test_database_error_does_not_expose_credentials(private_config):
    _, _, _, connect = private_config
    connect.side_effect = psycopg.OperationalError("password=private-password host=private-host")
    with pytest.raises(config.RuntimeConfigError) as error:
        config.get_setting("SUPABASE_URL")
    assert "private-password" not in str(error.value)
    assert "private-host" not in str(error.value)


def test_student_connection_never_uses_admin_password(monkeypatch):
    reader_url = "postgresql://quiz_reader:reader-password@pooler:5432/postgres"
    monkeypatch.setenv("DATABASE_PASSWORD", "administrator-password")
    monkeypatch.setattr(database, "get_setting", Mock(return_value=reader_url))
    connect = Mock()
    backend = Mock()
    monkeypatch.setattr(database.psycopg, "connect", connect)
    monkeypatch.setattr(database, "backend_connection", backend)
    database.get_connection(read_only=True)
    connect.assert_called_once_with(reader_url, connect_timeout=10)
    backend.assert_not_called()
    database.get_connection(read_only=False)
    backend.assert_called_once_with()


def test_initialization_preserves_existing_credentials_and_session_key(private_config):
    _, _, conn, _ = private_config
    assert configure_runtime.seed_settings(conn) is False
    assert conn.execute.call_count == 1


def test_initialization_binds_configuration_values_and_generates_session_key(private_config):
    monkeypatch, values, conn, _ = private_config
    conn.execute.return_value.fetchone.return_value = None
    for name, value in values.items():
        if name != "APP_SESSION_KEY":
            monkeypatch.setenv(name, value)
    assert configure_runtime.seed_settings(conn) is True
    query, params = conn.execute.call_args.args
    stored = params[1].obj
    assert "reader-password" not in query
    assert stored["QUIZ_DATABASE_URL"] == values["QUIZ_DATABASE_URL"]
    assert stored["APP_SESSION_KEY"]
    Fernet(stored["APP_SESSION_KEY"].encode())


def test_backup_initialization_does_not_replace_deployment_connection(private_config):
    monkeypatch, values, conn, _ = private_config
    monkeypatch.setenv("DATABASE_URL", "postgresql://current-backend@pooler/postgres")
    monkeypatch.setenv("DATABASE_PASSWORD", "current-password")
    conn.execute.return_value.fetchone.return_value = None
    assert configure_runtime.seed_settings(conn, values) is True
    assert conn.execute.call_args.args[1][1].obj == values
    assert os.environ["DATABASE_URL"] == "postgresql://current-backend@pooler/postgres"
    assert os.environ["DATABASE_PASSWORD"] == "current-password"
