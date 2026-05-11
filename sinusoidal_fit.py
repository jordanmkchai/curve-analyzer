import sys
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font
from openpyxl.utils import get_column_letter
from scipy.interpolate import CubicSpline
from scipy.optimize import curve_fit


def sinusoid(x, A, B, C, D):
    """Sinusoidal model: y = A * sin(B*x + C) + D."""
    return A * np.sin(B * x + C) + D


def estimate_initial_guess(x, y):
    """Estimate starting values for nonlinear least squares fitting."""
    if len(x) < 4:
        raise ValueError("At least 4 numeric x,y data points are required.")

    amplitude_guess = (np.max(y) - np.min(y)) / 2
    offset_guess = np.mean(y)

    # Estimate angular frequency B using the FFT.
    x_differences = np.diff(x)
    nonzero_differences = np.abs(x_differences[x_differences != 0])

    if len(nonzero_differences) == 0:
        raise ValueError("The x values must not all be the same.")

    x_spacing = np.mean(nonzero_differences)
    y_centered = y - offset_guess

    frequencies = np.fft.rfftfreq(len(x), d=x_spacing)
    fft_magnitudes = np.abs(np.fft.rfft(y_centered))

    # Ignore the zero-frequency term when finding the dominant frequency.
    if len(fft_magnitudes) > 1 and np.any(fft_magnitudes[1:] > 0):
        dominant_index = np.argmax(fft_magnitudes[1:]) + 1
        frequency_cycles = frequencies[dominant_index]
        angular_frequency_guess = 2 * np.pi * frequency_cycles
    else:
        angular_frequency_guess = 2 * np.pi / (np.max(x) - np.min(x))

    phase_guess = 0

    return amplitude_guess, angular_frequency_guess, phase_guess, offset_guess


def fit_sinusoidal(x_values, y_values):
    """Fit x,y data to y = A * sin(B*x + C) + D."""
    x_values, y_values = prepare_xy_values(x_values, y_values)

    initial_guess = estimate_initial_guess(x_values, y_values)

    fitted_parameters, covariance = curve_fit(
        sinusoid,
        x_values,
        y_values,
        p0=initial_guess,
        maxfev=10000,
    )

    A, B, C, D = fitted_parameters

    # Make the printed equation easier to read by keeping amplitude positive.
    if A < 0:
        A = -A
        C += np.pi

    # Normalize phase into the range [-pi, pi].
    C = (C + np.pi) % (2 * np.pi) - np.pi

    return A, B, C, D


def prepare_xy_values(x_values, y_values):
    """Sort x,y values and ensure each x value has one y value."""
    x_values = np.asarray(x_values, dtype=float)
    y_values = np.asarray(y_values, dtype=float)

    sorted_indices = np.argsort(x_values)
    x_values = x_values[sorted_indices]
    y_values = y_values[sorted_indices]

    unique_x = []
    unique_y = []

    for x_value, y_value in zip(x_values, y_values):
        if unique_x and np.isclose(x_value, unique_x[-1]):
            if not np.isclose(y_value, unique_y[-1]):
                raise ValueError(
                    "An exact y=f(x) formula is impossible because the same "
                    f"x value ({x_value}) has more than one y value."
                )
            continue

        unique_x.append(x_value)
        unique_y.append(y_value)

    if len(unique_x) < 4:
        raise ValueError("At least 4 unique numeric x,y data points are required.")

    return np.array(unique_x), np.array(unique_y)


def make_exact_spline(x_values, y_values):
    """Create a cubic spline that passes exactly through every data point."""
    x_values, y_values = prepare_xy_values(x_values, y_values)
    spline = CubicSpline(x_values, y_values, bc_type="natural")
    return x_values, y_values, spline


