import csv
import os
from openpyxl import load_workbook


def col_letter_to_index(letter):
    result = 0
    for char in letter.upper():
        result = result * 26 + (ord(char) - ord('A') + 1)
    return result - 1


def index_to_col_letter(index):
    result = ""
    index += 1
    while index > 0:
        index -= 1
        result = chr(ord('A') + index % 26) + result
        index //= 26
    return result


def parse_range(range_str):
    range_str = range_str.strip()
    if ':' in range_str:
        parts = range_str.split(':')
        start_str = parts[0].strip()
        end_str = parts[1].strip()

        sc, sr = _split_cell(start_str)
        ec, er = _split_cell(end_str)

        start_col = col_letter_to_index(sc) if sc else 0
        start_row = int(sr) if sr else 1
        end_col = col_letter_to_index(ec) if ec else start_col
        end_row = int(er) if er else start_row
        return (start_col, start_row, end_col, end_row)
    else:
        c, r = _split_cell(range_str)
        col = col_letter_to_index(c) if c else 0
        row = int(r) if r else 1
        return (col, row, col, row)


def _split_cell(cell_str):
    col_part = ''
    row_part = ''
    for ch in cell_str:
        if ch.isalpha():
            col_part += ch
        elif ch.isdigit():
            row_part += ch
    return col_part, row_part


class TableData:
    def __init__(self, name, file_path):
        self.name = name
        self.file_path = file_path
        self.raw_data = []
        self.headers = []
        self.header_row = 1
        self.index = {}

    def build_index(self):
        self.index = {}
        data_start = self.header_row
        for col_idx, header in enumerate(self.headers):
            if not header or str(header).strip() == '':
                continue
            col_index = {}
            for row_idx in range(data_start, len(self.raw_data)):
                value = self._get_cell(row_idx, col_idx)
                str_val = str(value) if value != '' else ''
                if str_val not in col_index:
                    col_index[str_val] = []
                col_index[str_val].append(row_idx)
            self.index[str(header).strip()] = col_index

    def _get_cell(self, row_idx, col_idx):
        if row_idx < len(self.raw_data):
            row = self.raw_data[row_idx]
            if col_idx < len(row):
                return row[col_idx]
        return ''

    def get_range(self, range_str):
        start_col, start_row, end_col, end_row = parse_range(range_str)
        start_row_0 = start_row - 1
        end_row_0 = end_row - 1
        result = []
        for row_idx in range(start_row_0, end_row_0 + 1):
            for col_idx in range(start_col, end_col + 1):
                result.append(self._get_cell(row_idx, col_idx))
        return result

    def get_range_2d(self, range_str):
        start_col, start_row, end_col, end_row = parse_range(range_str)
        start_row_0 = start_row - 1
        end_row_0 = end_row - 1
        result = []
        for row_idx in range(start_row_0, end_row_0 + 1):
            row_data = []
            for col_idx in range(start_col, end_col + 1):
                row_data.append(self._get_cell(row_idx, col_idx))
            result.append(row_data)
        return result

    def find_rows(self, column, value):
        col_key = str(column).strip()
        if col_key not in self.index:
            return []
        str_value = str(value)
        if str_value not in self.index[col_key]:
            return []
        return [self._row_to_dict(idx) for idx in self.index[col_key][str_value]]

    def find_row(self, column, value):
        rows = self.find_rows(column, value)
        return rows[0] if rows else None

    def _row_to_dict(self, row_idx):
        result = {}
        row = self.raw_data[row_idx]
        for col_idx, header in enumerate(self.headers):
            if header and str(header).strip():
                result[str(header).strip()] = row[col_idx] if col_idx < len(row) else ''
        return result

    def get_column_values(self, column_name):
        col_key = str(column_name).strip()
        if col_key not in self.headers:
            return []
        col_idx = self.headers.index(col_key)
        data_start = self.header_row
        result = []
        for row_idx in range(data_start, len(self.raw_data)):
            result.append(self._get_cell(row_idx, col_idx))
        return result


class TableLoader:
    @staticmethod
    def load(name, file_path, sheet_name=None, header_row=2):
        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            return TableLoader._load_csv(name, file_path, header_row)
        elif ext in ('.xlsx', '.xlsm'):
            return TableLoader._load_excel(name, file_path, sheet_name, header_row)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    @staticmethod
    def _load_csv(name, file_path, header_row):
        table = TableData(name, file_path)
        table.header_row = header_row

        raw = None
        for encoding in ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin1']:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    reader = csv.reader(f)
                    raw = [row for row in reader]
                break
            except UnicodeDecodeError:
                continue
        if raw is None:
            raise ValueError(f"无法读取CSV文件: {file_path}")

        table.raw_data = raw
        _pad_rows(table.raw_data)

        header_idx = header_row - 1
        if header_idx < len(table.raw_data):
            table.headers = [str(h).strip() if h else '' for h in table.raw_data[header_idx]]
        else:
            table.headers = []

        for i, h in enumerate(table.headers):
            if not h:
                table.headers[i] = f"Col_{index_to_col_letter(i)}"

        table.build_index()
        return table

    @staticmethod
    def _load_excel(name, file_path, sheet_name, header_row):
        wb = load_workbook(file_path, data_only=True, read_only=True)

        if sheet_name and sheet_name in wb.sheetnames:
            ws = wb[sheet_name]
        else:
            ws = wb.active

        table = TableData(name, file_path)
        table.header_row = header_row

        table.raw_data = []
        for row in ws.iter_rows(values_only=True):
            table.raw_data.append([str(cell) if cell is not None else '' for cell in row])

        wb.close()
        _pad_rows(table.raw_data)

        header_idx = header_row - 1
        if header_idx < len(table.raw_data):
            table.headers = [str(h).strip() if h else '' for h in table.raw_data[header_idx]]
        else:
            table.headers = []

        for i, h in enumerate(table.headers):
            if not h:
                table.headers[i] = f"Col_{index_to_col_letter(i)}"

        table.build_index()
        return table

    @staticmethod
    def get_sheet_names(file_path):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in ('.xlsx', '.xlsm'):
            wb = load_workbook(file_path, read_only=True)
            names = wb.sheetnames
            wb.close()
            return names
        return []


def _pad_rows(raw_data):
    if not raw_data:
        return
    max_cols = max(len(row) for row in raw_data)
    for row in raw_data:
        while len(row) < max_cols:
            row.append('')
