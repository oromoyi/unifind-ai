def register_blueprints(app):
    from . import admin, ai, auth, claims, items, notifications, public
    for mod in (auth, public, items, claims, notifications, admin, ai):
        app.register_blueprint(mod.bp)
