from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

# ✅ Load environment variables from .env file
load_dotenv()

# ✅ Get Mongo URI from .env
MONGO_URI = os.getenv("MONGO_URI")

# ✅ Raise error if MONGO_URI is missing
if not MONGO_URI:
    raise ValueError("❌ MONGO_URI not found in .env file. Please set it in your .env.")

# ✅ Connect to MongoDB
client = AsyncIOMotorClient(MONGO_URI)

# ✅ Use the database and relevant collections
db = client["resume_shortlister"]

users_collection = db["users"]
jd_collection = db["jd_history"]
otp_collection = db["otp_temp"]
ai_results_collection = db["ai_results"]

