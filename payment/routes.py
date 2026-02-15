import uuid, hashlib
from flask import Blueprint, request, jsonify, session, redirect, render_template
from extensions import db
from models import User, Transaction
from .services import get_snap, create_transaction_payload
from flask import current_app
from helper.plans import PLANS

import logging

payment_bp = Blueprint("payment", __name__)

PAID_PLANS = ["starter", "pro", "unlimited"]
PLAN_ORDER = ["free", "starter", "pro", "unlimited"]

@payment_bp.route("/price")
def price():
    return render_template("price.html")

@payment_bp.route("/buytoken")
def buytokenpage():
    if "user_id" not in session:
        return redirect("/login")

    user = User.query.get(session["user_id"])

    return render_template(
        "buytoken.html",
        client_key=current_app.config["MIDTRANS_CLIENT_KEY"],
        current_plan=user.plan
    )
@payment_bp.route("/create-transaction", methods=["POST"])
def buy_tokens():
    if "user_id" not in session:
        return jsonify({"error": "unauthorized"}), 401

    package = request.json.get("package")

    if package not in PAID_PLANS:
        return jsonify({"error": "invalid package"}), 400

    user = User.query.get(session["user_id"])
    if not user:
        return jsonify({"error": "user not found"}), 404

    # ✅ upgrade-only rule
    if PLAN_ORDER.index(package) <= PLAN_ORDER.index(user.plan):
        return jsonify({
            "error": "You already have this or higher plan"
        }), 400

    plan_config = PLANS[package]

    trx = Transaction(
        user_id=user.id,
        plan=package,
        amount=plan_config["price"],
        status="pending"
    )

    db.session.add(trx)
    db.session.commit()

    trx.gateway_ref = f"PLAN-{trx.id}-{uuid.uuid4().hex[:8]}"
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
    logging.info(f"Webhook received: {payload}")

    if not verify_midtrans_signature(payload):
        logging.warning("Invalid signature")
        return "invalid signature", 403

    trx = Transaction.query.filter_by(gateway_ref=payload["order_id"]).first()
    if not trx:
        logging.warning("Transaction not found")
        return "not found", 404

    if trx.status == "paid":
        logging.info("Transaction already paid")
        return "ok", 200

    if payload["transaction_status"] == "settlement":
        user = User.query.get(trx.user_id)
        plan_config = PLANS[trx.plan]
        user.plan = trx.plan
        user.daily_limit = plan_config["daily_limit"]
        user.used_today = 0
        trx.status = "paid"
        logging.info(f"Transaction {trx.gateway_ref} marked as paid")

    elif payload["transaction_status"] in ["cancel", "expire", "deny"]:
        trx.status = "failed"
        logging.info(f"Transaction {trx.gateway_ref} marked as failed")

    db.session.commit()
    return "ok", 200

@payment_bp.route('/payment-success')
def payment_success():
    return render_template("paymentSuccess.html")