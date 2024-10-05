from fastapi import FastAPI, HTTPException, status, Depends
from app.models import UserCreate, UserResponse, UserLogin, UserUpdate
from app.database import user_collection
from app.auth import hash_password, verify_password
from bson import ObjectId
from fastapi import Body


app = FastAPI()

async def get_user_by_email(email: str):
    user = await user_collection.find_one({"email": email})
    return user

@app.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register_user(user: UserCreate):
    existing_user = await get_user_by_email(user.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = hash_password(user.password)

    new_user = await user_collection.insert_one({"name":user.name,"email": user.email, "password": hashed_password})
    
    created_user = await user_collection.find_one({"_id": new_user.inserted_id})
    return UserResponse(email=created_user["email"])

@app.post("/login")
async def login_user(user: UserLogin):
    db_user = await get_user_by_email(user.email)
    if not db_user or not verify_password(user.password, db_user["password"]):
        raise HTTPException(status_code=400, detail="Invalid email or password")

    return {"message": "Login successful"}




@app.patch("/users/update/{email}")
async def update_user(email: str, user_update: UserUpdate = Body(...)):
    db_user = await get_user_by_email(email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = {}

    if user_update.password:
        if not user_update.old_password:
            raise HTTPException(status_code=400, detail="Old password is required to update the password")
        
        if not verify_password(user_update.old_password, db_user["password"]):
            raise HTTPException(status_code=400, detail="Old password is incorrect")

        hashed_password = hash_password(user_update.password)
        update_data["password"] = hashed_password

    if user_update.email:
        existing_user = await get_user_by_email(user_update.email)
        if existing_user and existing_user["_id"] != db_user["_id"]:
            raise HTTPException(status_code=400, detail="Email already registered")
        update_data["email"] = user_update.email

    if user_update.name:
        update_data["name"] = user_update.name

    if update_data:
        await user_collection.update_one({"email": email}, {"$set": update_data})

    return {"message": "User information updated successfully"}