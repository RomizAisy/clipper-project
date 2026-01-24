import uuid, hashlib
from flask import Blueprint, request, jsonify, session, redirect, render_template
from extensions import db
from models import User, Transaction
from .services import get_snap, create_transaction_payload
from flask import current_app

payment_bp = Blueprint("payment", __name__)

PACKAGES = {
    "starter": {"tokens": 50, "price": 20000},
    "pro": {"tokens": 200, "price": 70000},
}

@payment_bp.route("/buytoken")
def buytokenpage():
    if "user_id" not in session:
        return redirect("/login")

    return render_template(
        "buytoken.html",
        client_key=current_app.config["MIDTRANS_CLIENT_KEY"]
    )

@payment_bp.route("/create-transaction", methods=["POST"])
def buy_tokens():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    package = request.json.get("package")
    if package not in PACKAGES:
        return jsonify({"error": "invalid package"}), 400

    user = User.query.filter_by(username=session["username"]).first()
    if not user:
        return jsonify({"error": "user not found"}), 404

    trx = Transaction(
        user_id=user.id,
        tokens=PACKAGES[package]["tokens"],
        amount=PACKAGES[package]["price"],
        status="pending"
    )
    db.session.add(trx)
    db.session.commit()

    trx.gateway_ref = f"TOKEN-{trx.id}-{uuid.uuid4().hex[:8]}"
    db.session.commit()

    snap = get_snap()
    payload = create_transaction_payload(user, trx, package)
    response = snap.create_transaction(payload)

    return jsonify({"snap_token": response["token"]})


def verify_midtrans_signature(payload):
    server_key = current_app.config["MIDTRANS_SERVER_KEY"]
    raw = (
        payload["order_id"]
        + payload["status_code"]
        + payload["gross_amount"]
        + server_key
    )
    signature = hashlib.sha512(raw.encode()).hexdigest()
    return signature == payload["signature_key"]


@payment_bp.route("/midtrans/webhook", methods=["POST"])
def midtrans_webhook():
    payload = request.json

    if not verify_midtrans_signature(payload):
        return "invalid signature", 403

    trx = Transaction.query.filter_by(
        gateway_ref=payload["order_id"]
    ).first()

    if not trx:
        return "not found", 404

    if trx.status == "paid":
        return "ok", 200

    if payload["transaction_status"] == "settlement":
        user = User.query.get(trx.user_id)
        user.tokens += trx.tokens
        trx.status = "paid"

    elif payload["transaction_status"] in ["cancel", "expire", "deny"]:
        trx.status = "failed"

    db.session.commit()
    return "ok", 200

@payment_bp.route('/payment-success')
def payment_success():
    return render_template("paymentSuccess.html")