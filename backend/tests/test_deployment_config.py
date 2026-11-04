"""Deployment configuration: the two .env templates, the production Docker stack and the startup guard
against template passwords. Pure file/settings checks: no database, network or Docker needed."""

import ipaddress
import re
from urllib.parse import urlparse

import pytest
import yaml

from backend.app.config import ROOT_DIR, Settings, security_settings_errors

DEV_TEMPLATE = ROOT_DIR / ".env.example"
PROD_TEMPLATE = ROOT_DIR / ".env.production.example"
PROD_COMPOSE = ROOT_DIR / "docker-compose.prod.yml"
BACKEND_DOCKERFILE = ROOT_DIR / "backend" / "Dockerfile"
FRONTEND_DOCKERFILE = ROOT_DIR / "frontend" / "Dockerfile"
CADDYFILE = ROOT_DIR / "frontend" / "Caddyfile"
ASSIGNMENT = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$", re.MULTILINE)
SECRET_KEYS = ("JWT_SECRET", "ADMIN_API_KEY", "SUPER_ADMIN_EMAIL", "SUPER_ADMIN_PASSWORD", "GROQ_API_KEY",
               "GEMINI_API_KEY", "OPENROUTER_API_KEY", "WEB_SEARCH_API_KEY")
PRIVATE_JWT = "x" * 48


def _pairs(path):
    return ASSIGNMENT.findall(path.read_text(encoding="utf-8"))


def _values(path):
    return {key: value.strip() for key, value in _pairs(path)}


def _compose_variables(path):
    return set(re.findall(r"\$\{([A-Za-z_][A-Za-z0-9_]*)", path.read_text(encoding="utf-8")))


def _settings_from(values, **overrides):
    """Settings built only from the template values (init arguments beat the process environment)."""
    return Settings(_env_file=None, **{**values, **overrides})


# --- production template -------------------------------------------------------------------------------

def test_production_template_has_no_duplicate_keys():
    keys = [key for key, _ in _pairs(PROD_TEMPLATE)]
    assert len(keys) == len(set(keys))


def test_production_template_covers_every_production_compose_variable():
    assert _compose_variables(PROD_COMPOSE) <= set(_values(PROD_TEMPLATE))


def test_every_production_template_key_is_used():
    # COMPOSE_FILE is read by the docker compose CLI itself.
    used = _compose_variables(PROD_COMPOSE) | set(Settings.model_fields) | {"COMPOSE_FILE"}
    assert [key for key in _values(PROD_TEMPLATE) if key not in used] == []


def test_production_env_selects_the_production_compose_file():
    assert _values(PROD_TEMPLATE)["COMPOSE_FILE"] == PROD_COMPOSE.name


def test_production_template_ships_no_secrets():
    values = _values(PROD_TEMPLATE)
    assert {key: values[key] for key in SECRET_KEYS if values.get(key)} == {}


def test_production_template_targets_the_compose_database_and_https_origin():
    values = _values(PROD_TEMPLATE)
    url = urlparse(values["DATABASE_URL"])
    assert (url.scheme, url.hostname, url.port, url.path) == ("postgresql", "postgres", 5432, "/sap_brim_ai")
    assert url.username == "sap_brim_ai"
    assert url.password == values["SAP_BRIM_DB_PASSWORD"]
    assert values["ENVIRONMENT"] == "production"
    assert values["ALLOWED_ORIGINS"] == f"https://{values['APP_DOMAIN']}"
    assert values["INCLUDE_SELF_AUTHORED_DOCS"] == "False"


def test_untouched_production_template_is_refused_at_startup():
    values = _values(PROD_TEMPLATE)
    errors = " ".join(security_settings_errors(_settings_from(values)))
    assert "JWT_SECRET" in errors
    assert "DATABASE_URL still uses the template database password" in errors


def test_completed_production_template_passes_the_startup_checks():
    values = _values(PROD_TEMPLATE)
    settings = _settings_from(
        values,
        JWT_SECRET=PRIVATE_JWT,
        DATABASE_URL=values["DATABASE_URL"].replace("change-me-app-password", "Q2v8_private-db-pass"),
        SUPER_ADMIN_EMAIL="admin@assistant.example.com",
        SUPER_ADMIN_PASSWORD="a-private-admin-password",
    )
    assert security_settings_errors(settings) == []
    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",")]
    assert all(origin.startswith("https://") and "localhost" not in origin for origin in origins)


# --- development template ------------------------------------------------------------------------------

def test_development_template_database_url_matches_the_compose_values():
    values = _values(DEV_TEMPLATE)
    url = urlparse(values["DATABASE_URL"])
    assert url.hostname == "127.0.0.1"
    assert url.port == int(values["POSTGRES_HOST_PORT"])
    assert url.password == values["SAP_BRIM_DB_PASSWORD"]
    assert values["ENVIRONMENT"] == "development"


