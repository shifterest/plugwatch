from dynaconf import Dynaconf, Validator

settings = Dynaconf(
    envvar_prefix="DYNACONF",
    settings_files=["settings.toml", ".secrets.toml"],
    validators=[
        Validator(
            "userAgent",
            default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36",
        ),
        Validator(
            "precedence",
            default=[
                "directUrls",
                "github",
                "jenkins",
                "spigot",
                "bukkit",
            ],
        ),
        Validator("pluginsPath", default="plugins"),
        Validator("autoDownloads", default=False),
        Validator("forceRedownload", default=False),
        Validator("preferStable", default=True),
        Validator("preferActions", default=False),
        Validator("delay", default=0),
    ],
)

# `envvar_prefix` = export envvars with `export DYNACONF_FOO=bar`.
# `settings_files` = Load these files in the order.
