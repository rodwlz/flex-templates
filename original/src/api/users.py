from fastapi import APIRouter

router = APIRouter()

@router.get("/users/")
async def get_users():
    return {"message": "Get all users"}

@router.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"message": f"Get user with ID {user_id}"}
