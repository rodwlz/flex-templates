import src.templates.patterns as p
from fastapi import FastAPI
import uvicorn
import importlib
import os,signal

class backend_server(metaclass=p.Singleton):
    def __init__(self,route_modules: list=["__all__"],host="127.0.0.1",port=8080):
        self.backend = FastAPI()
        self.route_modules = route_modules
        self.host = host
        self.port = port

    def _load_modules(self):
        if self.route_modules == ["__all__"]:
            self.route_modules = ["users", "products",]

            # Import and include each route module one by one
        for route_module_name in self.route_modules:
                try:
                    route_module = importlib.import_module(f"src.api.{route_module_name}")
                    self.backend.include_router(route_module.router)
                except ModuleNotFoundError:
                    print(f"Route module '{route_module_name}' not found.")

    def launch(self):
         self._load_modules()
         uvicorn.run(self.backend, 
                        host=self.host, 
                        port=self.port)
           
    
    def shutdown(self):
        os.kill(os.getpid(), signal.SIGTERM)

backend = backend_server()

def main():
    backend.launch()
    
if __name__ == '__main__':
    main()
