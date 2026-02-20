_app = None


def get_app():
    global _app

    if _app is None:
        from app import create_app
        _app = create_app()

    return _app