def calculate_spline_area(spline, x_min, x_max):
    """Calculate signed and absolute area under an exact cubic spline."""
    signed_area = float(spline.integrate(x_min, x_max))

    roots = spline.roots(extrapolate=False)
    roots = roots[np.isreal(roots)].real
    roots = roots[(roots > x_min) & (roots < x_max)]

    split_points = np.concatenate(([x_min], np.sort(roots), [x_max]))
    absolute_area = 0

    for start, end in zip(split_points[:-1], split_points[1:]):
        absolute_area += abs(float(spline.integrate(start, end)))

    return signed_area, absolute_area


def calculate_sinusoid_area(A, B, C, D, x_min, x_max):
    """Calculate the signed area under y = A*sin(B*x + C) + D."""
    if np.isclose(B, 0):
        return float((A * np.sin(C) + D) * (x_max - x_min))

    start_value = (-A / B) * np.cos(B * x_min + C) + D * x_min
    end_value = (-A / B) * np.cos(B * x_max + C) + D * x_max

    return float(end_value - start_value)


def calculate_sinusoid_absolute_area(A, B, C, D, x_min, x_max):
    """Calculate absolute area under y = A*sin(B*x + C) + D."""
    if x_max < x_min:
        x_min, x_max = x_max, x_min

    if np.isclose(A, 0) or np.isclose(B, 0):
        return abs(calculate_sinusoid_area(A, B, C, D, x_min, x_max))

    target = -D / A
    roots = []

    if abs(target) <= 1:
        base_angle = np.arcsin(target)
        candidate_angles = [base_angle, np.pi - base_angle]
        theta_start = B * x_min + C
        theta_end = B * x_max + C
        theta_min = min(theta_start, theta_end)
        theta_max = max(theta_start, theta_end)
        k_min = int(np.floor((theta_min - 2 * np.pi) / (2 * np.pi))) - 1
        k_max = int(np.ceil((theta_max + 2 * np.pi) / (2 * np.pi))) + 1

        for k in range(k_min, k_max + 1):
            for angle in candidate_angles:
                root = (angle + 2 * np.pi * k - C) / B
                if x_min < root < x_max:
                    roots.append(root)

    split_points = np.array([x_min, *sorted(set(np.round(roots, 12))), x_max])
    absolute_area = 0

    for start, end in zip(split_points[:-1], split_points[1:]):
        absolute_area += abs(calculate_sinusoid_area(A, B, C, D, start, end))

    return float(absolute_area)


def format_number(value, digits=10):
    """Format numbers for readable equations without unnecessary trailing zeros."""
    text = f"{value:.{digits}g}"
    if text == "-0":
        return "0"
    return text


def format_signed(value, digits=10):
    """Format a signed number for equations."""
    sign = "+" if value >= 0 else "-"
    return f"{sign} {format_number(abs(value), digits)}"


def format_sinusoid_equation(A, B, C, D, digits=6):
    """Format y = A*sin(B*x + C) + D as readable text."""
    c_sign = "+" if C >= 0 else "-"
    d_sign = "+" if D >= 0 else "-"
    return (
        f"y = {format_number(A, digits)} * sin("
        f"{format_number(B, digits)} * x {c_sign} {format_number(abs(C), digits)}) "
        f"{d_sign} {format_number(abs(D), digits)}"
    )


def format_spline_formula(a, b, c, d, x0, digits=10):
    """Format one cubic spline interval as readable text."""
    return (
        f"y = {format_number(a, digits)}*(x - {format_number(x0, digits)})^3 "
        f"{format_signed(b, digits)}*(x - {format_number(x0, digits)})^2 "
        f"{format_signed(c, digits)}*(x - {format_number(x0, digits)}) "
        f"{format_signed(d, digits)}"
    )


def build_spline_formula_rows(x_values, spline):
    """Build formula rows for Excel export."""
    rows = []

    for index in range(len(x_values) - 1):
        x0 = float(x_values[index])
        x1 = float(x_values[index + 1])
        a, b, c, d = [float(value) for value in spline.c[:, index]]

        rows.append(
            {
                "Interval": index + 1,
                "x_start": x0,
                "x_end": x1,
                "a": a,
                "b": b,
                "c": c,
                "d": d,
                "Formula": format_spline_formula(a, b, c, d, x0),
            }
        )

    return rows


