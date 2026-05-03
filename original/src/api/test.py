from fastapi import FastAPI

backend = FastAPI()

# Define some sample data
items = [
    {"id": 1, "name": "Item 1", "description": "Description for Item 1"},
    {"id": 2, "name": "Item 2", "description": "Description for Item 2"},
]

# Define endpoints to retrieve data
@backend.get("/items")
async def get_items():
    return items

@backend.get("/items/{item_id}")
async def get_item(item_id: int):
    for item in items:
        if item["id"] == item_id:
            return item
    return {"error": "Item not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(backend, host="127.0.0.1", port=8000)
