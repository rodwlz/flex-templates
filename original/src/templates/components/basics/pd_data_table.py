import flet as ft
import pandas as pd

class PDDataTable(ft.DataTable):
    def __init__(self, dataframe: pd.DataFrame):
        super().__init__()
        
        self.dataframe = dataframe
        self.width = 1000
        self.column_spacing = 10
        self.data_row_min_height = 40  # Adjusted the minimum height for better vertical scrolling
        # Create columns from DataFrame columns
        self.columns = [
            ft.DataColumn(
                ft.Text(str(col)),
            )
            for col in dataframe.columns
        ]

        # Create rows from DataFrame rows
        self.rows = [
            ft.DataRow(
                [ft.DataCell(ft.Text(str(dataframe.at[index, col]))) for col in dataframe.columns]
            )
            for index in dataframe.index
        ]

    def container(self):
        return ft.Container(self, expand=1)
    