def build_sinusoid_formula_rows(A, B, C, D):
    """Build formula rows for sinusoidal Excel export."""
    return [
        {
            "Formula Type": "Sinusoidal best fit",
            "A": float(A),
            "B": float(B),
            "C": float(C),
            "D": float(D),
            "Formula": format_sinusoid_equation(A, B, C, D),
        }
    ]


def autosize_worksheet_columns(worksheet):
    """Adjust Excel column widths to fit exported content."""
    for column_cells in worksheet.columns:
        column_letter = get_column_letter(column_cells[0].column)
        max_length = 0

        for cell in column_cells:
            value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(value))

        worksheet.column_dimensions[column_letter].width = min(max_length + 2, 90)


def export_analysis_to_excel(output_path, metadata_rows, area_rows, formula_rows):
    """Export area results and formulas to an Excel workbook."""
    workbook = Workbook()

    area_sheet = workbook.active
    area_sheet.title = "Area Results"
    area_sheet.append(["Field", "Value"])

    for key, value in metadata_rows:
        area_sheet.append([key, value])

    area_sheet.append([])
    area_sheet.append(["Area Result", "Value"])

    for key, value in area_rows:
        area_sheet.append([key, value])

    formulas_sheet = workbook.create_sheet("Formulas")

    if formula_rows:
        headers = list(formula_rows[0].keys())
        formulas_sheet.append(headers)

        for row in formula_rows:
            formulas_sheet.append([row.get(header, "") for header in headers])
    else:
        formulas_sheet.append(["Formula"])
        formulas_sheet.append(["No formula rows were generated."])

    for worksheet in workbook.worksheets:
        for cell in worksheet[1]:
            cell.font = Font(bold=True)
            cell.alignment = Alignment(wrap_text=True)

        for row in worksheet.iter_rows():
            for cell in row:
                cell.alignment = Alignment(wrap_text=True, vertical="top")

        worksheet.freeze_panes = "A2"
        autosize_worksheet_columns(worksheet)

    workbook.save(output_path)
    return output_path


def save_spline_equations(
    x_values,
    spline,
    output_path,
    signed_area=None,
    absolute_area=None,
):
    """Save the exact piecewise cubic spline equations to a text file."""
    with open(output_path, "w", encoding="utf-8") as file:
        file.write("Exact interpolated cubic spline formula\n")
        file.write("Column A is x. Column B is y.\n\n")

        if signed_area is not None:
            file.write(
                f"Signed area from x = {format_number(x_values[0])} "
                f"to x = {format_number(x_values[-1])}: "
                f"{format_number(signed_area)}\n"
            )

        if absolute_area is not None:
            file.write(
                f"Absolute area from x = {format_number(x_values[0])} "
                f"to x = {format_number(x_values[-1])}: "
                f"{format_number(absolute_area)}\n"
            )

        if signed_area is not None or absolute_area is not None:
            file.write("\n")

        file.write(
            "Each interval uses this form:\n"
            "y = a*(x - x0)^3 + b*(x - x0)^2 + c*(x - x0) + d\n\n"
        )

        for index in range(len(x_values) - 1):
            x0 = x_values[index]
            x1 = x_values[index + 1]
            a, b, c, d = spline.c[:, index]

            file.write(
                f"For {format_number(x0)} <= x <= {format_number(x1)}:\n"
            )
            file.write(f"{format_spline_formula(a, b, c, d, x0)}\n\n")


