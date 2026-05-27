import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
import os


class HoursExportWindow(tk.Toplevel):
    """Окно для экспорта истории отработанных часов"""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.title("Export Hours History")
        self.geometry("800x500")
        self.db = db
        
        self._build_ui()
        self._load_data()
    
    def _build_ui(self):
        """Построение интерфейса"""
        # Заголовок
        header = ttk.Frame(self, style="Card.TFrame", padding=12)
        header.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(
            header, 
            text="📊 Work Hours History", 
            font=("Segoe UI", 12, "bold")
        ).pack(side="left")
        
        ttk.Button(
            header,
            text="📥 Export to CSV",
            command=self._export_csv,
            style="Success.TButton"
        ).pack(side="right", padx=5)
        
        ttk.Button(
            header,
            text="🔄 Refresh",
            command=self._load_data,
            style="Accent.TButton"
        ).pack(side="right")
        
        # Таблица
        table_frame = ttk.Frame(self)
        table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(table_frame, orient="vertical")
        v_scroll.pack(side="right", fill="y")
        
        h_scroll = ttk.Scrollbar(table_frame, orient="horizontal")
        h_scroll.pack(side="bottom", fill="x")
        
        # Treeview
        self.tree = ttk.Treeview(
            table_frame,
            columns=("employee", "date", "hours", "rate", "amount"),
            show="headings",
            yscrollcommand=v_scroll.set,
            xscrollcommand=h_scroll.set
        )
        
        v_scroll.config(command=self.tree.yview)
        h_scroll.config(command=self.tree.xview)
        
        # Заголовки
        self.tree.heading("employee", text="Employee")
        self.tree.heading("date", text="Date")
        self.tree.heading("hours", text="Hours")
        self.tree.heading("rate", text="Rate (€/h)")
        self.tree.heading("amount", text="Amount (€)")
        
        # Ширина колонок
        self.tree.column("employee", width=200, anchor="w")
        self.tree.column("date", width=120, anchor="center")
        self.tree.column("hours", width=100, anchor="center")
        self.tree.column("rate", width=120, anchor="center")
        self.tree.column("amount", width=120, anchor="e")
        
        self.tree.pack(fill="both", expand=True)
        
        # Zebra stripes
        self.tree.tag_configure("odd", background="#f9f9f9")
        self.tree.tag_configure("even", background="#ffffff")
        
        # Статистика внизу
        stats_frame = ttk.Frame(self, style="Card.TFrame", padding=12)
        stats_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.stats_label = ttk.Label(
            stats_frame,
            text="Total records: 0 | Total hours: 0.0 | Total amount: 0.00 €",
            font=("Segoe UI", 10, "bold"),
            foreground="#2563eb"
        )
        self.stats_label.pack()
    
    def _load_data(self):
        """Загрузка данных из БД"""
        self.tree.delete(*self.tree.get_children())
        
        hours_data = self.db.get_all_hours()
        
        total_hours = 0.0
        total_amount = 0.0
        
        for idx, row in enumerate(hours_data):
            employee = row["employee_name"]
            work_date = row["work_date"]
            hours = row["hours"]
            rate = row["rate"]
            amount = hours * rate
            
            total_hours += hours
            total_amount += amount
            
            # Форматируем дату для отображения
            try:
                date_obj = datetime.strptime(work_date, "%Y-%m-%d")
                display_date = date_obj.strftime("%d-%m-%Y")
            except:
                display_date = work_date
            
            tag = "odd" if idx % 2 == 0 else "even"
            
            self.tree.insert(
                "",
                "end",
                values=(
                    employee,
                    display_date,
                    f"{hours:.1f}",
                    f"{rate:.2f}",
                    f"{amount:.2f}"
                ),
                tags=(tag,)
            )
        
        # Обновляем статистику
        count = len(hours_data)
        self.stats_label.config(
            text=f"Total records: {count} | Total hours: {total_hours:.1f} | Total amount: {total_amount:.2f} €"
        )
    
    def _export_csv(self):
        """Экспорт в CSV файл"""
        try:
            # Диалог сохранения файла
            default_filename = f"hours_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            
            filepath = filedialog.asksaveasfilename(
                defaultextension=".csv",
                initialfile=default_filename,
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Hours History"
            )
            
            if not filepath:
                return  # Пользователь отменил
            
            # Экспортируем данные
            self.db.export_hours_to_csv(filepath)
            
            # Показываем сообщение об успехе
            result = messagebox.askyesno(
                "Export Successful",
                f"Hours history exported to:\n{filepath}\n\nOpen the file?",
                icon="info"
            )
            
            if result:
                # Открываем файл в системном приложении
                os.startfile(filepath)
        
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export:\n{str(e)}")
