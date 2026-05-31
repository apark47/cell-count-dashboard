from scipy.stats import mannwhitneyu
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
import sys
import os


# =========================================================
# CONSTANTS
# =========================================================

CSV_FILE = "cell-count.csv"
DB_FILE = "cell-count.db"
OUTPUT_FILE = "output.txt"
PLOTS_DIR = "plots"

POPULATIONS = [
    "b_cell",
    "cd8_t_cell",
    "cd4_t_cell",
    "nk_cell",
    "monocyte"
]


# =========================================================
# DATABASE SETUP
# =========================================================

def initialize_database(df):
    """
    Create SQLite database with:
    1. samples table
    2. cell_counts table
    """

    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()

    # -----------------------------------------------------
    # Create samples table
    # -----------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS samples (
        sample TEXT PRIMARY KEY,
        project TEXT,
        subject TEXT,
        condition TEXT,
        age INTEGER,
        sex TEXT,
        treatment TEXT,
        response TEXT,
        sample_type TEXT,
        time_from_treatment_start INTEGER
    )
    """)

    # -----------------------------------------------------
    # Create cell_counts table
    # -----------------------------------------------------

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cell_counts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sample TEXT,
        population TEXT,
        count INTEGER,
        FOREIGN KEY(sample) REFERENCES samples(sample)
    )
    """)

    # -----------------------------------------------------
    # Insert sample metadata
    # -----------------------------------------------------

    sample_columns = [
        "sample",
        "project",
        "subject",
        "condition",
        "age",
        "sex",
        "treatment",
        "response",
        "sample_type",
        "time_from_treatment_start"
    ]

    samples_df = df[sample_columns].drop_duplicates()

    samples_df.to_sql(
        "samples",
        conn,
        if_exists="replace",
        index=False
    )

    # -----------------------------------------------------
    # Convert wide immune columns to long format
    # -----------------------------------------------------

    cell_counts_df = df.melt(
        id_vars=["sample"],
        value_vars=POPULATIONS,
        var_name="population",
        value_name="count"
    )

    cell_counts_df.to_sql(
        "cell_counts",
        conn,
        if_exists="replace",
        index=False
    )

    conn.commit()

    print(f"Created database: {DB_FILE}")

    return conn


# =========================================================
# PART 2: RELATIVE FREQUENCY TABLE
# =========================================================

def find_relative_freqs(conn):
    """
    Generate relative frequency summary table using samples and cell_counts tables.
    """

    query = """
    WITH totals AS (
        SELECT
            sample,
            SUM(count) AS total_count
        FROM cell_counts
        GROUP BY sample
    )

    SELECT
        c.sample,
        t.total_count,
        c.population,
        c.count,
        ROUND(
            100.0 * c.count / t.total_count,
            4
        ) AS percentage
    FROM cell_counts c
    JOIN totals t
        ON c.sample = t.sample
    ORDER BY c.sample, c.population
    """

    summary_df = pd.read_sql_query(query, conn)

    print("\n========== PART 2: RELATIVE FREQUENCY SUMMARY ==========")
    print(summary_df.to_string(index=False))

    return summary_df


# =========================================================
# PART 3: STATISTICAL ANALYSIS
# =========================================================

