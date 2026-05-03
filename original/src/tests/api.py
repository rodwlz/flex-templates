import httpx
import asyncio

async def fetch_product(product_id):
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8080/products/{product_id}")
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Product not found"}

async def product_view(product_id: int):
    product = await fetch_product(product_id)
    print(product)
    # Rest of the function remains the same

asyncio.run(product_view(2))
