from flask import Flask
from app.config import config


def create_app(config_name='production'):
    app = Flask(__name__,
                template_folder='../templates',
                static_folder='../static')
    app.config.from_object(config[config_name])

    from app.db import close_db
    app.teardown_appcontext(close_db)

    from app.routes import register_blueprints
    register_blueprints(app)

    from app.db import ensure_category_columns
    with app.app_context():
        ensure_category_columns()

    return app
