from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.route('/')
def home():
    return "Backend is running!"

@app.route('/api/test')
def test():
    return jsonify({"status": "ok", "message": "Backend working"})

@app.route('/api/save-appointment', methods=['POST'])
def save_appointment():
    return jsonify({
        "success": True,
        "appointment_id": "TEST-123",
        "message": "Test appointment saved"
    })

if __name__ == '__main__':
    print("Simple backend starting on http://localhost:5002")
    app.run(debug=True, port=5002)