def print_spline_summary(x_values, output_path, signed_area, absolute_area):
    """Print a readable summary for the exact interpolated formula."""
    print("Exact interpolated formula:")
    print("A cubic spline was created through every data point.")
    print(f"Number of piecewise equations: {len(x_values) - 1}")
    print(f"Formula file saved to: {output_path}")
    print()
    print(f"Area range: x = {x_values[0]:.6f} to x = {x_values[-1]:.6f}")
    print(f"Signed area under curve:   {signed_area:.6f}")
    print(f"Absolute area under curve: {absolute_area:.6f}")
    print()
    print("Important:")
    print("This is exact at the Excel points, but it is a piecewise formula.")
    print("There is one cubic equation between each pair of x values.")


def to_float(value):
    """Convert worksheet values to floats, returning None for headers/blanks."""
    if value is None:
        return None

    if isinstance(value, str):
        value = value.strip()
        if not value:
            return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def load_xy_from_excel(file_path):
    """Load x values from column A and y values from column B."""
    workbook = load_workbook(file_path, read_only=True, data_only=True)
    worksheet = workbook.active
    worksheet_title = worksheet.title

    points = []
    skipped_rows = 0

    for x_raw, y_raw in worksheet.iter_rows(
        min_col=1,
        max_col=2,
        values_only=True,
    ):
        x_value = to_float(x_raw)
        y_value = to_float(y_raw)

        if x_value is None or y_value is None:
            if x_raw is not None or y_raw is not None:
                skipped_rows += 1
            continue

        points.append((x_value, y_value))

    workbook.close()

    if len(points) < 4:
        raise ValueError(
            "The Excel sheet needs at least 4 numeric rows in columns A and B."
        )

    points.sort(key=lambda point: point[0])

    x_values = np.array([point[0] for point in points], dtype=float)
    y_values = np.array([point[1] for point in points], dtype=float)

    return x_values, y_values, worksheet_title, len(points), skipped_rows


def choose_excel_file():
    """Open a file picker so the user can select an Excel workbook."""
    try:
        from tkinter import Tk, filedialog
    except ImportError:
        return None

    root = Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    file_path = filedialog.askopenfilename(
        title="Select Excel file: column A = x, column B = y",
        filetypes=[
            ("Excel workbooks", "*.xlsx *.xlsm"),
            ("All files", "*.*"),
        ],
    )

    root.destroy()
    return file_path or None


def choose_analysis_mode(default_mode="exact"):
    """Ask whether to use sinusoidal best fit or exact interpolation."""
    print("Choose graph formula mode:")
    print("1 = Best-fit sinusoidal equation")
    print("2 = Exact interpolated curve through every point")

    default_choice = "2" if default_mode == "exact" else "1"
    choice = input(f"Enter 1 or 2 [{default_choice}]: ").strip()

    if not choice:
        choice = default_choice

    if choice == "1":
        return "sinusoid"

    if choice == "2":
        return "exact"

    print("Invalid choice. Using exact interpolated curve.")
    return "exact"


def parse_arguments():
    """Parse optional command-line arguments."""
    excel_path = None
    mode = None

    for argument in sys.argv[1:]:
        normalized = argument.lower().strip()

        if normalized in {"--exact", "--interpolate", "--spline"}:
            mode = "exact"
        elif normalized in {"--sinusoid", "--best-fit", "--bestfit"}:
            mode = "sinusoid"
        else:
            excel_path = Path(argument)

    return excel_path, mode


def print_equation(
    A,
    B,
    C,
    D,
    signed_area=None,
    absolute_area=None,
    x_min=None,
    x_max=None,
):
    """Print the fitted sinusoidal equation in readable form."""
    print("Best-fit parameters:")
    print(f"Amplitude A:       {A:.6f}")
    print(f"Frequency B:       {B:.6f}")
    print(f"Phase shift C:     {C:.6f}")
    print(f"Vertical offset D: {D:.6f}")
    print()
    print("Best-fit sinusoidal equation:")
    print(format_sinusoid_equation(A, B, C, D, digits=4))

    if signed_area is not None:
        print()
        print(f"Area range: x = {x_min:.6f} to x = {x_max:.6f}")
        print(f"Signed area under fitted curve: {signed_area:.6f}")
        if absolute_area is not None:
            print(f"Absolute area under fitted curve: {absolute_area:.6f}")


