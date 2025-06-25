from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix="PURURU",
    settings_files=[
        "pururu/settings.test.toml",
        "pururu/settings.local.toml",
        "pururu/.secrets.local.toml",
        "/home/nonroot/app/config/settings.toml",
        "/home/nonroot/app/config/.secrets.toml",
    ],
    environments=True,
    env_switcher="PURURU_APP_ENV"
)
