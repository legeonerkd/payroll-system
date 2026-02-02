from dataclasses import dataclass


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

    @classmethod
    def from_row(cls, row):
        return cls(
            id=row["id"],
            name=row["name"],
            rate=row["rate"],
            has_bank_account=bool(row["has_bank_account"]),
            bank_name=row["bank_name"],
            iban=row["iban"],
            bic=row["bic"],
        )


# ==================================================
# PAYROLL ROW
# ==================================================
@dataclass
class PayrollRow:
    date: str            # ISO: YYYY-MM-DD
    date_ui: str         # UI: DD.MM.YYYY
    weekday: str         # Monday, Tuesday, ...
    hours: float
    rate: float
    amount: float


# ==================================================
# PAYROLL SUMMARY
# ==================================================
@dataclass
class PayrollSummary:
    total_hours: float
    gross_amount: float
    housing_deduction: float = 0.0
    utilities_deduction: float = 0.0
    net_amount: float = 0.0
