from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import csrf
from app import db
from app.models import Salon, Assinaturas
from app.config import Config

billing_bp = Blueprint("billing", __name__, url_prefix="/api/billing")


def verificar_token_n8n():
    """
    Protege a rota que recebe os eventos enviados pelo n8n.
    """

    auth = request.headers.get("Authorization", "")

    expected = f"{Config.KIWIFY_WEBHOOK_TOKEN}"

    return auth == expected

def parse_kiwify_datetime(value):
    """
    Converte datas recebidas da Kiwify/n8n.

    Exemplos:
    2026-08-17 11:15
    19/08/2026 11:14
    2026-08-17 11:15:00
    19/08/2026 11:14:00
    """

    if not value:
        return None

    if isinstance(value, datetime):
        return value

    formats = [
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except (ValueError, TypeError):
            continue

    return None


def localizar_salao_por_email(email):
    """
    Localiza o salão usando o e-mail informado na compra.
    """

    email = (email or "").strip().lower()

    if not email:
        return None

    return Salon.query.filter(
        db.func.lower(Salon.email) == email
    ).first()


@billing_bp.route("/kiwify", methods=["POST"])
@csrf.exempt
def kiwify_webhook():
    """
    Recebe do n8n os eventos enviados pela Kiwify.
    """

    # ==========================================================
    # SEGURANÇA
    # ==========================================================

    if not verificar_token_n8n():
        return jsonify({
            "success": False,
            "error": "Não autorizado"
        }), 401

    # ==========================================================
    # JSON
    # ==========================================================

    data = request.get_json(silent=True)

    if not data:
        return jsonify({
            "success": False,
            "error": "JSON inválido"
        }), 400

    # ==========================================================
    # DADOS PRINCIPAIS
    # ==========================================================

    order_id = data.get("order_id")
    order_ref = data.get("order_ref")

    event = data.get("event")
    status = data.get("status")

    payment_method = data.get("payment_method")

    amount = data.get("amount")
    kiwify_fee = data.get("kiwify_fee")
    net_amount = data.get("net_amount")

    product_id = data.get("product_id")
    product_name = data.get("product_name")

    customer_name = data.get("customer_name")

    customer_email = (
        data.get("customer_email") or ""
    ).strip().lower()

    customer_phone = data.get("customer_phone")

    pix_code = data.get("pix_code")
    pix_expiration = parse_kiwify_datetime(
        data.get("pix_expiration")
    )

    approved_date = parse_kiwify_datetime(
        data.get("approved_date")
    )

    print(
        "\n========== KIWIFY ==========\n"
        f"event: {event}\n"
        f"order_id: {order_id}\n"
        f"status: {status}\n"
        f"customer_email: {customer_email}\n"
        f"amount: {amount}\n"
        f"payment_method: {payment_method}\n"
        "============================\n"
    )

    # ==========================================================
    # VALIDAÇÕES
    # ==========================================================

    if not order_id:
        return jsonify({
            "success": False,
            "error": "order_id não informado"
        }), 400

    if not event:
        return jsonify({
            "success": False,
            "error": "event não informado"
        }), 400

    try:

        # ======================================================
        # PROCURA PAGAMENTO
        # ======================================================

        pagamento = Assinaturas.query.filter_by(
            order_id=order_id
        ).first()

        # ======================================================
        # 1. PIX CRIADO
        # ======================================================

        if event == "pix_created":

            criado_agora = False

            # --------------------------------------------------
            # PAGAMENTO NÃO EXISTE
            # --------------------------------------------------

            if not pagamento:

                if not customer_email:
                    return jsonify({
                        "success": False,
                        "error": (
                            "customer_email não informado "
                            "para criar o pagamento"
                        ),
                        "order_id": order_id
                    }), 400

                # ----------------------------------------------
                # LOCALIZA SALÃO
                # ----------------------------------------------

                salon = localizar_salao_por_email(
                    customer_email
                )

                if not salon:
                    return jsonify({
                        "success": False,
                        "error": (
                            "Salão não encontrado "
                            "pelo e-mail"
                        ),
                        "customer_email": customer_email,
                        "order_id": order_id
                    }), 404

                # ----------------------------------------------
                # CRIA PAGAMENTO
                # ----------------------------------------------

                pagamento = Assinaturas(
                    salon_id=salon.id,

                    order_id=order_id,
                    order_ref=order_ref,

                    product_id=product_id,
                    product_name=product_name,

                    plan=salon.plan,

                    status=status or "waiting_payment",

                    webhook_event=event,

                    payment_method=payment_method,

                    amount=amount,
                    kiwify_fee=kiwify_fee,
                    net_amount=net_amount,

                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,

                    pix_code=pix_code,
                    pix_expiration=pix_expiration,

                    created_at=datetime.utcnow()
                )

                db.session.add(pagamento)

                criado_agora = True

                print(
                    "[KIWIFY] Novo pagamento criado | "
                    f"salon_id={salon.id} | "
                    f"order_id={order_id}"
                )

            # --------------------------------------------------
            # PAGAMENTO JÁ EXISTE
            # --------------------------------------------------

            else:

                pagamento.status = (
                    status
                    or pagamento.status
                    or "waiting_payment"
                )

                pagamento.webhook_event = event

                if order_ref:
                    pagamento.order_ref = order_ref

                if payment_method:
                    pagamento.payment_method = (
                        payment_method
                    )

                if amount is not None:
                    pagamento.amount = amount

                if kiwify_fee is not None:
                    pagamento.kiwify_fee = kiwify_fee

                if net_amount is not None:
                    pagamento.net_amount = net_amount

                if product_id:
                    pagamento.product_id = product_id

                if product_name:
                    pagamento.product_name = product_name

                if customer_name:
                    pagamento.customer_name = (
                        customer_name
                    )

                if customer_email:
                    pagamento.customer_email = (
                        customer_email
                    )

                if customer_phone:
                    pagamento.customer_phone = (
                        customer_phone
                    )

                if pix_code:
                    pagamento.pix_code = pix_code

                if pix_expiration:
                    pagamento.pix_expiration = (
                        pix_expiration
                    )

                print(
                    "[KIWIFY] Pagamento existente atualizado | "
                    f"order_id={order_id}"
                )

            # --------------------------------------------------
            # COMMIT
            # --------------------------------------------------

            db.session.commit()

            return jsonify({
                "success": True,
                "message": (
                    "Pagamento criado"
                    if criado_agora
                    else "Pagamento atualizado"
                ),
                "order_id": pagamento.order_id,
                "salon_id": pagamento.salon_id,
                "status": pagamento.status
            }), 200

        # ======================================================
        # 2. PAGAMENTO APROVADO
        # ======================================================

        elif event == "order_approved":

            # --------------------------------------------------
            # SE NÃO EXISTIR, CRIA O PAGAMENTO
            # --------------------------------------------------

            if not pagamento:

                if not customer_email:
                    return jsonify({
                        "success": False,
                        "error": (
                            "Pagamento não existe e "
                            "customer_email não foi informado"
                        ),
                        "order_id": order_id
                    }), 400

                salon = localizar_salao_por_email(
                    customer_email
                )

                if not salon:
                    return jsonify({
                        "success": False,
                        "error": (
                            "Salão não encontrado "
                            "pelo e-mail"
                        ),
                        "customer_email": customer_email,
                        "order_id": order_id
                    }), 404

                pagamento = Assinaturas(
                    salon_id=salon.id,

                    order_id=order_id,
                    order_ref=order_ref,

                    product_id=product_id,
                    product_name=product_name,

                    plan=salon.plan,

                    status="paid",

                    webhook_event=event,

                    payment_method=payment_method,

                    amount=amount,
                    kiwify_fee=kiwify_fee,
                    net_amount=net_amount,

                    customer_name=customer_name,
                    customer_email=customer_email,
                    customer_phone=customer_phone,

                    pix_code=pix_code,
                    pix_expiration=pix_expiration,

                    approved_at=(
                        approved_date
                        or datetime.utcnow()
                    ),

                    created_at=datetime.utcnow()
                )

                db.session.add(pagamento)

                print(
                    "[KIWIFY] Pagamento aprovado "
                    "sem registro anterior. "
                    "Registro criado | "
                    f"salon_id={salon.id} | "
                    f"order_id={order_id}"
                )

            # --------------------------------------------------
            # IDEMPOTÊNCIA
            # --------------------------------------------------

            else:

                # Se já foi processado, não soma +30 novamente
                if pagamento.status == "paid":

                    return jsonify({
                        "success": True,
                        "message": (
                            "Pagamento já processado"
                        ),
                        "order_id": order_id,
                        "salon_id": pagamento.salon_id,
                        "status": "active"
                    }), 200

                pagamento.status = "paid"
                pagamento.webhook_event = event

                if order_ref:
                    pagamento.order_ref = order_ref

                if payment_method:
                    pagamento.payment_method = (
                        payment_method
                    )

                if amount is not None:
                    pagamento.amount = amount

                if kiwify_fee is not None:
                    pagamento.kiwify_fee = kiwify_fee

                if net_amount is not None:
                    pagamento.net_amount = (
                        net_amount
                    )

                if product_id:
                    pagamento.product_id = product_id

                if product_name:
                    pagamento.product_name = (
                        product_name
                    )

                if customer_name:
                    pagamento.customer_name = (
                        customer_name
                    )

                if customer_email:
                    pagamento.customer_email = (
                        customer_email
                    )

                if customer_phone:
                    pagamento.customer_phone = (
                        customer_phone
                    )

                if approved_date:
                    pagamento.approved_at = (
                        approved_date
                    )
                else:
                    pagamento.approved_at = (
                        datetime.utcnow()
                    )

            # --------------------------------------------------
            # LOCALIZA SALÃO
            # --------------------------------------------------

            salon = Salon.query.get(
                pagamento.salon_id
            )

            if not salon:

                db.session.rollback()

                return jsonify({
                    "success": False,
                    "error": "Salão não encontrado",
                    "salon_id": pagamento.salon_id,
                    "order_id": order_id
                }), 404

            # --------------------------------------------------
            # ATIVA ASSINATURA
            # --------------------------------------------------

            agora = datetime.utcnow()

            # Se já possui assinatura válida,
            # adiciona 30 dias ao final atual.
            if (
                salon.subscription_ends_at
                and salon.subscription_ends_at > agora
            ):
                salon.subscription_ends_at += (
                    timedelta(days=30)
                )

            else:
                salon.subscription_ends_at = (
                    agora + timedelta(days=30)
                )

            salon.subscription_status = "active"

            # --------------------------------------------------
            # COMMIT
            # --------------------------------------------------

            db.session.commit()

            print(
                "[KIWIFY] PAGAMENTO APROVADO ✅ | "
                f"salon_id={salon.id} | "
                f"order_id={order_id} | "
                f"expires={salon.subscription_ends_at}"
            )

            return jsonify({
                "success": True,
                "message": (
                    "Pagamento aprovado e "
                    "acesso liberado"
                ),
                "order_id": order_id,
                "salon_id": salon.id,
                "payment_status": "paid",
                "subscription_status": (
                    salon.subscription_status
                ),
                "subscription_ends_at": (
                    salon.subscription_ends_at.isoformat()
                )
            }), 200

        # ======================================================
        # 3. REEMBOLSO
        # ======================================================

        elif event == "order_refunded":

            if not pagamento:

                return jsonify({
                    "success": False,
                    "error": "Pagamento não encontrado",
                    "order_id": order_id
                }), 404

            pagamento.status = "refunded"
            pagamento.webhook_event = event

            pagamento.refunded_at = (
                datetime.utcnow()
            )

            salon = Salon.query.get(
                pagamento.salon_id
            )

            if salon:

                salon.subscription_status = (
                    "canceled"
                )

            db.session.commit()

            print(
                "[KIWIFY] REEMBOLSO | "
                f"order_id={order_id} | "
                f"salon_id={pagamento.salon_id}"
            )

            return jsonify({
                "success": True,
                "message": "Reembolso processado",
                "order_id": order_id
            }), 200

        # ======================================================
        # 4. CHARGEBACK
        # ======================================================

        elif event == "chargeback":

            if not pagamento:

                return jsonify({
                    "success": False,
                    "error": "Pagamento não encontrado",
                    "order_id": order_id
                }), 404

            pagamento.status = "chargeback"
            pagamento.webhook_event = event

            salon = Salon.query.get(
                pagamento.salon_id
            )

            if salon:

                salon.subscription_status = (
                    "canceled"
                )

            db.session.commit()

            print(
                "[KIWIFY] CHARGEBACK | "
                f"order_id={order_id} | "
                f"salon_id={pagamento.salon_id}"
            )

            return jsonify({
                "success": True,
                "message": "Chargeback processado",
                "order_id": order_id
            }), 200

        # ======================================================
        # 5. OUTROS EVENTOS
        # ======================================================

        else:

            # Não falha o webhook por evento ainda
            # não tratado.
            print(
                "[KIWIFY] Evento não tratado | "
                f"event={event} | "
                f"order_id={order_id}"
            )

            return jsonify({
                "success": True,
                "message": (
                    "Evento recebido, "
                    "mas ainda não processado"
                ),
                "event": event,
                "order_id": order_id
            }), 200

    except Exception:

        db.session.rollback()

        current_app.logger.exception(
            "[KIWIFY] Erro processando webhook"
        )

        return jsonify({
            "success": False,
            "error": "Erro interno ao processar pagamento"
        }), 500

# =============================================================
# STATUS DO PAGAMENTO
# =============================================================

@billing_bp.route("/status", methods=["GET"])
@login_required
def payment_status():

    order_id = request.args.get("order_id")

    if not order_id:
        return jsonify({
            "success": False,
            "error": "order_id não informado"
        }), 400

    pagamento = Assinaturas.query.filter_by(
        order_id=order_id,
        salon_id=current_user.salon_id
    ).first()

    if not pagamento:
        return jsonify({
            "success": False,
            "error": "Pagamento não encontrado"
        }), 404

    salon = current_user.salon

    return jsonify({
        "success": True,

        "payment": {
            "order_id": pagamento.order_id,
            "status": pagamento.status,
            "payment_method": pagamento.payment_method,
            "amount": pagamento.amount,
            "approved_at": (
                pagamento.approved_at.isoformat()
                if pagamento.approved_at
                else None
            )
        },

        "subscription": {
            "status": salon.subscription_status,
            "ends_at": (
                salon.subscription_ends_at.isoformat()
                if salon.subscription_ends_at
                else None
            )
        }
    }), 200
