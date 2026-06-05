import pandas as pd

df = pd.read_csv("01-paper-selection/paper_selection.csv")
df_in = df.loc[df["In-Scope"] == "yes"]
print(f"Total papers: {len(df)}, In-Scope papers: {len(df_in)}, Sampled papers: {len(df_in.loc[df_in['Coder 1'].notna()])}")
sampled_orig = df_in.loc[df_in["Coder 1"].notna()]


def detailed_sampling_stats(sampled, df_filt):
    # Pivot sampled table
    pivot = (
        sampled
        .groupby(["conference_year", "conference_name"], observed=False)["id"]
        .count()
        .unstack(fill_value=0)
    )
    
    # Add Sample totals (row + column)
    pivot.loc["Sample"] = pivot.sum(axis=0)
    pivot["Sample"] = pivot.sum(axis=1)

    # Pivot real totals from df_filt
    real_pivot = (
        df_filt
        .groupby(["conference_year", "conference_name"], observed=False)["id"]
        .count()
        .unstack(fill_value=0)
    )
    
    # Align real_pivot with sampled pivot columns
    real_pivot = real_pivot.reindex(
        index=pivot.index.drop("Sample"),
        columns=pivot.columns.drop("Sample"),
        fill_value=0
    )
    
    
    # Add Total row + column as integers
    pivot.loc["Total"] = real_pivot.sum(axis=0)
    pivot["Total"] = real_pivot.sum(axis=1)
    pivot.loc["Total", "Total"] = len(df_filt)
    
    # Compute Pct_sample row/column: Sample / Total
    pct_sample = pivot.loc["Sample"] / pivot.loc["Total"]
    pivot.loc["Pct_sample"] = pct_sample
    pivot["Pct_sample"] = (pivot["Sample"] / pivot["Total"])
    pivot.loc["Pct_sample", "Pct_sample"] = len(sampled) / len(df_filt)
    
    print(pivot)


# Sampling year x conferences x 2 papers (2021-2024)
SEED = 42
N_PER_GROUP = 2


sampled = (
    df_in.loc[df_in["conference_year"] <= 2024]
    .groupby(["conference_name", "conference_year"], group_keys=False)[["id", "conference_name", "conference_year"]]
    .apply(lambda g: g.sample(
        n=min(len(g), N_PER_GROUP),
        random_state=SEED
    ))
)

print("Seed", SEED)
print(f"Total selected papers (2021-2024): {len(sampled)}, sampled 2 for each conference X year combination")
detailed_sampling_stats(sampled, df_in.loc[df_in["conference_year"] <= 2024])
# Framing errors/resample
# Two papers were excluded as they do not contain an "active web measurement" according to our criteria
# DISTINCT CCS 2022 and Accountable Javascript Code Delivery NDSS 2023
# Resample two paper
ccs_resample = df_in.loc[
    (df_in["conference_name"] == "ccs")
    & (df_in["conference_year"] == 2022)
    & (df_in["In-Scope"] == "yes")
    & (df_in["id"].isin(sampled["id"].tolist()) == False)
].sample(1, random_state=SEED)

ndss_resample = df_in.loc[
    (df_in["conference_name"] == "ndss")
    & (df_in["conference_year"] == 2023)
    & (df_in["In-Scope"] == "yes")
    & (df_in["id"].isin(sampled["id"].tolist()) == False)
].sample(1, random_state=SEED)

sampled = pd.concat(
    [
        sampled,
        ccs_resample[sampled.columns],
        ndss_resample[sampled.columns],
    ],
    ignore_index=False,
)
print("Same papers sampled (0 difference):",set(sampled_orig.loc[sampled_orig["conference_year"] <= 2024]["id"].tolist()) - set(sampled["id"].tolist()))

# 2025 sampling

SEED = 44
N_PER_GROUP = 2

sampled_2025 = (
    df_in.loc[df_in["conference_year"] == 2025]
    .groupby(["conference_name", "conference_year"], group_keys=False)[["id", "conference_name", "conference_year"]]
    .apply(lambda g: g.sample(
        n=min(len(g), N_PER_GROUP),
        random_state=SEED
    ))
)

print("Seed", SEED)
print(f"Total selected papers (2025-2025): {len(sampled_2025)}, sampled 2 for each conference X year combination")
detailed_sampling_stats(sampled_2025, df_in.loc[df_in["conference_year"] == 2025])
print("Same papers sampled (0 difference):",set(sampled_orig.loc[sampled_orig["conference_year"] == 2025]["id"].tolist()) - set(sampled_2025["id"].tolist()))