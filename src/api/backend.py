# main.py

from fastapi import FastAPI
import importlib

backend = FastAPI()

# List of route module names to import
route_modules = ["users", "products",]

# Import and include each route module one by one
for route_module_name in route_modules:
    try:
        route_module = importlib.import_module(f"api.{route_module_name}")
        backend.include_router(route_module.router)
    except ModuleNotFoundError:
        print(f"api module '{route_module_name}' not found.")
