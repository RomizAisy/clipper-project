from extensions import db


class Transaction(db.Model):
    __tablename__ = "transactions"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    plan = db.Column(db.String(20))
#    tokens = db.Column(db.Integer, nullable=False)   # tokens bought
    amount = db.Column(db.Integer, nullable=False)   # price paid

    status = db.Column(
        db.String(20),
        nullable=False,
        default="pending"  # pending, paid, failed
    )

    gateway_ref = db.Column(db.String(100), unique=True)

    created_at = db.Column(
        db.DateTime,
        default=db.func.now()
    )

    user = db.relationship("User", backref="transactions")