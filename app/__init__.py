from flask import Flask

from .routes import bp


def create_app() -> Flask:
    app = Flask(
        __name__,
        template_folder="../templates",
        static_folder="../static",
    )
    app.config["SECRET_KEY"] = "dev"
    app.register_blueprint(bp)
    return app
