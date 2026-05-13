import os
import traceback
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

import matplotlib

matplotlib.use("TkAgg")

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from sinusoidal_fit import (
    build_spike_metric_rows,
    build_sinusoid_formula_rows,
    build_spline_formula_rows,
    build_average_spike_from_tsvs,
    calculate_sinusoid_absolute_area,
    calculate_sinusoid_area,
    calculate_spline_area,
    calculate_spike_metrics,
    export_average_spikes_to_excel,
    export_analysis_to_excel,
    fit_sinusoidal,
    format_sinusoid_equation,
    load_previous_analysis_workbook,
    load_xy_from_excel,
    make_exact_spline,
    save_average_spike_plot,
    sinusoid,
)


class CurveAnalyzerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Curve Analyzer")
        self.root.geometry("1160x760")
        self.root.minsize(980, 640)

        self.file_path_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="exact")
        self.status_var = tk.StringVar(value="Select an Excel file to begin.")
        self.output_path_var = tk.StringVar(value="No results exported yet.")
        self.last_result = None
        self.note_artist = None
        self.metric_text_artists = []
        self._drag_artist = None

        self._build_ui()
        self._draw_empty_plot()

    def _build_ui(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TButton", padding=(10, 6))
        style.configure("Primary.TButton", padding=(12, 7), font=("Segoe UI", 10, "bold"))
        style.configure("Header.TLabel", font=("Segoe UI", 13, "bold"))

        main = ttk.Frame(self.root, padding=14)
        main.pack(fill=tk.BOTH, expand=True)
        main.columnconfigure(0, weight=1)
        main.rowconfigure(3, weight=1)

        header = ttk.Label(
            main,
            text="Curve Analyzer",
            style="Header.TLabel",
        )
        header.grid(row=0, column=0, sticky="w", pady=(0, 10))

        file_frame = ttk.LabelFrame(main, text="Excel File")
        file_frame.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        file_frame.columnconfigure(0, weight=1)

        file_entry = ttk.Entry(file_frame, textvariable=self.file_path_var)
        file_entry.grid(row=0, column=0, sticky="ew", padx=(10, 8), pady=10)

        browse_button = ttk.Button(file_frame, text="Browse", command=self.browse_file)
        browse_button.grid(row=0, column=1, padx=(0, 10), pady=10)

        options = ttk.Frame(main)
        options.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        options.columnconfigure(1, weight=1)

        mode_frame = ttk.LabelFrame(options, text="Formula Mode")
        mode_frame.grid(row=0, column=0, sticky="w")

        ttk.Radiobutton(
            mode_frame,
            text="Exact interpolated curve",
            variable=self.mode_var,
            value="exact",
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(8, 2))

        ttk.Radiobutton(
            mode_frame,
            text="Sinusoidal best fit",
            variable=self.mode_var,
            value="sinusoid",
        ).grid(row=1, column=0, sticky="w", padx=10, pady=(2, 8))

        action_frame = ttk.Frame(options)
        action_frame.grid(row=0, column=1, sticky="e")

        self.analyze_button = ttk.Button(
            action_frame,
            text="Analyze and Export",
            command=self.analyze,
            style="Primary.TButton",
        )
        self.analyze_button.grid(row=0, column=0, padx=(0, 8))

        self.export_button = ttk.Button(
            action_frame,
            text="Export As",
            command=self.export_as,
            state=tk.DISABLED,
        )
        self.export_button.grid(row=0, column=1, padx=(0, 8))

        self.open_folder_button = ttk.Button(
            action_frame,
            text="Open Output Folder",
            command=self.open_output_folder,
            state=tk.DISABLED,
        )
        self.open_folder_button.grid(row=0, column=2)

        self.average_tsv_button = ttk.Button(
            action_frame,
            text="Average Spikes",
            command=self.average_tsv_spikes,
        )
        self.average_tsv_button.grid(row=0, column=3, padx=(8, 0))

        self.open_previous_button = ttk.Button(
            action_frame,
            text="Open Previous Analysis",
            command=self.open_previous_analysis,
        )
        self.open_previous_button.grid(row=0, column=4, padx=(8, 0))

        content = ttk.PanedWindow(main, orient=tk.HORIZONTAL)
        content.grid(row=3, column=0, sticky="nsew")

        left = ttk.Frame(content, padding=(0, 0, 10, 0))
        right = ttk.Frame(content)
        content.add(left, weight=1)
        content.add(right, weight=3)

        left.rowconfigure(1, weight=1)
        left.columnconfigure(0, weight=1)

        output_label = ttk.Label(left, textvariable=self.output_path_var, wraplength=320)
        output_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.summary_text = ScrolledText(
            left,
            width=42,
            height=18,
            wrap=tk.WORD,
            font=("Consolas", 10),
        )
        self.summary_text.grid(row=1, column=0, sticky="nsew")
        self.summary_text.configure(state=tk.DISABLED)

        right.rowconfigure(0, weight=1)
        right.columnconfigure(0, weight=1)

        self.figure = Figure(figsize=(7, 5), dpi=100)
        self.axis = self.figure.add_subplot(111)
        self.canvas = FigureCanvasTkAgg(self.figure, master=right)
        self.canvas.get_tk_widget().grid(row=0, column=0, sticky="nsew")

        toolbar_frame = ttk.Frame(right)
        toolbar_frame.grid(row=1, column=0, sticky="ew")
        self.toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
        self.toolbar.update()

        status = ttk.Label(main, textvariable=self.status_var, anchor="w")
        status.grid(row=4, column=0, sticky="ew", pady=(10, 0))

    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="Select Excel file",
            filetypes=[
                ("Excel workbooks", "*.xlsx *.xlsm"),
                ("All files", "*.*"),
            ],
        )

        if file_path:
            self.file_path_var.set(file_path)
            self.status_var.set("Excel file selected.")

    def analyze(self):
        file_path = Path(self.file_path_var.get().strip())

        if not file_path:
            messagebox.showwarning("No file selected", "Please choose an Excel file.")
            return

        if not file_path.exists():
            messagebox.showerror("File not found", f"Could not find:\n{file_path}")
            return

        self._set_busy(True)

        try:
            result = self._build_result(file_path)
            output_path = file_path.with_name(f"{file_path.stem}_analysis_results.xlsx")
            export_analysis_to_excel(
                output_path,
                result["metadata_rows"],
                result["area_rows"],
                result["formula_rows"],
                result["spike_metric_rows"],
                result["data_rows"],
            )

            result["output_path"] = output_path
            self.last_result = result

            self._write_summary(result)
            self._draw_result(result)
            self.output_path_var.set(f"Results exported to: {output_path}")
            self.status_var.set("Analysis complete.")
            self.export_button.configure(state=tk.NORMAL)
            self.open_folder_button.configure(state=tk.NORMAL)
        except Exception as error:
            traceback.print_exc()
            messagebox.showerror("Analysis failed", str(error))
            self.status_var.set("Analysis failed.")
        finally:
            self._set_busy(False)

    def _build_result(self, file_path):
        x_data, y_data, sheet_name, used_rows, skipped_rows = load_xy_from_excel(file_path)
        mode = self.mode_var.get()
        spike_metrics = calculate_spike_metrics(x_data, y_data)
        spike_metric_rows = build_spike_metric_rows(spike_metrics)

        if mode == "sinusoid":
            A, B, C, D = fit_sinusoidal(x_data, y_data)
            x_min = float(np.min(x_data))
            x_max = float(np.max(x_data))
            signed_area = calculate_sinusoid_area(A, B, C, D, x_min, x_max)
            absolute_area = calculate_sinusoid_absolute_area(A, B, C, D, x_min, x_max)
            equation = format_sinusoid_equation(A, B, C, D)

            metadata_rows = [
                ("Source file", str(file_path)),
                ("Worksheet", sheet_name),
                ("Analysis mode", "Sinusoidal best fit"),
                ("Numeric data rows used", used_rows),
                ("Rows skipped", skipped_rows),
                ("Formula type", "y = A * sin(B*x + C) + D"),
            ]
            area_rows = [
                ("x start", x_min),
                ("x end", x_max),
                ("Signed area under curve", signed_area),
                ("Absolute area under curve", absolute_area),
            ]

            return {
                "mode": "sinusoid",
                "source_file": file_path,
                "sheet_name": sheet_name,
                "x": x_data,
                "y": y_data,
                "parameters": (A, B, C, D),
                "signed_area": signed_area,
                "absolute_area": absolute_area,
                "equation": equation,
                "metadata_rows": metadata_rows,
                "area_rows": area_rows,
                "formula_rows": build_sinusoid_formula_rows(A, B, C, D),
                "spike_metrics": spike_metrics,
                "spike_metric_rows": spike_metric_rows,
                "data_rows": [
                    {"x": float(x_value), "y": float(y_value)}
                    for x_value, y_value in zip(x_data, y_data)
                ],
            }

        x_data, y_data, spline = make_exact_spline(x_data, y_data)
        signed_area, absolute_area = calculate_spline_area(spline, x_data[0], x_data[-1])

        metadata_rows = [
            ("Source file", str(file_path)),
            ("Worksheet", sheet_name),
            ("Analysis mode", "Exact cubic spline interpolation"),
            ("Numeric data rows used", used_rows),
            ("Rows skipped", skipped_rows),
            ("Unique x values", len(x_data)),
            (
                "Formula type",
                "Piecewise cubic spline: y = a*(x-x0)^3 + b*(x-x0)^2 + c*(x-x0) + d",
            ),
        ]
        area_rows = [
            ("x start", float(x_data[0])),
            ("x end", float(x_data[-1])),
            ("Signed area under curve", signed_area),
            ("Absolute area under curve", absolute_area),
        ]

        return {
            "mode": "exact",
            "source_file": file_path,
            "sheet_name": sheet_name,
            "x": x_data,
            "y": y_data,
            "spline": spline,
            "signed_area": signed_area,
            "absolute_area": absolute_area,
            "metadata_rows": metadata_rows,
            "area_rows": area_rows,
            "formula_rows": build_spline_formula_rows(x_data, spline),
            "spike_metrics": spike_metrics,
            "spike_metric_rows": spike_metric_rows,
            "data_rows": [
                {"x": float(x_value), "y": float(y_value)}
                for x_value, y_value in zip(x_data, y_data)
            ],
        }

    def open_previous_analysis(self):
        file_path = filedialog.askopenfilename(
            title="Open previous Curve Analyzer workbook",
            filetypes=[
                ("Excel workbooks", "*.xlsx *.xlsm"),
                ("All files", "*.*"),
            ],
        )

        if not file_path:
            return

        self._set_busy(True)
        try:
            result = load_previous_analysis_workbook(file_path)
            result["output_path"] = Path(file_path)
            self.last_result = result
            self._write_summary(result)
            if "x" in result and "y" in result:
                self._draw_result(result)
                self.export_button.configure(state=tk.NORMAL)
            else:
                self._draw_empty_plot()
                self.export_button.configure(state=tk.DISABLED)
            self.output_path_var.set(f"Loaded previous analysis: {file_path}")
            self.status_var.set("Previous analysis loaded.")
            self.open_folder_button.configure(state=tk.NORMAL)
        except Exception as error:
            traceback.print_exc()
            messagebox.showerror("Open previous analysis failed", str(error))
            self.status_var.set("Open previous analysis failed.")
        finally:
            self._set_busy(False)

    def average_tsv_spikes(self):
        file_paths = filedialog.askopenfilenames(
            title="Select TSV files with EEG spikes",
            filetypes=[
                ("TSV/TXT/CSV files", "*.tsv *.txt *.csv"),
                ("All files", "*.*"),
            ],
        )

        if not file_paths:
            return

        self._set_busy(True)

        try:
            average_result = build_average_spike_from_tsvs(
                file_paths,
                progress_callback=self._set_average_progress,
            )
            first_file = Path(file_paths[0])
            stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_excel = first_file.with_name(f"average_epileptiform_spikes_{stamp}.xlsx")
            output_plot = first_file.with_name(f"average_epileptiform_spikes_{stamp}.png")

            export_average_spikes_to_excel(output_excel, average_result)
            save_average_spike_plot(output_plot, average_result)

            result = self._build_average_spike_analysis_result(
                output_excel,
                average_result,
            )
            result["output_path"] = output_excel
            self.last_result = result

            self._write_summary(result)
            self._draw_result(result)
            self.output_path_var.set(
                f"Average spike exported to: {output_excel}\nGraph exported to: {output_plot}"
            )
            self.status_var.set(
                f"Average complete: {len(average_result['spikes'])} spikes used."
            )
            self.export_button.configure(state=tk.NORMAL)
            self.open_folder_button.configure(state=tk.NORMAL)
        except Exception as error:
            traceback.print_exc()
            messagebox.showerror("Average spikes failed", str(error))
            self.status_var.set("Average spikes failed.")
        finally:
            self._set_busy(False)

    def _set_average_progress(self, message):
        self.status_var.set(message)
        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, message)
        self.summary_text.configure(state=tk.DISABLED)
        self.root.update_idletasks()

    def _build_average_spike_analysis_result(self, source_file, average_result):
        x_data, y_data, spline = make_exact_spline(
            average_result["x_ms"],
            average_result["average_y"],
        )
        signed_area, absolute_area = calculate_spline_area(spline, x_data[0], x_data[-1])
        spike_metrics = calculate_spike_metrics(x_data, y_data)
        spike_metric_rows = build_spike_metric_rows(spike_metrics)

        metadata_rows = [
            ("Source file", str(source_file)),
            ("Worksheet", "Average Spike"),
            ("Analysis mode", "Average TSV epileptiform spike"),
            ("Spikes averaged", len(average_result["spikes"])),
            ("Files analysed", len(average_result["file_rows"])),
            ("Pre-peak window (ms)", average_result["pre_ms"]),
            ("Post-peak window (ms)", average_result["post_ms"]),
            ("Spike alignment", average_result.get("alignment", "")),
            ("Dominant average polarity", average_result.get("dominant_polarity", "")),
            ("Positive aligned spikes", average_result.get("positive_alignment_count", "")),
            ("Negative aligned spikes", average_result.get("negative_alignment_count", "")),
            (
                "Formula type",
                "Piecewise cubic spline: y = a*(x-x0)^3 + b*(x-x0)^2 + c*(x-x0) + d",
            ),
        ]
        area_rows = [
            ("x start", float(x_data[0])),
            ("x end", float(x_data[-1])),
            ("Signed area under curve", signed_area),
            ("Absolute area under curve", absolute_area),
        ]

        return {
            "mode": "average_spike",
            "source_file": Path(source_file),
            "sheet_name": "Average Spike",
            "x": x_data,
            "y": y_data,
            "spline": spline,
            "signed_area": signed_area,
            "absolute_area": absolute_area,
            "metadata_rows": metadata_rows,
            "area_rows": area_rows,
            "formula_rows": build_spline_formula_rows(x_data, spline),
            "spike_metrics": spike_metrics,
            "spike_metric_rows": spike_metric_rows,
            "data_rows": [
                {"x": float(x_value), "y": float(y_value)}
                for x_value, y_value in zip(x_data, y_data)
            ],
        }

    def export_as(self):
        if not self.last_result:
            messagebox.showwarning("No results", "Run an analysis first.")
            return

        source_file = self.last_result["source_file"]
        output_path = filedialog.asksaveasfilename(
            title="Save results workbook",
            initialdir=str(source_file.parent),
            initialfile=f"{source_file.stem}_analysis_results.xlsx",
            defaultextension=".xlsx",
            filetypes=[("Excel workbook", "*.xlsx")],
        )

        if not output_path:
            return

        try:
            export_analysis_to_excel(
                output_path,
                self.last_result["metadata_rows"],
                self.last_result["area_rows"],
                self.last_result["formula_rows"],
                self.last_result["spike_metric_rows"],
                self.last_result.get("data_rows"),
            )
            self.last_result["output_path"] = Path(output_path)
            self.output_path_var.set(f"Results exported to: {output_path}")
            self.status_var.set("Results exported.")
            self.open_folder_button.configure(state=tk.NORMAL)
        except Exception as error:
            traceback.print_exc()
            messagebox.showerror("Export failed", str(error))

    def open_output_folder(self):
        if not self.last_result or "output_path" not in self.last_result:
            messagebox.showwarning("No output", "Export results first.")
            return

        output_path = Path(self.last_result["output_path"])
        if output_path.exists():
            os.startfile(output_path.parent)
        else:
            os.startfile(output_path.parent if output_path.parent.exists() else ".")

    def _write_summary(self, result):
        lines = [
            f"Source: {result['source_file']}",
            f"Worksheet: {result['sheet_name']}",
            "",
            f"Mode: {self._mode_label(result)}",
        ]

        if "signed_area" in result and "absolute_area" in result:
            lines.extend(
                [
                    f"x start: {self._format_number(result['area_rows'][0][1])}",
                    f"x end:   {self._format_number(result['area_rows'][1][1])}",
                    "",
                    f"Signed area:   {result['signed_area']:.6f}",
                    f"Absolute area: {result['absolute_area']:.6f}",
                ]
            )
        elif result.get("area_rows"):
            lines.extend(["", "Area results:"])
            for key, value in result["area_rows"]:
                lines.append(f"{key}: {value}")

        if result.get("spike_metrics"):
            lines.extend(
                [
                    "",
                    "Spike metrics:",
                    f"Baseline y: {result['spike_metrics']['Baseline y (median)']:.6f}",
                    f"Polarity: {result['spike_metrics']['Spike polarity']}",
                    f"Peak x: {result['spike_metrics']['Peak x']:.6f}",
                    f"Peak y: {result['spike_metrics']['Peak y']:.6f}",
                    (
                        "Peak amplitude: "
                        f"{result['spike_metrics']['Peak amplitude (absolute from baseline)']:.6f}"
                    ),
                    self._format_optional_metric(
                        "Rise time (10-90%)",
                        result["spike_metrics"]["Rise time (10-90%)"],
                    ),
                    self._format_optional_metric(
                        "Decay time (90-10%)",
                        result["spike_metrics"]["Decay time (90-10%)"],
                    ),
                ]
            )

        if result.get("metadata_rows"):
            lines.extend(["", "Workbook metadata:"])
            for key, value in result["metadata_rows"]:
                lines.append(f"{key}: {value}")

        if result["mode"] == "sinusoid":
            A, B, C, D = result["parameters"]
            lines.extend(
                [
                    "",
                    "Equation:",
                    result["equation"],
                    "",
                    f"A = {A:.8g}",
                    f"B = {B:.8g}",
                    f"C = {C:.8g}",
                    f"D = {D:.8g}",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    f"Formula rows: {len(result.get('formula_rows', []))}",
                ]
            )

        self.summary_text.configure(state=tk.NORMAL)
        self.summary_text.delete("1.0", tk.END)
        self.summary_text.insert(tk.END, "\n".join(lines))
        self.summary_text.configure(state=tk.DISABLED)

    def _mode_label(self, result):
        if result["mode"] == "exact":
            return "Exact cubic spline interpolation"
        if result["mode"] == "sinusoid":
            return "Sinusoidal best fit"
        if result["mode"] == "previous_average_spike":
            return "Previous average spike analysis"
        if result["mode"] == "previous_data":
            return "Previous analysis with saved x/y data"
        if result["mode"] == "previous_summary":
            return "Previous workbook summary"
        return "Average TSV epileptiform spike"

    def _format_optional_metric(self, label, value):
        if value is None:
            return f"{label}: not found"
        return f"{label}: {value:.6f}"

    def _format_number(self, value):
        try:
            return f"{float(value):.6f}"
        except (TypeError, ValueError):
            return str(value)

    def _draw_empty_plot(self):
        self.axis.clear()
        self.note_artist = None
        self.metric_text_artists = []
        self.axis.set_title("No data loaded")
        self.axis.set_xlabel("x")
        self.axis.set_ylabel("y")
        self.axis.grid(True)
        self.figure.tight_layout()
        self.canvas.draw()

    def _draw_result(self, result):
        self.axis.clear()
        self.note_artist = None
        self.metric_text_artists = []

        x_data = result["x"]
        y_data = result["y"]
        spike_metrics = result["spike_metrics"]

        if result["mode"] == "sinusoid":
            A, B, C, D = result["parameters"]
            x_fit = np.linspace(np.min(x_data), np.max(x_data), 1200)
            y_fit = sinusoid(x_fit, A, B, C, D)
            line_label = "Fitted curve"
            title = f"Sinusoidal Best Fit: {result['source_file'].name}"
            plot_note = (
                f"{result['equation']}\n"
                f"Signed area = {result['signed_area']:.4f}\n"
                f"Absolute area = {result['absolute_area']:.4f}"
            )
        else:
            spline = result["spline"]
            x_fit = np.linspace(np.min(x_data), np.max(x_data), 2000)
            y_fit = spline(x_fit)
            line_label = "Exact interpolated curve"
            if result["mode"] in {"average_spike", "previous_average_spike"}:
                line_label = "Average spike curve"
                title = f"Average Epileptiform Spike: {result['source_file'].name}"
            else:
                title = f"Exact Interpolated Curve: {result['source_file'].name}"
            plot_note = (
                "Exact cubic spline interpolation\n"
                f"Signed area = {result['signed_area']:.4f}\n"
                f"Absolute area = {result['absolute_area']:.4f}"
            )

        for spike in result.get("overlay_spikes", []):
            self.axis.plot(
                spike["x_ms"],
                spike["y"],
                color="#1f77b4",
                alpha=0.14,
                linewidth=1,
                zorder=1,
            )

        scatter_label = (
            "Average spike data"
            if result["mode"] in {"average_spike", "previous_average_spike"}
            else "Original data"
        )
        self.axis.scatter(x_data, y_data, label=scatter_label, color="#1f5cff", s=28)
        self.axis.plot(x_fit, y_fit, label=line_label, color="#d7191c", linewidth=2)
        self.axis.scatter(
            [spike_metrics["Peak x"]],
            [spike_metrics["Peak y"]],
            label="Peak amplitude",
            color="#111111",
            s=50,
            marker="x",
            linewidths=2,
            zorder=5,
        )
        self._draw_spike_metric_markers(result, x_fit, y_fit)
        self.axis.fill_between(
            x_fit,
            y_fit,
            0,
            color="#d7191c",
            alpha=0.12,
            label="Area under curve",
        )
        self.axis.set_title(title)
        self.axis.set_xlabel("x")
        self.axis.set_ylabel("y")
        self.axis.grid(True)
        legend = self.axis.legend(loc="best")
        legend.set_draggable(True)
        self.note_artist = self.axis.text(
            0.02,
            0.98,
            plot_note,
            transform=self.axis.transAxes,
            verticalalignment="top",
            bbox={"facecolor": "white", "alpha": 0.85, "edgecolor": "gray"},
        )
        self.note_artist.set_picker(True)
        self._connect_note_dragging()
        self.figure.tight_layout()
        self.canvas.draw()

    def _draw_spike_metric_markers(self, result, x_fit, y_fit):
        spike_metrics = result["spike_metrics"]
        baseline = spike_metrics["Baseline y (median)"]
        peak_x = spike_metrics["Peak x"]
        peak_y = spike_metrics["Peak y"]
        amplitude = spike_metrics["Peak amplitude (absolute from baseline)"]

        self.axis.axhline(
            baseline,
            color="#555555",
            linewidth=1,
            linestyle=":",
            label="Baseline",
        )
        self.axis.annotate(
            "",
            xy=(peak_x, peak_y),
            xytext=(peak_x, baseline),
            arrowprops={
                "arrowstyle": "<->",
                "color": "#111111",
                "linewidth": 1.6,
            },
        )
        amplitude_text = self.axis.text(
            peak_x,
            (peak_y + baseline) / 2,
            f"Amplitude\n{amplitude:.4g}",
            color="#111111",
            fontsize=9,
            ha="left",
            va="center",
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        )
        amplitude_text.set_picker(True)
        self.metric_text_artists.append(amplitude_text)

        self._draw_time_range(
            x_fit,
            y_fit,
            spike_metrics["Rise start x (10% amplitude)"],
            spike_metrics["Rise end x (90% amplitude)"],
            "Rise time",
            "#238b45",
        )
        self._draw_time_range(
            x_fit,
            y_fit,
            spike_metrics["Decay start x (90% amplitude)"],
            spike_metrics["Decay end x (10% amplitude)"],
            "Decay time",
            "#f16913",
        )

    def _draw_time_range(self, x_fit, y_fit, x_start, x_end, label, color):
        if x_start is None or x_end is None:
            return

        if np.isclose(x_start, x_end):
            return

        start_y = float(np.interp(x_start, x_fit, y_fit))
        end_y = float(np.interp(x_end, x_fit, y_fit))
        mid_x = (x_start + x_end) / 2
        mid_y = float(np.interp(mid_x, x_fit, y_fit))

        self.axis.plot(
            [x_start, x_end],
            [start_y, end_y],
            color=color,
            linewidth=4,
            solid_capstyle="round",
            label=label,
            zorder=4,
        )
        self.axis.scatter(
            [x_start, x_end],
            [start_y, end_y],
            color=color,
            s=36,
            zorder=6,
        )
        label_text = self.axis.text(
            mid_x,
            mid_y,
            f"{label}\n{x_end - x_start:.4g}",
            color=color,
            fontsize=9,
            ha="center",
            va="bottom",
            bbox={"facecolor": "white", "alpha": 0.75, "edgecolor": "none"},
        )
        label_text.set_picker(True)
        self.metric_text_artists.append(label_text)

    def _connect_note_dragging(self):
        if hasattr(self, "_drag_connections_ready") and self._drag_connections_ready:
            return

        self.canvas.mpl_connect("button_press_event", self._on_plot_press)
        self.canvas.mpl_connect("motion_notify_event", self._on_plot_motion)
        self.canvas.mpl_connect("button_release_event", self._on_plot_release)
        self._drag_connections_ready = True

    def _on_plot_press(self, event):
        if event.inaxes != self.axis:
            return

        for artist in [self.note_artist, *self.metric_text_artists]:
            if artist is None:
                continue
            contains, _ = artist.contains(event)
            if contains:
                self._drag_artist = artist
                return

    def _on_plot_motion(self, event):
        if self._drag_artist is None or event.inaxes != self.axis:
            return

        self._drag_artist.set_position((event.xdata, event.ydata))
        self._drag_artist.set_transform(self.axis.transData)
        self.canvas.draw_idle()

    def _on_plot_release(self, event):
        self._drag_artist = None

    def _set_busy(self, busy):
        state = tk.DISABLED if busy else tk.NORMAL
        self.analyze_button.configure(state=state)
        self.status_var.set("Working..." if busy else self.status_var.get())
        self.root.update_idletasks()


def main():
    root = tk.Tk()
    app = CurveAnalyzerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
