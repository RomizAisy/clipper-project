from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db



#DATABASE USER MODEL
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(40), unique = True, nullable = False)
    email = db.Column(db.String(100), unique = True, nullable = False)
    password_hash = db.Column(db.String(200), nullable = False)
    tokens = db.Column(db.Integer, default = 0)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'{self.username}'

