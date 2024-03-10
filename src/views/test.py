import flet as ft
import src.templates.components as c
import src.templates.layouts as l
import pandas as pd

def report():
    # URL to the raw test.csv file on GitHub
    csv_url = 'https://raw.githubusercontent.com/dsindy/kaggle-titanic/master/data/test.csv'
    # Read the CSV data into a DataFrame
    df = pd.read_csv(csv_url)
    # Filter female passengers
    return df[df['Sex'] == 'female']



def view(page):

    df = report()

    # Creating a PDDataTable instance
    screen_content =ft.Row([c.basics.PDDataTable(dataframe=df).container()])
    # Running the Flet app with the PDDataTable
    return l.StView(page, '/test',[screen_content])