def statistical_analysis(df):

    print("\n============= PART 3: STATISTICAL ANALYSIS =============")

    # -----------------------------------------------------
    # Filter dataset
    # -----------------------------------------------------

    df_subset = df[
        (df["condition"] == "melanoma") &
        (df["treatment"] == "miraclib") &
        (df["sample_type"] == "PBMC")
    ].copy()

    # -----------------------------------------------------
    # Compute total immune cells
    # -----------------------------------------------------

    df_subset["total_cells"] = df_subset[
        POPULATIONS
    ].sum(axis=1)

    # -----------------------------------------------------
    # Compute relative frequencies
    # -----------------------------------------------------

    for pop in POPULATIONS:

        df_subset[f"{pop}_freq"] = (
            df_subset[pop] / df_subset["total_cells"]
        )

    # -----------------------------------------------------
    # Split responders vs non-responders
    # -----------------------------------------------------

    responders = df_subset[df_subset["response"] == "yes"]
    nonresponders = df_subset[df_subset["response"] == "no"]

    print("\n"
          "***************************\n"
          "    STATISTICAL RESULTS    \n"
          "***************************")

    significant_pops = []

    # -----------------------------------------------------
    # Statistical testing
    # -----------------------------------------------------

    for pop in POPULATIONS:

        responder_freqs = responders[f"{pop}_freq"]

        nonresponder_freqs = nonresponders[f"{pop}_freq"]

        stat, pvalue = mannwhitneyu(
            responder_freqs,
            nonresponder_freqs,
            alternative="two-sided"
        )

        print(f"{pop}\n"
              f"Responder mean freq: {responder_freqs.mean():.4f}\n"
              f"Non-responder mean freq: {nonresponder_freqs.mean():.4f}\n"
              f"P-value: {pvalue:.5f}")

        if pvalue < 0.05:
            print("SIGNIFICANT DIFFERENCE")
            significant_pops.append(pop)

        else:
            print("Not significant")

        # -------------------------------------------------
        # Boxplot visualization
        # -------------------------------------------------

        plt.figure(figsize=(6, 5))

        plt.boxplot(
            [responder_freqs, nonresponder_freqs],
            labels=["Responders", "Non-Responders"]
        )

        plt.ylabel("Relative Frequency")

        plt.title(
            f"{pop} Relative Frequency"
        )

        plt.tight_layout()

        os.makedirs(PLOTS_DIR, exist_ok=True)
        plot_path = os.path.join(PLOTS_DIR, f"{pop}_boxplot.png")
        plt.savefig(plot_path)
        print(f"Saved to {plot_path}\n")
        plt.close()

    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    print("*******************************\n"
          "    SIGNIFICANT POPULATIONS    \n"
          "*******************************")

    if significant_pops:

        for pop in significant_pops:
            print(pop)

    else:
        print("No significant populations found.")


# =========================================================
# PART 4: DATA SUBSET ANALYSIS
# =========================================================

def subset_analysis(df):

    print("\n======================== PART 4 ========================")

    df_subset2 = df[
        (df["condition"] == "melanoma") &
        (df["treatment"] == "miraclib") &
        (df["sample_type"] == "PBMC") &
        (df["time_from_treatment_start"] == 0)
    ].copy()

    # -----------------------------------------------------
    # Samples per project
    # -----------------------------------------------------

    print("Samples per project:")

    project_counts = (
        df_subset2["project"]
        .value_counts()
    )

    for project, count in project_counts.items():

        print(f"{project}: {count}")

    # -----------------------------------------------------
    # Responders / non-responders
    # -----------------------------------------------------

    responders2 = (df_subset2[df_subset2["response"] == "yes"]["subject"].nunique())

    nonresponders2 = (df_subset2[df_subset2["response"] == "no"]["subject"].nunique())

    print("\nSubjects by response:")
    print(f"Responders: {responders2}")
    print(f"Non-responders: {nonresponders2}")

    # -----------------------------------------------------
    # Male / female
    # -----------------------------------------------------

    females = (df_subset2[df_subset2["sex"] == "F"]["subject"].nunique())
    males = (df_subset2[df_subset2["sex"] == "M"]["subject"].nunique())

    print("\nSubjects by sex:")
    print(f"Females: {females}")
    print(f"Males: {males}")


# =========================================================
# MAIN
# =========================================================

def main():

    print("\n========== PART 1: DATA MANAGEMENT =====================")

    # -----------------------------------------------------
    # Read CSV
    # -----------------------------------------------------

    df = pd.read_csv(CSV_FILE)

    print(f"Loaded file: {CSV_FILE}")

    # -----------------------------------------------------
    # Initialize DB
    # -----------------------------------------------------

    conn = initialize_database(df)

    # -----------------------------------------------------
    # PART 2
    # -----------------------------------------------------

    summary_df = find_relative_freqs(conn)

    # Save summary table
    summary_df.to_sql(
        "relative_frequencies",
        conn,
        if_exists="replace",
        index=False
    )

    # -----------------------------------------------------
    # PART 3
    # -----------------------------------------------------

    statistical_analysis(df)

    # -----------------------------------------------------
    # PART 4
    # -----------------------------------------------------

    subset_analysis(df)

    conn.close()

    print("\nAnalysis complete.")
    return df


if __name__ == "__main__":
    original_stdout = sys.stdout 
    with open(OUTPUT_FILE, 'w') as f:
        sys.stdout = f
        df = main()
    sys.stdout = original_stdout
    print("Output printed to", OUTPUT_FILE)

    subset = df[
        (df["condition"] == "melanoma") &
        (df["sex"] == "M") &
        (df["response"] == "yes") &
        (df["time_from_treatment_start"] == 0)
    ]

    avg_b_cells = subset["b_cell"].mean()
    print("Avg no. B cells for Melanoma male responders at time=0:", f"{avg_b_cells:.2f}")