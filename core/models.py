from dataclasses import dataclass
from typing import Optional


# ======================================================
# EMPLOYEE
# ======================================================
@dataclass
class Employee:
    id: int
    name: str
    rate: float

    has_bank_account: bool = False
    bank_name: Optional[str] = None
    iban: Optional[str] = None
    bic: Optional[str] = None

    @classmethod
    def from_row(cls, row):
        """
        Создание Employee из sqlite3.Row
        """
        return cls(
            id=row["id"],
            name=row["name"],
            rate=row["rate"],
            has_bank_account=bool(row["has_bank_account"]),
            bank_name=row["bank_name"],
            iban=row["iban"],
            bic=row["bic"],
        )


# ======================================================
# PAYROLL ROW (один день)
# ======================================================
@dataclass
class PayrollRow:
    date_iso: str          # YYYY-MM-DD
    date_ui: str           # DD-MM-YYYY
    weekday: str
    hours: float
    rate: float

    @property
    def amount(self) -> float:
        return round(self.hours * self.rate, 2)


# ======================================================
# PAYROLL SUMMARY
# ======================================================
@dataclass
class PayrollSummary:
    total_hours: float
    rate: float
    gross_amount: float

    housing_deduction: float = 0.0
    utilities_deduction: float = 0.0

    @property
    def total_deductions(self) -> float:
        return round(self.housing_deduction + self.utilities_deduction, 2)

    @property
    def net_amount(self) -> float:
        return round(self.gross_amount - self.total_deductions, 2)
