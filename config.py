import os 
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    #Security
    SECRET_KEY = os.getenv("SECRET_KEY")

    #Mail
    MAIL_SERVER = os.getenv("MAIL_SERVER")
    MAIL_PORT = int(os.getenv("MAIL_PORT",587))
    MAIL_USERNAME = os.getenv("MAIL_USERNAME")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_DEFAULT_SENDER = os.getenv("MAIL_DEFAULT_SENDER")

    #Database
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "sqlite:///" + os.path.join(BASE_DIR,"instance", "app.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #Session
    PERMANENT_SESSION_LIFETIME = timedelta(days = 7)

    #Payment Midtrans
    MIDTRANS_SERVER_KEY = os.getenv("MIDTRANS_SERVER_KEY")
    MIDTRANS_CLIENT_KEY = os.getenv("MIDTRANS_CLIENT_KEY")
    MIDTRANS_IS_PRODUCTION = False
