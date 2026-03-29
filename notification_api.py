from flask import Blueprint, request, jsonify
from .notifications import send_notifications
from .data_loader import get_appointment_by_id


notification_bp = Blueprint("notification_bp", __name__)

@notification_bp.route("/api/send-confirmation", methods=["POST"])
def send_confirmation():
    data = request.get_json()
    appointment_id = data.get("appointment_id")

    if not appointment_id:
        return jsonify({"dashboard_status": "Appointment ID missing"}), 400

    appointment = get_appointment_by_id(appointment_id)

    if not appointment:
        return jsonify({"dashboard_status": "Appointment not found"}), 404

    result = send_notifications(appointment)

    return jsonify(result)
