from dataclasses import dataclass
from sqlite3 import Row


# ==================================================
# EMPLOYEE
# ==================================================
@dataclass
class Employee:
    id: int
    name: str
    rate: float

    has_bank_account: bool = False
    bank_name: str | None = None
    iban: str | None = None
    bic: str | None = None

    @staticmethod
    def from_row(row: Row) -> "Employee":
        return Employee(
            id=row["id"],
            name=row["name"],
            rate=row["rate"],
            has_bank_account=bool(row["has_bank_account"]),
            bank_name=row["bank_name"],
            iban=row["iban"],
            bic=row["bic"],
        )


# ==================================================
# PAYROLL ROW (ONE DAY)
# ==================================================
@dataclass
class PayrollRow:
    date_iso: str
    date_ui: str
    weekday: str
    hours: float
    rate: float          # 🔴 ДОБАВЛЕНО
    amount: float


# ==================================================
# PAYROLL SUMMARY
# ==================================================
@dataclass
class PayrollSummary:
    total_hours: float
    gross_amount: float
    total_deductions: float = 0.0
    net_amount: float = 0.0
