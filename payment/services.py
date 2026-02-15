from flask import Blueprint, render_template, redirect, session, flash

import  midtransclient
import uuid
from flask import current_app


def get_snap():
    return midtransclient.Snap(
        is_production=current_app.config["MIDTRANS_IS_PRODUCTION"],
        server_key=current_app.config["MIDTRANS_SERVER_KEY"],
        client_key=current_app.config["MIDTRANS_CLIENT_KEY"]
    )


def create_transaction_payload(user, trx, package_name):
    return {
        "transaction_details": {
            "order_id": trx.gateway_ref,
            "gross_amount": trx.amount
        },
        "customer_details": {
            "email": user.email
        },
        "item_details": [{
            "id": package_name,
            "price": trx.amount,
            "quantity": 1,
            "name": f"{trx.plan} plan purchase"
        }]
    }