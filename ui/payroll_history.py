import tkinter as tk
from tkinter import ttk
from services.report_service import preview_payroll_pdf_from_history


class PayrollHistory(tk.Toplevel):
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Payroll History")
        self.geometry("700x400")

        self.db = db

        self.tree = ttk.Treeview(
            self,
            columns=("id", "employee", "period", "created", "net"),
            show="headings"
        )

        self.tree.heading("id", text="ID")
        self.tree.heading("employee", text="Employee")
        self.tree.heading("period", text="Period")
        self.tree.heading("created", text="Created")
        self.tree.heading("net", text="Net amount")

        self.tree.column("id", width=50, anchor="center")

        self.tree.pack(fill="both", expand=True, padx=10, pady=10)

        self.tree.bind("<Double-1>", self._open_pdf)

        self._load()

    def _load(self):
        for r in self.db.get_payrolls():
            self.tree.insert(
                "",
                "end",
                values=(
                    r["id"],
                    r["name"],
                    f"{r['period_from']} – {r['period_to']}",
                    r["created_at"],
                    f"{r['net_amount']:.2f} €"
                )
            )

    def _open_pdf(self, event):
        item = self.tree.selection()
        if not item:
            return

        payroll_id = self.tree.item(item[0])["values"][0]
        payroll, days = self.db.get_payroll_full(payroll_id)
        preview_payroll_pdf_from_history(payroll, days)
