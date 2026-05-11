from __future__ import annotations

import shutil
import tempfile
import threading
from pathlib import Path
from tkinter import BooleanVar, IntVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_YEAR = 2025
DEFAULT_BANK = "standard_chartered_hk"


class TaxCalculatorApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("Tax Calculation")
        self.root.geometry("760x520")
        self.root.minsize(680, 460)

        self.year_var = IntVar(value=DEFAULT_YEAR)
        self.bank_var = StringVar(value=DEFAULT_BANK)
        self.no_hkex_var = BooleanVar(value=True)
        self.output_var = StringVar(value=str(PROJECT_ROOT / "outputs" / f"tax_report_{DEFAULT_YEAR}.xlsx"))
        self.files_var = StringVar(value="No PDF files selected")
        self.status_var = StringVar(value="Ready")
        self.selected_files: list[Path] = []

        self._build_layout()

    def _build_layout(self) -> None:
        root_frame = ttk.Frame(self.root, padding=20)
        root_frame.pack(fill="both", expand=True)
        root_frame.columnconfigure(1, weight=1)
        root_frame.rowconfigure(7, weight=1)

        title = ttk.Label(root_frame, text="Hong Kong Overseas Income Tax Calculator", font=("TkDefaultFont", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(root_frame, text="Tax year").grid(row=1, column=0, sticky="w", pady=6)
        year_spinbox = ttk.Spinbox(root_frame, from_=2000, to=2100, textvariable=self.year_var, width=10)
        year_spinbox.grid(row=1, column=1, sticky="w", pady=6)
        year_spinbox.bind("<FocusOut>", lambda _event: self._refresh_default_output())

        ttk.Label(root_frame, text="Bank parser").grid(row=2, column=0, sticky="w", pady=6)
        bank_box = ttk.Combobox(root_frame, textvariable=self.bank_var, values=[DEFAULT_BANK], state="readonly")
        bank_box.grid(row=2, column=1, sticky="ew", pady=6)

        ttk.Label(root_frame, text="PDF files").grid(row=3, column=0, sticky="nw", pady=6)
        ttk.Label(root_frame, textvariable=self.files_var, wraplength=460).grid(row=3, column=1, sticky="ew", pady=6)
        ttk.Button(root_frame, text="Choose PDFs", command=self._choose_pdfs).grid(row=3, column=2, sticky="e", padx=(12, 0), pady=6)

        ttk.Label(root_frame, text="Output Excel").grid(row=4, column=0, sticky="w", pady=6)
        ttk.Entry(root_frame, textvariable=self.output_var).grid(row=4, column=1, sticky="ew", pady=6)
        ttk.Button(root_frame, text="Choose Output", command=self._choose_output).grid(row=4, column=2, sticky="e", padx=(12, 0), pady=6)

        ttk.Checkbutton(
            root_frame,
            text="Disable HKEX online lookup",
            variable=self.no_hkex_var,
        ).grid(row=5, column=1, sticky="w", pady=6)

        self.generate_button = ttk.Button(root_frame, text="Generate Report", command=self._start_report)
        self.generate_button.grid(row=6, column=1, sticky="w", pady=(16, 10))

        status_frame = ttk.LabelFrame(root_frame, text="Status", padding=12)
        status_frame.grid(row=7, column=0, columnspan=3, sticky="nsew", pady=(8, 0))
        status_frame.columnconfigure(0, weight=1)
        status_frame.rowconfigure(0, weight=1)
        self.status_label = ttk.Label(status_frame, textvariable=self.status_var, wraplength=650, justify="left")
        self.status_label.grid(row=0, column=0, sticky="nw")

    def _choose_pdfs(self) -> None:
        filenames = filedialog.askopenfilenames(
            parent=self.root,
            title="Choose bank statement PDFs",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not filenames:
            return
        self.selected_files = [Path(name) for name in filenames]
        shown = ", ".join(path.name for path in self.selected_files[:5])
        if len(self.selected_files) > 5:
            shown += f", and {len(self.selected_files) - 5} more"
        self.files_var.set(shown)
        self.status_var.set(f"Selected {len(self.selected_files)} PDF file(s).")

    def _choose_output(self) -> None:
        filename = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save Excel report",
            defaultextension=".xlsx",
            initialdir=str(PROJECT_ROOT / "outputs"),
            initialfile=f"tax_report_{self.year_var.get()}.xlsx",
            filetypes=[("Excel workbook", "*.xlsx"), ("All files", "*.*")],
        )
        if filename:
            self.output_var.set(filename)

    def _refresh_default_output(self) -> None:
        current = Path(self.output_var.get())
        if current.name.startswith("tax_report_"):
            self.output_var.set(str(PROJECT_ROOT / "outputs" / f"tax_report_{self.year_var.get()}.xlsx"))

    def _start_report(self) -> None:
        if not self.selected_files:
            messagebox.showwarning("Missing PDFs", "Please choose one or more PDF files first.")
            return
        output_text = self.output_var.get().strip()
        if not output_text:
            messagebox.showwarning("Missing output", "Please choose where to save the Excel report.")
            return

        self.generate_button.configure(state="disabled")
        self.status_var.set("Generating report. This may take a moment...")
        worker = threading.Thread(target=self._run_report, daemon=True)
        worker.start()

    def _run_report(self) -> None:
        try:
            from workflow import run_tax_calculation

            with tempfile.TemporaryDirectory(prefix="tax_calculation_upload_") as temp_dir:
                input_dir = Path(temp_dir)
                self._copy_selected_pdfs(input_dir)
                summary = run_tax_calculation(
                    year=self.year_var.get(),
                    bank=self.bank_var.get(),
                    input_dir=input_dir,
                    output_path=Path(self.output_var.get()).expanduser(),
                    rules_dir=PROJECT_ROOT / "tax_rules",
                    hkex_enabled=not self.no_hkex_var.get(),
                )
            message = (
                "Report generated successfully.\n\n"
                f"Parsed PDFs: {summary.parsed_pdfs}\n"
                f"Income records: {summary.income_records}\n"
                f"Rows needing review: {summary.rows_needing_review}\n"
                f"Wrote: {summary.output_path}"
            )
            self.root.after(0, self._show_success, message)
        except Exception as exc:  # noqa: BLE001 - show GUI users the actionable error.
            self.root.after(0, self._show_error, str(exc))

    def _copy_selected_pdfs(self, input_dir: Path) -> None:
        seen_names: dict[str, int] = {}
        for source in self.selected_files:
            count = seen_names.get(source.name, 0)
            seen_names[source.name] = count + 1
            if count:
                destination = input_dir / f"{source.stem}_{count}{source.suffix}"
            else:
                destination = input_dir / source.name
            shutil.copy2(source, destination)

    def _show_success(self, message: str) -> None:
        self.status_var.set(message)
        self.generate_button.configure(state="normal")
        messagebox.showinfo("Report generated", message)

    def _show_error(self, error: str) -> None:
        self.status_var.set(f"Error: {error}")
        self.generate_button.configure(state="normal")
        messagebox.showerror("Could not generate report", error)


def main() -> None:
    root = Tk()
    TaxCalculatorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
