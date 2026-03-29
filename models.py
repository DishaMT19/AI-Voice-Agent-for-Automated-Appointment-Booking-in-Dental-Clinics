from datetime import datetime, timedelta
import re

class ConversationState:
    def __init__(self):
        self.step = 1
        self.patient = {
            "name": None,
            "phone": None,
            "address": None,
            "email": None
        }
        self.appointment = {
            "service": None,
            "date": None,
            "time": None,
            "duration": None
        }

    def process(self, text):
        t = text.lower()

        if self.step == 1:
            if "appointment" in t:
                self.step = 2
                return "Sure. May I know your name?"
            return "Say I want to book an appointment."

        if self.step == 2:
            name = re.sub(r"(my name is|i am|i'm)\s*", "", text, flags=re.I)
            self.patient["name"] = name
            self.step = 3
            return f"Thank you {name}. What is your phone number?"

        if self.step == 3:
            phone = re.sub(r"\D", "", text)
            self.patient["phone"] = phone
            self.step = 4
            return "Got it. What is your address?"

        if self.step == 4:
            self.patient["address"] = text
            self.step = 5
            return "Thanks. What is your email? You can say skip."

        if self.step == 5:
            if "skip" in t:
                self.patient["email"] = "Not Provided"
            else:
                self.patient["email"] = text
            self.step = 6
            return "Which service do you need?"

        if self.step == 6:
            self.appointment["service"] = text
            self.step = 7
            return "What date do you prefer?"

        if self.step == 7:
            self.appointment["date"] = text
            self.step = 8
            return "Available times are 10 AM, 12 PM and 3 PM. Which one?"

        if self.step == 8:
            self.appointment["time"] = text
            self.step = 9
            return "Should I confirm?"

        if self.step == 9:
            if "yes" in t:
                return "Saving your appointment now."
            return "Appointment cancelled."

services = {}
