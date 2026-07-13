"""
Сервис для импорта данных из Excel файлов

Поддерживаемый формат Excel:
- Колонка A: Имя сотрудника (Employee Name)
- Колонка B: Ставка €/h (Hourly Rate)
- Колонка C: Банк (Bank) - опционально
- Колонка D: IBAN - опционально
- Колонка E: BIC - опционально
- Колонки F+: Даты с количеством часов (формат: DD-MM-YYYY)

Пример:
| Employee Name | Hourly Rate | Bank | IBAN | BIC | 01-05-2026 | 02-05-2026 | ... |
|---------------|-------------|------|------|-----|------------|------------|-----|
| John Doe      | 12.50       | ABC  | DE.. | .. | 8.0        | 10.0       | ... |
"""

import pandas as pd
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re


class ExcelImportError(Exception):
    """Ошибка импорта Excel файла"""
    pass


class EmployeeData:
    """Данные сотрудника из Excel"""
    def __init__(self, name: str, rate: float, bank: str = None, iban: str = None, bic: str = None):
        self.name = name
        self.rate = rate
        self.bank = bank
        self.iban = iban
        self.bic = bic
        self.hours_by_date: Dict[str, float] = {}  # {YYYY-MM-DD: hours}
    
    def add_hours(self, date: str, hours: float):
        """Добавить часы для даты"""
        self.hours_by_date[date] = hours
    
    def get_total_hours(self) -> float:
        """Общее количество часов"""
        return sum(self.hours_by_date.values())
    
    def get_date_range(self) -> Tuple[str, str]:
        """Получить диапазон дат (начало, конец)"""
        if not self.hours_by_date:
            return None, None
        dates = sorted(self.hours_by_date.keys())
        return dates[0], dates[-1]


def parse_date_column(col_name: str) -> Optional[str]:
    """
    Парсит название колонки и извлекает дату
    Поддерживаемые форматы: DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
    Возвращает дату в формате YYYY-MM-DD или None
    """
    # Убираем пробелы
    col_name = str(col_name).strip()
    
    # Паттерны для разных форматов дат
    patterns = [
        r'(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})',  # DD-MM-YYYY, DD/MM/YYYY, DD.MM.YYYY
        r'(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})',  # YYYY-MM-DD, YYYY/MM/DD
    ]
    
    for pattern in patterns:
        match = re.search(pattern, col_name)
        if match:
            groups = match.groups()
            # Определяем формат
            if len(groups[0]) == 4:  # YYYY-MM-DD
                year, month, day = groups
            else:  # DD-MM-YYYY
                day, month, year = groups
            
            try:
                # Проверяем валидность даты
                date_obj = datetime(int(year), int(month), int(day))
                return date_obj.strftime("%Y-%m-%d")
            except ValueError:
                continue
    
    return None


def validate_excel_structure(df: pd.DataFrame) -> Tuple[bool, str]:
    """
    Валидация структуры Excel файла
    Возвращает (is_valid, error_message)
    """
    if df.empty:
        return False, "Файл пустой"
    
    # Проверяем минимальное количество колонок
    if df.shape[1] < 6:  # Минимум: Name, Rate, Bank, IBAN, BIC + 1 дата
        return False, f"Недостаточно колонок. Найдено {df.shape[1]}, требуется минимум 6"
    
    # Проверяем наличие обязательных колонок
    columns = df.columns.tolist()
    
    # Первые 2 колонки должны быть Name и Rate
    first_col = str(columns[0]).lower()
    second_col = str(columns[1]).lower()
    
    if not any(keyword in first_col for keyword in ['name', 'employee', 'имя', 'сотрудник']):
        return False, f"Первая колонка должна быть 'Employee Name', найдено: {columns[0]}"
    
    if not any(keyword in second_col for keyword in ['rate', 'ставка', 'hourly']):
        return False, f"Вторая колонка должна быть 'Hourly Rate', найдено: {columns[1]}"
    
    # Проверяем наличие хотя бы одной колонки с датой
    date_columns = [col for col in columns[5:] if parse_date_column(col)]
    if not date_columns:
        return False, "Не найдено ни одной колонки с датами (формат: DD-MM-YYYY)"
    
    return True, "OK"


