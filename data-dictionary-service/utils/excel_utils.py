import openpyxl
from io import BytesIO


def write_excel(rows_iter, headers):
    wb = openpyxl.Workbook(write_only=True)
    ws = wb.create_sheet(title="Data", index=0)
    ws.append(headers)
    for row in rows_iter:
        ws.append(row)
    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio
