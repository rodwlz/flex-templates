import flet as ft
import src.templates.layouts as l
import src.templates.components as c
import httpx
import asyncio

async def fetch_product(product_id):
    
    async with httpx.AsyncClient() as client:
        response = await client.get(f"http://127.0.0.1:8080/products/{product_id}")

        if response.status_code == 200:
            return response.json()
        else:
            return {"error": "Product not found"}


def product_view(page: ft.Page, product_id: int):
    product = asyncio.run(fetch_product(product_id))
   
    product_id_text = ft.Text(f"Product ID: {product['id']}")
    product_desc_text = ft.Text(f"Product Description: {product['description']}")

    return ft.Container(
            ft.Column([product_id_text,product_desc_text])
        )
    # Return the page after adding components

def view(page):

    sub_text = ft.Container(
        ft.Text("Product", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
    )

    # Example product ID to fetch product information
    product_id = 1
    product_section = product_view(page, product_id)

    # Add the product section to the screen
    screen = [
        sub_text,
        product_section,
    ]

    v = l.StView(page, "/products", screen)
    return v
