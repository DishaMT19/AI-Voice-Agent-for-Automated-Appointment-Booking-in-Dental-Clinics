from pymongo import MongoClient

# Replace with your MongoDB URI
MONGO_URI = "mongodb+srv://<username>:<password>@cluster0.mongodb.net/clinic_db?retryWrites=true&w=majority"

client = MongoClient(MONGO_URI)
db = client.clinic_db

# Collections
patients_col = db.patients
doctors_col = db.doctors
appointments_col = db.appointments
clinic_hours_col = db.clinic_hours
rooms_col = db.rooms
blackout_dates_col = db.blackout_dates
