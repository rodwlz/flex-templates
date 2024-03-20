# main.py

from fastapi import FastAPI
import importlib

backend = FastAPI()

# List of route module names to import
route_modules = ["users", "products",]

# Import and include each route module one by one
for route_module_name in route_modules:
    try:
        route_module = importlib.import_module(f"src.api.{route_module_name}")
        backend.include_router(route_module.router)
    except ModuleNotFoundError:
        print(f"Route module '{route_module_name}' not found.")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(backend, host="127.0.0.1", port=8080)
