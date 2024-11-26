import flet as ft


def main(page: ft.Page):
    # Dados iniciais
    data = [
        {"id": 1, "name": "FERN", "country": "BRAZIL"},
        {"id": 2, "name": "ALIC", "country": "USA"},
        {"id": 3, "name": "JAKE", "country": "USA"},
        {"id": 4, "name": "LEBRO", "country": "USA"},
        {"id": 75, "name": "PIETRO", "country": "ITALY"},
    ]

    # Lista de países únicos
    countries = sorted(set(row["country"] for row in data))

    # Estado para armazenar os países selecionados
    selected_countries = set()

    # Função para atualizar a tabela com base no filtro
    def update_table():
        filtered_data = [
            row
            for row in data
            if not selected_countries or row["country"] in selected_countries
        ]
        data_table.rows = [
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(str(row["id"]))),
                    ft.DataCell(ft.Text(row["name"])),
                    ft.DataCell(ft.Text(row["country"])),
                ]
            )
            for row in filtered_data
        ]
        page.update()

    # Função chamada ao selecionar/desselecionar um país no checkbox
    def toggle_country(e):
        country = e.control.data
        if e.control.value:
            selected_countries.add(country)
        else:
            selected_countries.discard(country)
        update_table()

    # Criação dos checkboxes para os países
    country_checkboxes = [
        ft.Checkbox(label=country, value=False, data=country, on_change=toggle_country)
        for country in countries
    ]

    # Dropdown customizado (simulado com um PopupMenuButton)
    country_filter_dropdown = ft.PopupMenuButton(
        items=[
            ft.PopupMenuItem(
                content=ft.Column(
                    controls=country_checkboxes,
                    spacing=5,
                )
            )
        ],
        tooltip="Select Countries",
    )

    # Cria a tabela com cabeçalho customizado
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("ID")),
            ft.DataColumn(ft.Text("NAME")),
            ft.DataColumn(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text("COUNTRY"),
                            country_filter_dropdown,
                        ],
                        alignment="spaceBetween",
                    )
                )
            ),
        ],
        rows=[],
    )

    # Atualiza a tabela inicialmente
    update_table()

    # Adiciona os componentes na página
    page.add(data_table)


# Executa a aplicação
ft.app(target=main)