def plot_fit(
    x_values,
    y_values,
    A,
    B,
    C,
    D,
    title="Sinusoidal Curve Fit",
    signed_area=None,
):
    """Plot the original data points and fitted sinusoidal curve."""
    x_fit = np.linspace(np.min(x_values), np.max(x_values), 1000)
    y_fit = sinusoid(x_fit, A, B, C, D)

    c_sign = "+" if C >= 0 else "-"
    d_sign = "+" if D >= 0 else "-"
    equation_text = (
        f"y = {A:.4f} sin({B:.4f}x {c_sign} {abs(C):.4f}) "
        f"{d_sign} {abs(D):.4f}"
    )

    if signed_area is not None:
        equation_text += f"\nSigned area = {signed_area:.4f}"

    plt.scatter(x_values, y_values, label="Original data", color="blue")
    plt.plot(x_fit, y_fit, label="Fitted curve", color="red", linewidth=2)
    plt.fill_between(
        x_fit,
        y_fit,
        0,
        color="red",
        alpha=0.12,
        label="Area under fitted curve",
    )

    plt.xlabel("x")
    plt.ylabel("y")
    plt.title(title)
    plt.text(
        0.02,
        0.98,
        equation_text,
        transform=plt.gca().transAxes,
        verticalalignment="top",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "gray"},
    )
    plt.legend()
    plt.grid(True)
    plt.show()


def plot_exact_spline(
    x_values,
    y_values,
    spline,
    title="Exact Interpolated Curve",
    signed_area=None,
    absolute_area=None,
):
    """Plot original points and the exact interpolated spline curve."""
    x_fit = np.linspace(np.min(x_values), np.max(x_values), 2000)
    y_fit = spline(x_fit)

    label_text = "Exact cubic spline interpolation\nFormula saved as piecewise equations"
    if signed_area is not None:
        label_text += f"\nSigned area = {signed_area:.4f}"
    if absolute_area is not None:
        label_text += f"\nAbsolute area = {absolute_area:.4f}"

    plt.scatter(x_values, y_values, label="Original data", color="blue")
    plt.plot(
        x_fit,
        y_fit,
        label="Exact interpolated curve",
        color="red",
        linewidth=2,
    )
    plt.fill_between(
        x_fit,
        y_fit,
        0,
        color="red",
        alpha=0.12,
        label="Area under curve",
    )

    plt.xlabel("x")
    plt.ylabel("y")
    plt.title(title)
    plt.text(
        0.02,
        0.98,
        label_text,
        transform=plt.gca().transAxes,
        verticalalignment="top",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "gray"},
    )
    plt.legend()
    plt.grid(True)
    plt.show()


def make_sample_data():
    """Create sample data if no Excel file is selected."""
    np.random.seed(42)

    x_data = np.linspace(0, 10, 80)

    true_A = 2.5
    true_B = 1.7
    true_C = 0.6
    true_D = 1.2

    noise = np.random.normal(0, 0.3, size=len(x_data))
    y_data = sinusoid(x_data, true_A, true_B, true_C, true_D) + noise

    return x_data, y_data


