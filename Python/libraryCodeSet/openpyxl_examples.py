"""openpyxl — practical single-file examples.

Install:  pip install openpyxl
Run:      python openpyxl_examples.py

Builds a workbook in memory, writes styled cells, formulas, charts, merged
cells, data validation, and conditional formatting, then saves it to
``output/`` and reads it back in both normal and read-only modes.

These examples are illustrative, not a test suite. See ../README.md.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.chart import BarChart, LineChart, PieChart, Reference
from openpyxl.formatting.rule import CellIsRule, ColorScaleRule, DataBarRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

OUTPUT = Path(__file__).resolve().parent / "output"
WORKBOOK_PATH = OUTPUT / "openpyxl_examples.xlsx"


def section(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


# ---------------------------------------------------------------------------
# 1. Writing values and basic formatting
# ---------------------------------------------------------------------------
def write_data(sheet) -> None:
    section("1. Writing values")

    headers = ["Region", "Q1", "Q2", "Q3", "Q4", "Total", "Growth"]
    for column, header in enumerate(headers, start=1):
        sheet.cell(row=1, column=column, value=header)

    rows = [
        ["North", 120000, 135000, 150000, 170000],
        ["South", 90000, 110000, 105000, 130000],
        ["East", 75000, 82000, 88000, 95000],
        ["West", 60000, 68000, 72000, 81000],
    ]
    for row_index, row in enumerate(rows, start=2):
        for column_index, value in enumerate(row, start=1):
            sheet.cell(row=row_index, column=column_index, value=value)

        # Formulas are stored as strings and calculated by Excel/LibreOffice
        sheet.cell(row=row_index, column=6, value=f"=SUM(B{row_index}:E{row_index})")
        sheet.cell(row=row_index, column=7, value=f"=F{row_index}/B{row_index}-1")
        sheet.cell(row=row_index, column=7).number_format = "0.0%"

    # Totals row
    total_row = len(rows) + 2
    sheet.cell(row=total_row, column=1, value="Total")
    for column in range(2, 7):
        letter = get_column_letter(column)
        sheet.cell(row=total_row, column=column, value=f"=SUM({letter}2:{letter}{total_row - 1})")
    sheet.cell(row=total_row, column=7, value=f"=F{total_row}/B{total_row}-1").number_format = "0.0%"

    # A few data types
    sheet["I1"] = "Type examples"
    sheet["I2"] = 42
    sheet["I3"] = 3.14159
    sheet["I4"] = True
    sheet["I5"] = datetime(2026, 10, 19, 14, 30)
    sheet["I6"] = date(2026, 10, 19)
    sheet["I7"] = "=TODAY()"
    sheet["I5"].number_format = "yyyy-mm-dd hh:mm"
    sheet["I6"].number_format = "yyyy-mm-dd"

    print("wrote headers and", len(rows), "data rows")
    print("dimensions:", sheet.dimensions, "max_row:", sheet.max_row, "max_col:", sheet.max_column)


# ---------------------------------------------------------------------------
# 2. Styles
# ---------------------------------------------------------------------------
def style_sheet(sheet) -> None:
    section("2. Fonts, fills, borders, and alignment")

    header_font = Font(name="Calibri", size=12, bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="1F4E78")
    thin = Side(style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    for cell in sheet[1]:
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = border

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row, min_col=1, max_col=7):
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(horizontal="right" if cell.column > 1 else "left")

    sheet["A1"].alignment = Alignment(horizontal="left", vertical="center")
    sheet["A1"].font = Font(bold=True, size=13, color="FFC000")

    # Highlight the totals row
    total_row = sheet.max_row
    for cell in sheet[total_row]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="DDEBF7")

    # Number formats
    for row in range(2, total_row + 1):
        for column in range(2, 7):
            sheet.cell(row=row, column=column).number_format = "#,##0"
        sheet.cell(row=row, column=7).number_format = "0.0%"

    # Row heights and column widths
    sheet.row_dimensions[1].height = 24
    widths = {"A": 14, "B": 12, "C": 12, "D": 12, "E": 12, "F": 14, "G": 12, "I": 22}
    for letter, width in widths.items():
        sheet.column_dimensions[letter].width = width

    # Freeze the header and add an autofilter
    sheet.freeze_panes = "B2"
    sheet.auto_filter.ref = f"A1:G{total_row - 1}"

    print("styled", sheet.max_row, "rows")


# ---------------------------------------------------------------------------
# 3. Merging, wrapping, and annotations
# ---------------------------------------------------------------------------
def extras(sheet) -> None:
    section("3. Merged cells and comments")

    sheet.merge_cells("A12:G12")
    merged = sheet["A12"]
    merged.value = "Quarterly revenue by region (figures in USD)"
    merged.font = Font(bold=True, italic=True, size=11)
    merged.alignment = Alignment(horizontal="center", vertical="center")
    merged.fill = PatternFill("solid", fgColor="FFF2CC")
    sheet.row_dimensions[12].height = 22

    sheet["A14"] = "Note"
    sheet["A14"].font = Font(bold=True)
    sheet["B14"] = "Formulas are evaluated by the spreadsheet application, not by openpyxl."
    sheet["B14"].alignment = Alignment(wrap_text=True, vertical="top")
    sheet.merge_cells("B14:G14")
    sheet.row_dimensions[14].height = 34

    # Cell comment (legacy note)
    from openpyxl.comments import Comment

    sheet["F1"].comment = Comment("Sum of Q1-Q4", "dataset")
    print("merged ranges:", [str(rng) for rng in sheet.merged_cells.ranges])


# ---------------------------------------------------------------------------
# 4. Data validation and conditional formatting
# ---------------------------------------------------------------------------
def validation_and_formatting(sheet) -> None:
    section("4. Data validation and conditional formatting")

    status_header = sheet.cell(row=1, column=10, value="Status")
    status_header.font = Font(bold=True, color="FFFFFF")
    status_header.fill = PatternFill("solid", fgColor="1F4E78")

    statuses = ["Open", "In progress", "Closed"]
    for row, status in enumerate(statuses, start=2):
        sheet.cell(row=row, column=10, value=status)

    validation = DataValidation(
        type="list",
        formula1='"Open,In progress,Closed"',
        allow_blank=True,
        showDropDown=False,
    )
    validation.error = "Choose one of: Open, In progress, Closed"
    validation.errorTitle = "Invalid status"
    validation.prompt = "Select a status"
    validation.promptTitle = "Status"
    sheet.add_data_validation(validation)
    validation.add("J2:J8")

    # Numeric range validation for a budget column
    budget_header = sheet.cell(row=1, column=11, value="Budget")
    budget_header.font = Font(bold=True, color="FFFFFF")
    budget_header.fill = PatternFill("solid", fgColor="1F4E78")
    for row in range(2, 6):
        sheet.cell(row=row, column=11, value=100000 + row * 5000).number_format = "#,##0"

    number_validation = DataValidation(type="decimal", operator="between", formula1="0", formula2="1000000")
    number_validation.error = "Budget must be between 0 and 1,000,000"
    sheet.add_data_validation(number_validation)
    number_validation.add("K2:K5")

    # Colour scale on the numeric revenue columns
    sheet.conditional_formatting.add(
        "B2:E5",
        ColorScaleRule(
            start_type="min", start_color="F8696B",
            mid_type="percentile", mid_value=50, mid_color="FFEB84",
            end_type="max", end_color="63BE7B",
        ),
    )

    # Data bars on the totals column
    sheet.conditional_formatting.add(
        "F2:F5",
        DataBarRule(start_type="num", start_value=0, end_type="num", end_value=500000, color="5B9BD5"),
    )

    # Highlight low growth values in red
    sheet.conditional_formatting.add(
        "G2:G5",
        CellIsRule(operator="lessThan", formula=["0.1"], fill=PatternFill("solid", fgColor="FFC7CE")),
    )

    print("validations:", len(sheet.data_validations.dataValidation))
    print("conditional formatting ranges:", [str(rng) for rng in sheet.conditional_formatting])


# ---------------------------------------------------------------------------
# 5. Charts
# ---------------------------------------------------------------------------
def charts(sheet) -> None:
    section("5. Adding charts")

    bar = BarChart()
    bar.type = "col"
    bar.style = 10
    bar.title = "Quarterly revenue by region"
    bar.y_axis.title = "Revenue (USD)"
    bar.x_axis.title = "Region"
    bar.y_axis.numFmt = "#,##0"

    data = Reference(sheet, min_col=2, max_col=5, min_row=1, max_row=5)
    categories = Reference(sheet, min_col=1, min_row=2, max_row=5)
    bar.add_data(data, titles_from_data=True)
    bar.set_categories(categories)
    bar.height = 8
    bar.width = 16
    sheet.add_chart(bar, "A17")

    line = LineChart()
    line.title = "Revenue trend"
    line.y_axis.title = "Revenue (USD)"
    line.add_data(data, titles_from_data=True)
    line.set_categories(categories)
    line.height = 8
    line.width = 16
    sheet.add_chart(line, "J17")

    pie = PieChart()
    pie.title = "Q4 share"
    q4 = Reference(sheet, min_col=5, min_row=1, max_row=5)
    pie.add_data(q4, titles_from_data=True)
    pie.set_categories(categories)
    pie.height = 8
    pie.width = 12
    sheet.add_chart(pie, "A36")

    print("charts on sheet:", len(sheet._charts))


# ---------------------------------------------------------------------------
# 6. Multiple sheets and workbook properties
# ---------------------------------------------------------------------------
def multiple_sheets(workbook: Workbook) -> None:
    section("6. Multiple worksheets")

    summary = workbook.create_sheet("Summary")
    summary["A1"] = "Region"
    summary["B1"] = "Annual total"
    summary["C1"] = "Share"

    for row, region in enumerate(["North", "South", "East", "West"], start=2):
        source_row = row  # same row on the data sheet
        summary.cell(row=row, column=1, value=region)
        summary.cell(row=row, column=2, value=f"='Revenue'!F{source_row}")
        summary.cell(row=row, column=3, value=f"=B{row}/SUM($B$2:$B$5)")
        summary.cell(row=row, column=3).number_format = "0.0%"

    summary["B6"] = "=SUM(B2:B5)"
    summary["B6"].number_format = "#,##0"
    summary["B6"].font = Font(bold=True)

    for cell in summary[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="375623")

    summary.column_dimensions["A"].width = 16
    summary.column_dimensions["B"].width = 16
    summary.column_dimensions["C"].width = 10

    # Hidden sheet and tab colours
    notes = workbook.create_sheet("Notes")
    notes["A1"] = "Generated by openpyxl_examples.py"
    notes.sheet_state = "visible"
    notes.sheet_properties.tabColor = "FFC000"
    summary.sheet_properties.tabColor = "00B050"

    workbook.properties.title = "openpyxl examples"
    workbook.properties.creator = "programDataset"
    workbook.properties.description = "Single-file workbook demonstration"
    workbook.active = 0

    print("sheets:", workbook.sheetnames)


# ---------------------------------------------------------------------------
# 7. Save, reload, and inspect
# ---------------------------------------------------------------------------
def save_and_reload() -> None:
    section("7. Saving, loading, and read-only iteration")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    revenue = workbook.active
    revenue.title = "Revenue"
    revenue.sheet_view.showGridLines = False

    write_data(revenue)
    style_sheet(revenue)
    extras(revenue)
    validation_and_formatting(revenue)
    charts(revenue)
    multiple_sheets(workbook)
    workbook.save(WORKBOOK_PATH)
    print("saved workbook:", WORKBOOK_PATH, f"({WORKBOOK_PATH.stat().st_size:,} bytes)")

    # Normal load: full object model
    loaded = load_workbook(WORKBOOK_PATH, data_only=False)
    print("\nloaded sheets:", loaded.sheetnames)
    print("revenue dimensions:", loaded["Revenue"].dimensions)
    print("formula cell F2:", loaded["Revenue"]["F2"].value)

    # data_only=True returns cached values (None until Excel opens and saves)
    values_only = load_workbook(WORKBOOK_PATH, data_only=True)
    print("cached F2 with data_only=True:", values_only["Revenue"]["F2"].value)

    # Read-only mode streams rows and uses less memory for large files
    read_only = load_workbook(WORKBOOK_PATH, read_only=True)
    sheet = read_only["Revenue"]
    rows = sheet.iter_rows(min_row=1, max_row=6, max_col=7, values_only=True)
    print("\nfirst rows (read_only):")
    for row in rows:
        print(" ", row)
    read_only.close()

    # iterate over columns and rows
    print("\nsummary values:")
    for region, total in loaded["Summary"].iter_rows(min_row=2, max_row=5, min_col=1, max_col=2, values_only=True):
        print(f"  {region}: {total}")

    # Sheet metadata
    print("\nsheet states:", {ws.title: ws.sheet_state for ws in loaded.worksheets})
    print("merged ranges:", [str(rng) for rng in loaded["Revenue"].merged_cells.ranges])
    print("freeze panes:", loaded["Revenue"].freeze_panes)


def main() -> None:
    import openpyxl

    print("openpyxl version:", openpyxl.__version__)
    save_and_reload()
    print("\nAll openpyxl example sections completed.")


if __name__ == "__main__":
    main()