def test_development_template_ships_no_secrets():
    values = _values(DEV_TEMPLATE)
    assert {key: values[key] for key in SECRET_KEYS if values.get(key)} == {}


def test_both_templates_use_the_same_embedding_model():
    # Vectors record their model name: a mismatch makes a restored development database unusable.
    assert _values(DEV_TEMPLATE)["EMBEDDING_MODEL"] == _values(PROD_TEMPLATE)["EMBEDDING_MODEL"]


# --- startup guard against template passwords ----------------------------------------------------------

@pytest.mark.parametrize("password", ["change-me-app-password", "CHANGE_ME", "changeme123"])
def test_production_refuses_a_template_database_password(password):
    settings = _settings_from({}, ENVIRONMENT="production", JWT_SECRET=PRIVATE_JWT,
                              DATABASE_URL=f"postgresql://sap_brim_ai:{password}@postgres:5432/sap_brim_ai")
    assert any("template database password" in error for error in security_settings_errors(settings))


def test_production_refuses_a_template_admin_password():
    settings = _settings_from({}, ENVIRONMENT="production", JWT_SECRET=PRIVATE_JWT,
                              DATABASE_URL="postgresql://sap_brim_ai:Q2v8_private@postgres:5432/sap_brim_ai",
                              SUPER_ADMIN_EMAIL="admin@example.com", SUPER_ADMIN_PASSWORD="change-me-admin-pass")
    assert any("SUPER_ADMIN_PASSWORD still uses a template value" in e for e in security_settings_errors(settings))


def test_development_keeps_accepting_the_template_database_password():
    settings = _settings_from({}, ENVIRONMENT="development", JWT_SECRET=PRIVATE_JWT, ADMIN_API_KEY="",
                              SUPER_ADMIN_EMAIL="", SUPER_ADMIN_PASSWORD="",
                              DATABASE_URL="postgresql://sap_brim_ai:change-me-app-password@127.0.0.1:5434/sap_brim_ai")
    assert security_settings_errors(settings) == []


# --- Docker stack ------------------------------------------------------------------------------------

def _compose():
    return yaml.safe_load(PROD_COMPOSE.read_text(encoding="utf-8"))


def test_only_the_web_container_is_published():
    services = _compose()["services"]
    assert set(services) == {"postgres", "backend", "web"}
    assert "ports" not in services["postgres"]
    assert "ports" not in services["backend"]
    assert services["web"]["ports"]


def test_backend_trusts_only_private_proxy_ranges_and_does_not_auto_migrate_in_process():
    backend = _compose()["services"]["backend"]
    assert backend["environment"]["AUTO_MIGRATE"] == "False"
    networks = [ipaddress.ip_network(part.strip()) for part in backend["environment"]["TRUSTED_PROXIES"].split(",")]
    assert networks and all(network.is_private for network in networks)
    assert backend["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert "./knowledge_base:/app/knowledge_base" in backend["volumes"]


def test_database_volume_is_named_and_kept():
    compose = _compose()
    assert "pgdata:/var/lib/postgresql/data" in compose["services"]["postgres"]["volumes"]
    assert "pgdata" in compose["volumes"]


def test_backend_image_migrates_then_serves_one_worker_as_an_unprivileged_user():
    dockerfile = BACKEND_DOCKERFILE.read_text(encoding="utf-8")
    assert re.search(r"^USER app$", dockerfile, re.MULTILINE)
    command = dockerfile[dockerfile.index("CMD"):]
    assert command.index("alembic -c backend/alembic.ini upgrade head") < command.index("uvicorn backend.app.main:app")
    assert "--workers 1" in command
    assert "download.pytorch.org/whl/cpu" in dockerfile


def test_backend_build_context_excludes_secrets_and_local_data():
    lines = [line.strip() for line in (ROOT_DIR / ".dockerignore").read_text(encoding="utf-8").splitlines()]
    rules = [line for line in lines if line and not line.startswith("#")]
    assert rules[0] == "*" and "!backend/" in rules
    assert "backend/**/.env" in rules and "backend/**/.env.*" in rules
    assert not any(rule.startswith("!") and ".env" in rule for rule in rules)


def test_web_image_builds_the_app_and_proxies_the_api_with_streaming():
    dockerfile = FRONTEND_DOCKERFILE.read_text(encoding="utf-8")
    assert "npm ci" in dockerfile and "npm run build" in dockerfile
    caddyfile = CADDYFILE.read_text(encoding="utf-8")
    api_block = caddyfile[caddyfile.index("handle /api/*"):caddyfile.index("handle /health")]
    assert "reverse_proxy backend:8000" in api_block and "flush_interval -1" in api_block
    assert "try_files {path} /index.html" in caddyfile
    assert "frame-ancestors 'none'" in caddyfile
