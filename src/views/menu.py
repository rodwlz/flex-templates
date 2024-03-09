import flet as ft
from src.templates.layouts import base_view
import src.templates.components as c
import src.templates.layouts as l
import pandas as pd

def test_report_event_handler():
    # URL to the raw test.csv file on GitHub
    csv_url = 'https://raw.githubusercontent.com/dsindy/kaggle-titanic/master/data/test.csv'

    # Read the CSV data into a DataFrame
    df = pd.read_csv(csv_url)

    # Filter female passengers
    female_passengers = df[df['Sex'] == 'female']

    # Print the CSV of female passengers
    print(female_passengers.to_csv(index=False))


def view(page):
    # Card for test_report
    test_report_card = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.ListTile(
                        leading=ft.Icon(ft.icons.EVENT),
                        title=ft.Text("Test Report"),
                        subtitle=ft.Text("Click to view test report."),
                    ),
                    ft.ElevatedButton("execute", on_click=lambda _: test_report_event_handler()),
                ]
            ),
            width=400,
            padding=10,
        )
    )

    title = ft.Container(
        ft.Text("Menu", size=24, weight="bold", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
    )

    sub_text = ft.Container(
        ft.Text("Pick a report", color=ft.colors.ON_BACKGROUND),
        alignment=ft.alignment.center
    )

    screen_content = [
        title,
        sub_text,
        test_report_card,  # Add the test_report_card to the screen content
    ]

    return l.StView(page, '/menu',screen_content)
