from flask import Flask
from app.config import Config
from app.extensions import cache


def create_app(test_config: dict | None = None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    cache.init_app(app)

    from app.routes.agent_routes import agent_bp
    from app.routes.pokemon_routes import pokemon_bp
    
    app.register_blueprint(agent_bp, url_prefix="/agent")
    app.register_blueprint(pokemon_bp)

    return app
