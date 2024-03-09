import flet as ft
from src.templates.layouts import base_view
import src.templates.components as c
import src.templates.layouts as l
import pandas as pd

def report():
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
    test_report_card = c.basics.ReportCard()
    test_report_card.Button.on_click = lambda _: report()


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
        test_report_card.container(),  # Add the test_report_card to the screen content
    ]

    return l.StView(page, '/menu',screen_content)