def main():
    excel_path, mode = parse_arguments()

    if excel_path is None:
        selected_file = choose_excel_file()
        excel_path = Path(selected_file) if selected_file else None

    if excel_path:
        if not excel_path.exists():
            raise FileNotFoundError(f"Could not find Excel file: {excel_path}")

        x_data, y_data, sheet_name, used_rows, skipped_rows = load_xy_from_excel(
            excel_path
        )

        print(f"Loaded file: {excel_path}")
        print(f"Worksheet: {sheet_name}")
        print(f"Numeric data rows used: {used_rows}")
        print(f"Rows skipped: {skipped_rows}")
        print()

        base_title = excel_path.name
        output_stem = excel_path.with_suffix("")
        source_label = str(excel_path)
    else:
        print("No Excel file selected. Using built-in sample data.")
        print()
        x_data, y_data = make_sample_data()
        sheet_name = "Built-in sample"
        used_rows = len(x_data)
        skipped_rows = 0
        base_title = "Sample Data"
        output_stem = Path("sample_data")
        source_label = "Built-in sample data"

    if mode is None:
        mode = choose_analysis_mode(default_mode="exact")

    if mode == "sinusoid":
        A, B, C, D = fit_sinusoidal(x_data, y_data)
        x_min = float(np.min(x_data))
        x_max = float(np.max(x_data))
        signed_area = calculate_sinusoid_area(A, B, C, D, x_min, x_max)
        absolute_area = calculate_sinusoid_absolute_area(A, B, C, D, x_min, x_max)
        results_path = output_stem.with_name(f"{output_stem.name}_analysis_results.xlsx")

        print_equation(
            A,
            B,
            C,
            D,
            signed_area=signed_area,
            absolute_area=absolute_area,
            x_min=x_min,
            x_max=x_max,
        )

        export_analysis_to_excel(
            results_path,
            metadata_rows=[
                ("Source file", source_label),
                ("Worksheet", sheet_name),
                ("Analysis mode", "Sinusoidal best fit"),
                ("Numeric data rows used", used_rows),
                ("Rows skipped", skipped_rows),
                ("Formula type", "y = A * sin(B*x + C) + D"),
            ],
            area_rows=[
                ("x start", x_min),
                ("x end", x_max),
                ("Signed area under curve", signed_area),
                ("Absolute area under curve", absolute_area),
            ],
            formula_rows=build_sinusoid_formula_rows(A, B, C, D),
        )
        print(f"Excel results saved to: {results_path}")

        plot_fit(
            x_data,
            y_data,
            A,
            B,
            C,
            D,
            title=f"Sinusoidal Best Fit: {base_title}",
            signed_area=signed_area,
        )
    else:
        x_data, y_data, spline = make_exact_spline(x_data, y_data)
        formula_path = output_stem.with_name(f"{output_stem.name}_exact_formula.txt")
        results_path = output_stem.with_name(f"{output_stem.name}_analysis_results.xlsx")
        signed_area, absolute_area = calculate_spline_area(
            spline,
            x_data[0],
            x_data[-1],
        )

        save_spline_equations(
            x_data,
            spline,
            formula_path,
            signed_area=signed_area,
            absolute_area=absolute_area,
        )
        export_analysis_to_excel(
            results_path,
            metadata_rows=[
                ("Source file", source_label),
                ("Worksheet", sheet_name),
                ("Analysis mode", "Exact cubic spline interpolation"),
                ("Numeric data rows used", used_rows),
                ("Rows skipped", skipped_rows),
                ("Unique x values", len(x_data)),
                (
                    "Formula type",
                    "Piecewise cubic spline: y = a*(x-x0)^3 + b*(x-x0)^2 + c*(x-x0) + d",
                ),
            ],
            area_rows=[
                ("x start", float(x_data[0])),
                ("x end", float(x_data[-1])),
                ("Signed area under curve", signed_area),
                ("Absolute area under curve", absolute_area),
            ],
            formula_rows=build_spline_formula_rows(x_data, spline),
        )
        print_spline_summary(x_data, formula_path, signed_area, absolute_area)
        print(f"Excel results saved to: {results_path}")
        plot_exact_spline(
            x_data,
            y_data,
            spline,
            title=f"Exact Interpolated Curve: {base_title}",
            signed_area=signed_area,
            absolute_area=absolute_area,
        )


if __name__ == "__main__":
    main()
