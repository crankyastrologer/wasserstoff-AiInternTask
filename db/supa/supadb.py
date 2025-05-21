from supabase import create_client, Client
from schema import UserInDB
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


def get_user(username: str) -> UserInDB | None:
    response = supabase.table("users").select("*").eq("username", username).limit(1).execute()
    print(response.data)
    if response.data:
        return UserInDB(**response.data[0])
    return None


def insert_user(user: UserInDB, hashed_password: str):
    result = supabase.table("users").insert({
        "username": user.username,
        "hashed_password": hashed_password,
    }).execute()

    return result
