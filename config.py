import os 
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    #Security
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")

    #Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR, "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Session
    PERMANENT_SESSION_LIFETIME = timedelta(days = 7)

    #Payment Midtrans
    MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
    MIDTRANS_CLIENT_KEY = os.getenv("MIDTRANS_CLIENT_KEY")
    MIDTRANS_IS_PRODUCTION = False
