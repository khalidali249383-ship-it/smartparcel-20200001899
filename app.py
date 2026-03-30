# -------------------------------------------------------
# SmartParcel — NET_214 Project, Spring 2026
# Author  : YOUR NAME
# ID      : 20200001899
# Email   : yourname@students.cud.ac.ae
# AWS Acc : YOUR_AWS_ACCOUNT_ID
# -------------------------------------------------------

from flask import Flask, request, jsonify
import uuid
import datetime
import socket

app = Flask(__name__)

# In-memory storage (replace later with DynamoDB)
database = {}

# API Keys (simple role-based access)
API_KEYS = {
    "admin-key": "admin",
    "driver-key": "driver",
    "customer-key": "customer"
}

# -----------------------------
# Helper Functions
# -----------------------------
def authenticate():
    key = request.headers.get("X-API-Key")
    if not key:
        return None, ("Missing API Key", 401)
    role = API_KEYS.get(key)
    if not role:
        return None, ("Invalid API Key", 401)
    return role, None


def validate_fields(data, required):
    for field in required:
        if field not in data or not data[field]:
            return False, f"{field} is required"
    return True, ""


def log_request(code):
    print(f"{datetime.datetime.now()} | {request.method} {request.path} -> {code}")


# -----------------------------
# Health Endpoint
# -----------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "healthy",
        "hostname": socket.gethostname()
    }), 200


# -----------------------------
# Create Parcel
# -----------------------------
@app.route("/api/parcels", methods=["POST"])
def create_parcel():
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    if role not in ["admin", "driver"]:
        return jsonify({"error": "Access denied"}), 403

    data = request.json or {}

    valid, msg = validate_fields(data, ["sender", "receiver", "address", "email"])
    if not valid:
        return jsonify({"error": msg}), 400

    pid = f"PKG-{uuid.uuid4().hex[:8]}"

    database[pid] = {
        "parcel_id": pid,
        "sender": data["sender"],
        "receiver": data["receiver"],
        "address": data["address"],
        "email": data["email"],
        "status": "created",
        "history": [{
            "status": "created",
            "time": datetime.datetime.utcnow().isoformat()
        }]
    }

    log_request(201)
    return jsonify({"parcel_id": pid}), 201


# -----------------------------
# Get Parcel
# -----------------------------
@app.route("/api/parcels/<pid>", methods=["GET"])
def get_parcel(pid):
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    parcel = database.get(pid)
    if not parcel:
        return jsonify({"error": "Parcel not found"}), 404

    log_request(200)
    return jsonify(parcel), 200


# -----------------------------
# Update Status
# -----------------------------
@app.route("/api/parcels/<pid>/status", methods=["PUT"])
def update_status(pid):
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    if role != "driver":
        return jsonify({"error": "Driver only"}), 403

    parcel = database.get(pid)
    if not parcel:
        return jsonify({"error": "Parcel not found"}), 404

    data = request.json or {}
    new_status = data.get("status")

    allowed = ["picked_up", "in_transit", "delivered"]
    if new_status not in allowed:
        return jsonify({"error": "Invalid status"}), 400

    parcel["status"] = new_status
    parcel["history"].append({
        "status": new_status,
        "time": datetime.datetime.utcnow().isoformat()
    })

    log_request(200)
    return jsonify({"message": "Status updated"}), 200


# -----------------------------
# List Parcels
# -----------------------------
@app.route("/api/parcels", methods=["GET"])
def list_parcels():
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    if role != "admin":
        return jsonify({"error": "Admin only"}), 403

    status_filter = request.args.get("status")

    results = list(database.values())
    if status_filter:
        results = [p for p in results if p["status"] == status_filter]

    log_request(200)
    return jsonify(results), 200


# -----------------------------
# Cancel Parcel
# -----------------------------
@app.route("/api/parcels/<pid>", methods=["DELETE"])
def delete_parcel(pid):
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    if role != "admin":
        return jsonify({"error": "Admin only"}), 403

    parcel = database.get(pid)
    if not parcel:
        return jsonify({"error": "Not found"}), 404

    if parcel["status"] != "created":
        return jsonify({"error": "Cannot cancel"}), 409

    parcel["status"] = "cancelled"
    parcel["history"].append({
        "status": "cancelled",
        "time": datetime.datetime.utcnow().isoformat()
    })

    log_request(200)
    return jsonify({"message": "Cancelled"}), 200


# -----------------------------
# Upload Photo (Mock)
# -----------------------------
@app.route("/api/parcels/<pid>/photo", methods=["POST"])
def upload_photo(pid):
    role, err = authenticate()
    if err:
        return jsonify({"error": err[0]}), err[1]

    if role != "driver":
        return jsonify({"error": "Driver only"}), 403

    parcel = database.get(pid)
    if not parcel:
        return jsonify({"error": "Parcel not found"}), 404

    photo_url = f"s3://smartparcel-photos-20200001899/{pid}/proof.jpg"

    return jsonify({
        "parcel_id": pid,
        "photo_url": photo_url
    }), 200


# -----------------------------
# Run App
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, threaded=True)