# routes/product.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/products/{product_id}")
async def get_product(product_id: int):
    # Get product logic
    return {"product_id": product_id}

@router.post("/products")
async def create_product(product_data: dict):
    # Create product logic
    return {"message": "Product created successfully"}