def import_excel_file(filepath: str) -> List[EmployeeData]:
    """
    Импорт данных из Excel файла
    
    Args:
        filepath: Путь к Excel файлу
    
    Returns:
        Список объектов EmployeeData
    
    Raises:
        ExcelImportError: При ошибке чтения или валидации
    """
    try:
        # Читаем Excel файл
        df = pd.read_excel(filepath, engine='openpyxl')
        
        # Валидация структуры
        is_valid, error_msg = validate_excel_structure(df)
        if not is_valid:
            raise ExcelImportError(f"Неверная структура файла: {error_msg}")
        
        employees = []
        columns = df.columns.tolist()
        
        # Определяем колонки с датами (начиная с 6-й колонки)
        date_columns = {}
        for col in columns[5:]:
            parsed_date = parse_date_column(col)
            if parsed_date:
                date_columns[col] = parsed_date
        
        if not date_columns:
            raise ExcelImportError("Не найдено колонок с датами")
        
        # Обрабатываем каждую строку
        for idx, row in df.iterrows():
            # Пропускаем пустые строки
            if pd.isna(row.iloc[0]) or str(row.iloc[0]).strip() == '':
                continue
            
            # Читаем основные данные
            name = str(row.iloc[0]).strip()
            
            try:
                rate = float(row.iloc[1])
                if rate <= 0:
                    raise ValueError(f"Ставка должна быть положительным числом")
            except (ValueError, TypeError) as e:
                raise ExcelImportError(f"Строка {idx + 2}: неверная ставка для '{name}': {row.iloc[1]}")
            
            # Опциональные данные
            bank = str(row.iloc[2]).strip() if not pd.isna(row.iloc[2]) else None
            iban = str(row.iloc[3]).strip() if not pd.isna(row.iloc[3]) else None
            bic = str(row.iloc[4]).strip() if not pd.isna(row.iloc[4]) else None
            
            # Создаём объект сотрудника
            employee = EmployeeData(name, rate, bank, iban, bic)
            
            # Читаем часы по датам
            for col_name, date_str in date_columns.items():
                hours_value = row[col_name]
                
                # Пропускаем пустые ячейки
                if pd.isna(hours_value) or str(hours_value).strip() == '':
                    continue
                
                try:
                    hours = float(hours_value)
                    if hours < 0:
                        raise ValueError("Часы не могут быть отрицательными")
                    if hours > 24:
                        raise ValueError("Часы не могут быть больше 24")
                    
                    if hours > 0:  # Сохраняем только ненулевые значения
                        employee.add_hours(date_str, hours)
                
                except (ValueError, TypeError) as e:
                    raise ExcelImportError(
                        f"Строка {idx + 2}, колонка '{col_name}': "
                        f"неверное значение часов для '{name}': {hours_value}"
                    )
            
            # Добавляем сотрудника только если есть хотя бы одна запись часов
            if employee.hours_by_date:
                employees.append(employee)
        
        if not employees:
            raise ExcelImportError("Не найдено ни одного сотрудника с данными о часах")
        
        return employees
    
    except pd.errors.EmptyDataError:
        raise ExcelImportError("Файл пустой или поврежден")
    except FileNotFoundError:
        raise ExcelImportError(f"Файл не найден: {filepath}")
    except Exception as e:
        if isinstance(e, ExcelImportError):
            raise
        raise ExcelImportError(f"Ошибка чтения файла: {str(e)}")


def get_import_summary(employees: List[EmployeeData]) -> Dict:
    """
    Получить сводку по импортированным данным
    
    Returns:
        Dict с информацией: количество сотрудников, диапазон дат, общие часы
    """
    if not employees:
        return {
            'employee_count': 0,
            'total_hours': 0,
            'date_range': (None, None),
            'unique_dates': set()
        }
    
    total_hours = sum(emp.get_total_hours() for emp in employees)
    
    # Собираем все уникальные даты
    all_dates = set()
    for emp in employees:
        all_dates.update(emp.hours_by_date.keys())
    
    if all_dates:
        sorted_dates = sorted(all_dates)
        date_range = (sorted_dates[0], sorted_dates[-1])
    else:
        date_range = (None, None)
    
    return {
        'employee_count': len(employees),
        'total_hours': total_hours,
        'date_range': date_range,
        'unique_dates': all_dates
    }
