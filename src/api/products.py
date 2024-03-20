# routes/product.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/products/{product_id}")
async def get_product(product_id: int):
    
    products = {
    1: {"id": 1, "name": "Product 1", "description": "Description for Product 1"},
    2: {"id": 2, "name": "Product 2", "description": "Description for Product 2"},
}

    # Get product logic
    try:
        return products[product_id]
    
    except Exception:
        print(Exception)
        return {'id':'error'}
    

@router.post("/products")
async def create_product(product_data: dict):
    # Create product logic
    return {"message": "Product created successfully"}
