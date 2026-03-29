from fastapi import FastAPI, HTTPException
from pymongo import MongoClient
from models import Appointment
from fastapi.middleware.cors import CORSMiddleware
import random

app = FastAPI()

# Allow frontend running on another port (e.g., 5500) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For testing, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Connect to MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["dentalvoice"]
appointments_collection = db["appointments"]

@app.post("/appointments")
async def create_appointment(appointment: Appointment):
    # Generate confirmation ID
    confirmation_id = f"APPT-{random.randint(1000,9999)}"
    
    appointment_dict = appointment.dict()
    appointment_dict["confirmationId"] = confirmation_id
    
    # Insert into MongoDB
    result = appointments_collection.insert_one(appointment_dict)
    
    if result.inserted_id:
        return {"message": "Appointment saved successfully", "confirmationId": confirmation_id}
    else:
        raise HTTPException(status_code=500, detail="Failed to save appointment")
