import marimo

__generated_with = "0.23.9"
app = marimo.App()


@app.cell
def _():
    # Imports
    import marimo as mo
    import pandas as pd
    import json
    import re
    import os
    from collections import Counter
    import numpy as np
    import matplotlib.pyplot as plt
    import ast
    from pathlib import Path

    return Counter, ast, mo, pd


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Load Data
    """)
    return


@app.cell
def _(Counter, ast, pd):
    # Final data
    df = pd.read_csv("03-analysis/anonymized_results.csv")

    # Helper code
    def normalize_entry(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                parsed = ast.literal_eval(value)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
            return [value]
        if pd.isna(value):
            return []
        return [value]


    def compute_counts(series):
        counter = Counter()
        for raw_value in series:
            for entry in normalize_entry(raw_value):
                if pd.isna(entry):
                    continue
                text = str(entry).strip()
                if text:
                    counter[text] += 1
        return counter

    # List of all factors and how often they were mentioned
    # existing observed counts
    counts = pd.concat([
        pd.DataFrame.from_dict(
            compute_counts(df[f"{c}"]),
            orient="index",
            columns=["count"]
        ).reset_index(names="factor").assign(category=na)
        for c, na in [
            ("79-q-p3-factors-4-dataset", "dataset"),
            ("80-q-p3-factors-5-implementation", "implementation"),
            ("81-q-p3-factors-6-env", "env"),
            ("82-q-p3-factors-7-process", "process"),
            ("83-q-p3-factors-8-reporting", "reporting"),
            ("84-q-p3-factors-9-other", "other"),
        ]
    ])

    counts = pd.concat([
        counts,
        pd.concat([
            pd.DataFrame([{
                "category": cat,
                "factor": "ANY",
                "count": (
                    df[f"{prefix}"]
                    .fillna("[]")
                    .apply(ast.literal_eval)
                    .apply(lambda x: len(x) > 0)
                    .sum()
                )
            }])
            for prefix, cat in [
                ("79-q-p3-factors-4-dataset", "dataset"),
                ("80-q-p3-factors-5-implementation", "implementation"),
                ("81-q-p3-factors-6-env", "env"),
                ("82-q-p3-factors-7-process", "process"),
                ("83-q-p3-factors-8-reporting", "reporting"),
                ("84-q-p3-factors-9-other", "other"),
            ]
        ])
    ], ignore_index=True)


    # merge and fill missing counts with 0
    all_factors = counts.assign(count=lambda x: x["count"].astype(int)).sort_values(["category", "count"], ascending=[True, False])

    tested_cols = [
        ("factortested_dataset", "dataset"),
        ("factortested_implementation", "implementation"),
        ("factortested_env", "env"),
        ("factortested_process", "process"),
        ("factortested_reporting", "reporting"),
        ("factortested_other", "other"),
    ]

    tested_factors = pd.concat([
        df[c]
          .fillna("[]")
          .apply(ast.literal_eval)
          .explode()
          .dropna()
          .value_counts()
          .rename_axis("factor")
          .reset_index(name="count")
          .assign(category=cat)
        for c, cat in tested_cols
    ], ignore_index=True)

    any_rows = pd.concat([
        pd.DataFrame([{
            "category": cat,
            "factor": "ANY",
            "count": df[col]
                .fillna("[]")
                .apply(ast.literal_eval)
                .apply(len)
                .gt(0)
                .sum()
        }])
        for col, cat in tested_cols
    ])

    tested_factors = pd.concat([tested_factors, any_rows], ignore_index=True)

    # Compare tested and mentioned factors, what was mentioned a lot but rarely tested and the other way round
    comparison = (
        all_factors[["category", "factor", "count"]]
        .rename(columns={"count": "mentioned"})
        .set_index(["category", "factor"])
        .join(
            tested_factors[["category", "factor", "count"]]
            .rename(columns={"count": "tested"})
            .set_index(["category", "factor"])
        )
        .fillna({"tested": 0})
        .astype({"mentioned": int, "tested": int})
    )
    comparison = comparison.assign(

        # raw difference
        diff=lambda x: x["mentioned"] - x["tested"],

        # tested relative to mentioned
        tested_per_mentioned=lambda x: (
            x["tested"] / x["mentioned"].replace(0, pd.NA)
        ),

    ).reset_index()
    return all_factors, comparison, compute_counts, df, tested_factors


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Paper Analysis
    """)
    return


@app.cell(hide_code=True)
def _(df, mo):
    mo.md(rf"""
    ## Sample Overview
    - 70 papers: `2*7*5`
    - How import and purpose of crawl?
        - For 13 papers the crawl is the only core contribution, for 48 it is a major contribution, and for 9 it is a minor contribution
            - Outlier: IMC 0 papers with minor and highest percentage with only core contribution (50%)
        - Purpose: For roughly half the papers 'Measure Prevalence' is the main purpose, other purposes also common: {df["15-q-p1-major-8-crawlpurpose"].value_counts().to_dict()}
    """)
    return


@app.cell
def _(df, mo, pd):
    mo.output.append(df["14-q-p1-major-7-crawlpercentage"].value_counts())
    # Requires non-anonymized data
    mo.output.append(pd.pivot_table(
        df,
        index=["14-q-p1-major-7-crawlpercentage"],
        columns=["4-q-p1-meta-1-metadata.conference"],
        aggfunc="size",
        fill_value=0,
    ))
    return


@app.cell
def _(df, mo):
    # Mostly Measure Prevalence
    mo.output.append(mo.md("For roughly half the papers 'Measure Prevalence' is the main purpose, other purposes also common"))

    mo.output.append(df["15-q-p1-major-8-crawlpurpose"].value_counts())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Factor Overview
    """)
    return


@app.cell
def _(comparison, pd):
    # Overview table for the paper
    # Id/memonic for each factor, description, count for category?, numbers, ...
    # Rename some of them (later)!
    # Factors vs subfactors?: use only factors, the only factors with more than one subfactor are "Website Selection (C1)" and "Other browser settings (C13)"
    # ...
    order = [
        "dataset",
        "implementation",
        "env",
        "process",
        "reporting",
        "other",
    ]

    cat_short = {
        "dataset": "D",
        "implementation": "B",
        "env": "E",
        "process": "P",
        "reporting": "A",
        "other": "N",   
    }

    labels = {
        "dataset": "Dataset (D)",
        "implementation": "Crawler Basis (B)",
        "env": "Environment (E)",
        "process": "Measurement Process (P)",
        "reporting": "Analysis \\& Reporting (A)",
        "other": "Nature of the Web (N)",
    }

    factor_map = [
        # Dataset
        {
            "factor": "Website selection (C1)",
            "factor_name": "Website selection",
            "category": "dataset",
            "short_code": "Site",
            "description": "Which sites are chosen? Which list are they coming from?",
            "order": 0
        },
        {
            "factor": "Webpage selection/crawling strategy (C2)",
            "factor_name": "Webpage selection",
            "category": "dataset",
            "short_code": "Page",
            "description": "Which pages are chosen within each site (e.g., internal vs landing-pages only)?",
            "order": 1
        },
        {
            "factor": "Dataset issues",
            "factor_name": "Other dataset factors",
            "category": "dataset",
            "short_code": "Other",
            "description": "Other issues with input dataset such as interacting with sites during the measurement (notification) or errornous data (e.g., HAR file issues).",
            "order": 2
        },

        # Implementation
        {
            "factor": "Browser",
            "factor_name": "Browser",
            "category": "implementation",
            "short_code": "Brow",
            "description": "Browser used for the crawl.",
            "order": 6
        },
        {
            "factor": "Instrumentation technology",
            "factor_name": "Instrumentation",
            "category": "implementation",
            "short_code": "Instr",
            "description": "Measurement instrumentation technologies, e.g., custom JS code or Selenium that can be detected or does not support modern ECMAScript.",
            "order": 5
        },
        {
            "factor": "Other browser settings (C13)",
            "factor_name": "Settings",
            "category": "implementation",
            "short_code": "Set",
            "description": "Additional configuration of the browser or tools.",
            "order": 10
        },
        {
            "factor": "Type of crawler",
            "factor_name": "Type of crawler",
            "category": "implementation",
            "short_code": "Type",
            "description": "Whether the crawler is browser-based or non-browser based.",
            "order": 4
        },
        {
            "factor": "User-Agent Sniffing/Spoofing",
            "factor_name": "User-Agent",
            "category": "implementation",
            "short_code": "UA",
            "description": "Spoofed or detected user-agent strings.",
            "order": 8
        },
        {
            "factor": "Browser version (C13)",
            "factor_name": "Browser version",
            "category": "implementation",
            "short_code": "Ver",
            "description": "Specific browser version used in the crawl.",
            "order": 7
        },
        {
            "factor": "Headless vs Headfull (C13)",
            "factor_name": "Headful vs headless",
            "category": "implementation",
            "short_code": "Head",
            "description": "Whether the browser ran with or without a visible UI.",
            "order": 9
        },

        # Environment
        {
            "factor": "Geolocation",
            "factor_name": "Geolocation",
            "category": "env",
            "short_code": "Geo",
            "description": "Network location used for the crawl.",
            "order": 11
        },
        {
            "factor": "IP",
            "factor_name": "IP type",
            "category": "env",
            "short_code": "IP",
            "description": "IP address or network origin type (residential, cloud, university) and reputation.",
            "order": 12
        },
        {
            "factor": "Crawling Platform",
            "factor_name": "Crawling platform",
            "category": "env",
            "short_code": "Platform",
            "description": "Hosting environment or machine (Operating System) on which the crawl ran.",
            "order": 13
        },

        # Process
        {
            "factor": "Page interaction (C10)",
            "factor_name": "Page interaction",
            "category": "process",
            "short_code": "Interact",
            "description": "Whether and how the crawler interacts with pages.",
            "order": 16
        },
        {
            "factor": "Autenthication",
            "factor_name": "Authentication",
            "category": "process",
            "short_code": "Auth",
            "description": "Authentication or login steps performed during crawling.",
            "order": 17
        },
        {
            "factor": "Fresh profile vs accumulating state (C11)",
            "factor_name": "Stateful vs stateless",
            "category": "process",
            "short_code": "State",
            "description": "Whether each site/page crawl starts clean or reuses accumulated state.",
            "order": 14
        },
        {
            "factor": "Other non-trival state creation",
            "factor_name": "Cookie interaction",
            "category": "process",
            "short_code": "Cookie",
            "description": "Whether the crawler interacted with cookie banners before or during the crawl.",
            "order":18 
        },
        {
            "factor": "Timeouts and how long to stay on a webpage",
            "factor_name": "Timeouts",
            "category": "process",
            "short_code": "Time",
            "description": "Timeouts and dwell time used when loading and visiting pages.",
            "order": 15
        },

        # Analysis
        {
            "factor": "Detection logic/classification/heuristics",
            "factor_name": "Processing code",
            "category": "reporting",
            "short_code": "Detect",
            "description": "Rules, heuristics, or classifiers used to process interpret collected data.",
            "order": 19
        },
        {
            "factor": "Removal of data (e.g., outlier)",
            "factor_name": "Data cleaning",
            "category": "reporting",
            "short_code": "Clean",
            "description": "Filtering, exclusion, or outlier removal during analysis.",
            "order": 20
        },
        {
            "factor": "Manual analysis",
            "factor_name": "Manual analysis",
            "category": "reporting",
            "short_code": "Manual",
            "description": "Human inspection or manual labeling/interpretation of results.",
            "order": 21
        },

        # Nature of Web
        {
            "factor": "Bot detection",
            "factor_name": "Bot detection",
            "category": "other",
            "short_code": "Bot",
            "description": "Detection or blocking of automated crawlers.",
            "order": 22
        },
        {
            "factor": "Time of the crawl",
            "factor_name": "Time",
            "category": "other",
            "short_code": "Time",
            "description": "When the measurement was performed.",
            "order": 23
        },
        {
            "factor": "General Web Randomness",
            "factor_name": "Web randomness",
            "category": "other",
            "short_code": "Rand",
            "description": "Uncontrolled variability in web behavior across runs.",
            "order": 24
        },
    ]
    factor_map = pd.DataFrame(factor_map)
    comparison_table = comparison.merge(
        factor_map,
        on=["category", "factor"],
        how="left"
    )

    blocks = []

    for cat in order:
        sub = comparison_table.loc[
            (comparison_table["category"] == cat)
            & ((comparison_table["mentioned"] > 0) | (comparison_table["tested"] > 0))
        ].copy()
        # No sort
        #sub = sub.sort_values(["order", "factor"])

        if sub.empty:
            continue

        total_mentioned = sub.loc[sub["factor"] == "ANY", "mentioned"].sum()
        total_tested = sub.loc[sub["factor"] == "ANY", "tested"].sum()

        block_rows = [{
            "category": f"\\multicolumn{{2}}{{@{{}}c@{{}}}}{{\\bfseries {labels[cat]}}}",
            "factor": "",
            "description": "",
            "mentioned": f"{{\\bfseries {int(total_mentioned)}}}",
            "tested": f"{{\\bfseries {int(total_tested)}}}",
        }]

        for _, r in sub[sub["factor"] != "ANY"].iterrows():
            block_rows.append({
                #"category": f"\\hspace*{{1.5em}}-{r['short_code']}",
                "category": f"{cat_short[r['category']]}-{r['short_code']}",
                "factor": r["factor_name"],
                "description": r["description"],
                "mentioned": f"{int(r['mentioned'])}",
                "tested": f"{int(r['tested'])}",
            })

        blocks.append(pd.DataFrame(block_rows))

    if not blocks:
        latex = ""
    else:
        column_format = "l l p{9cm} r r"

        first_block_lines = blocks[0].to_latex(
            index=False,
            escape=False,
            column_format=column_format,
            header=["ID", "Factor", "Description", "Mentioned", "Tested"]
        ).splitlines()
        first_midrule = next(i for i, line in enumerate(first_block_lines) if line.strip() == r"\midrule")
        first_bottomrule = next(i for i, line in enumerate(first_block_lines) if line.strip() == r"\bottomrule")

        latex_lines = first_block_lines[:first_midrule + 1]
        latex_lines.extend(first_block_lines[first_midrule + 1:first_bottomrule])

        for block in blocks[1:]:
            block_lines = block.to_latex(
                index=False,
                escape=False,
                column_format=column_format,
                header=False,
            ).splitlines()
            block_bottomrule = next(i for i, line in enumerate(block_lines) if line.strip() == r"\bottomrule")
            #latex_lines.append(r"\addlinespace")
            latex_lines.extend(block_lines[2:block_bottomrule])

        latex_lines.append(r"\bottomrule")
        latex_lines.append(r"\end{tabular}")
        latex = "\n".join(latex_lines)
    for cat in order:
        label = labels[cat]

        old = (
            rf"\multicolumn{{2}}{{@{{}}c@{{}}}}{{\bfseries {label}}} "
            rf"&  &  & {{\bfseries"
        )

        new = (
            rf"\multicolumn{{2}}{{@{{}}c@{{}}}}{{\bfseries {label}}} "
            rf"& & {{\bfseries"
        )

        latex = latex.replace(old, new)

    print(latex)
    with open("03-analysis/tested_mentioned_overview.tex", "w") as file:
        file.write(latex)
    return


@app.cell
def _(compute_counts, df, mo):
    with mo.redirect_stdout():
        factors = df["76-q-p3-factors-1-factors"].value_counts().to_dict()
        mo.output.append(factors)
        print(f"Most papers ({factors[True]}) mention that results could depend on some measurement (or analysis) setup/process. However, note that we were very generous here and that some papers only very indirectly mention it. Also often a single or few factors are mentioned.")
        mo.output.append(df["77-q-p3-factors-2-factorsloc"].value_counts())
        factors_loc_count = dict(compute_counts(df["77-q-p3-factors-2-factorsloc"]))
        print(f"Roughly the same number of papers mention this in the methods section or the limitations section (many in both), fewer paper mention it in other locations and usually only in addition to the two main locations:")
        mo.output.append(factors_loc_count)
    return


@app.cell
def _(all_factors, df, mo):
    mo.output.append(df["factor_mentioned_all"].explode().nunique())
    mo.output.append(df["factor_mentioned_all"].str.len().agg(["sum", "mean", "median", "max"]))
    mo.output.append(all_factors.loc[all_factors["factor"] != "ANY"].groupby("category")["count"].agg(["sum", "max", "min", "count", lambda s: (s!=0).sum()]))
    return


@app.cell
def _(ast, df, mo):
    with mo.redirect_stdout():
        factorscat = (
            df["78-q-p3-factors-3-factorscat"]
              .fillna("[]")
              .apply(ast.literal_eval)
              .explode()
              .str.get_dummies()
              .groupby(level=0)
              .sum()
        )
        out = df[[
            "4-q-p1-meta-1-metadata.conference",
            "4-q-p1-meta-1-metadata.year"
        ]].join(factorscat)
        out["Categories Mentioned"] = out.iloc[:, 2:].sum(axis=1)

        def report_cats(df):
            mo.output.append(df[["Categories Mentioned", "Analysis & Reporting", "Crawler Implementation", "Crawling Environment", "Crawling Setup", "Dataset", "Other/Ungrouped"]].sum())
            mo.output.append(df["Categories Mentioned"].agg(["sum", "min", "mean", "median", "max"]))

        print("Overall reported categories:")
        print("""
    Dataset is most often reported (39 papers), Crawling Environment the least (14 papers)
    The papers report between 0 and all 6 categories with the median paper reporting 2 categories
    The number of mentioned categories are between 13 (SP), 14 (CCS), 18 (WWW), 20 (USS), , 26 (NDSS), 27 (IMC) and 42 (PETS) (Note: maximum would be 60 if all 10 selected papers of a conference report all 6 categories).
    No clear trend across the years is visible.
    """)
        report_cats(out)
        print("Grouped by conferences: PETS clear outlier (more factors mentioned!), IMC and NDSS also above average")
        report_cats(out.groupby("4-q-p1-meta-1-metadata.conference"))
        print("Grouped by year: no clear trend visible")
        report_cats(out.groupby("4-q-p1-meta-1-metadata.year"))
    return out, report_cats


@app.cell
def _(compute_counts, df, mo):
    # Tested factors
    # 85-q-p3-factortesting-1-testing
    # 86-q-p3-factortesting-2-which
    # 86-q-p3-factortesting-2-which-Comment
    # 87-q-p3-factortesting-3-core
    # 87-q-p3-factortesting-3-core
    with mo.redirect_stdout():
        mo.output.append(df["85-q-p3-factortesting-1-testing"].value_counts())
        mo.output.append(df["87-q-p3-factortesting-3-core"].value_counts())

        mo.output.append(dict(compute_counts(df["factortested_categories"])))
        mo.output.append(dict(compute_counts(df["factortested_all_factors"])))
        mo.output.append(dict(compute_counts(df["86-q-p3-factortesting-2-which"])))
    return


@app.cell
def _(ast, df, mo):
    mo.output.append(df["factortested_all_factors"].apply(ast.literal_eval).explode().nunique())
    mo.output.append(df["factortested_all_factors"].apply(ast.literal_eval).str.len().agg(["sum", "mean", "median", "max"]))
    return


@app.cell
def _(ast, df, mo, tested_factors):
    def run_analysis_factortested_categories():
        with mo.redirect_stdout():
            factorstestedcat = (
                df["factortested_categories"]
                  .fillna("[]")
                  .apply(ast.literal_eval)
                  .explode()
                  .str.get_dummies()
                  .groupby(level=0)
                  .sum()
            )
            out = df[[
                "4-q-p1-meta-1-metadata.conference",
                "4-q-p1-meta-1-metadata.year"
            ]].join(factorstestedcat)
            out["Categories Mentioned"] = out.iloc[:, 2:].sum(axis=1)

            def report_cats(df):
                tested_overview = df[["Categories Mentioned", "dataset", "env", "implementation", "other", "process"]].sum()
                mo.output.append(tested_overview)
                mo.output.append(df["Categories Mentioned"].agg(["sum", "min", "mean", "median", "max"]))
                return tested_overview

            print("Overall tested categories:")
            print("""
        Other is most often tested (18 papers), Crawling Environment the least (6 papers) (analysis 0)
        The papers test between 0 and all 4 categories with the median paper testing 1 categories
        The number of tested categories are between 3 (SP), and 23 (PETS) (Note: maximum would be 60 if all 10 selected papers of a conference report all 6 categories).
        No clear trend across the years is visible.
        """)
            tested_overview = report_cats(out)
            mo.output.append(tested_factors[["category", "factor", "count"]])
            print("Grouped by conferences: PETS clear outlier (more factors tested!),")
            report_cats(out.groupby("4-q-p1-meta-1-metadata.conference"))
            print("Grouped by year: no clear trend visible")
            report_cats(out.groupby("4-q-p1-meta-1-metadata.year"))
            return tested_overview

    tested_overview = run_analysis_factortested_categories()
    return (tested_overview,)


@app.cell
def _(ast, df):
    print("Only 5 papers mention factors from all 6 categories, most 1, followed by 2")
    df["78-q-p3-factors-3-factorscat"].fillna('[]').apply(ast.literal_eval).apply(len).value_counts()
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Dataset
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned dataset factors + manual insights
    report_cats(out)
    mo.output.append(df["79-q-p3-factors-4-dataset"].value_counts())
    mo.output.append(compute_counts(df["79-q-p3-factors-4-dataset"]))
    return


@app.cell
def _(compute_counts, df, mo, tested_overview):
    # Tested dataset factors + manual insights
    mo.output.append(tested_overview)
    mo.output.append(df["factortested_dataset"].value_counts())
    mo.output.append(compute_counts(df["factortested_dataset"]))

    mo.output.append(df["factortested_dataset_org"].value_counts())
    mo.output.append(compute_counts(df["factortested_dataset_org"]))
    return


@app.cell
def _(compute_counts, df, mo):
    # Datasetsource 
    with mo.redirect_stdout():
        mo.output.append(df["12-q-p1-major-5-datasetsource"].value_counts())
        print(compute_counts(df["12-q-p1-major-5-datasetsource"]))
        print("Used datasets are: HTTPArchive (x3), Common Crawl (x4), Internet Archive (x4), datasets from other papers (x6), and Netograph (x1)")
        print(compute_counts(df["13-q-p1-major-6-datasetused"]))
        mo.output.append(df["13-q-p1-major-6-datasetused"].value_counts())
    return


@app.cell
def _(ast, df, mo):
    with mo.redirect_stdout():
        print("Most common is Tranco and Alexa. Clear trend that Alexa got replaced by Tranco over the years. Many other options possible but more specific and not as general.")
        mo.output.append(df["17-q-p2-dataset-website-1-list"].apply(ast.literal_eval).explode().value_counts())
        tmp = (
            df[[
                "4-q-p1-meta-1-metadata.conference",
                "4-q-p1-meta-1-metadata.year",
                "17-q-p2-dataset-website-1-list"
            ]]
            .assign(
                website_list=lambda x: x["17-q-p2-dataset-website-1-list"]
                    .fillna("[]")
                    .apply(ast.literal_eval)
            )
            .explode("website_list")
        ).reset_index()
    return


@app.cell
def _(df, mo):
    with mo.redirect_stdout():
        mo.output.append(df["17-q-p2-dataset-website-1-list-Comment"].dropna().head())
        print("10K most common, then 100k, then 1M, many other from as small as 50 also exist, some are -1 as it is unclear (stream of pages or similar)")
        mo.output.append(df["18-q-p2-dataset-website-2-subsetsize"].value_counts())
        mo.output.append(df["19-q-p2-dataset-website-2-details"].head())
        mo.output.append(df["20-q-p2-dataset-website-3-subsetsampling"].value_counts())
    return


@app.cell
def _(compute_counts, df, mo):
    with mo.redirect_stdout():
        mo.output.append(df["23-q-p2-dataset-webpage-1-starting"].value_counts())
        mo.output.append(df["23-q-p2-dataset-webpage-1-starting-Comment"].dropna().head())
        mo.output.append(df["24-q-p2-dataset-webpage-2-internal"].value_counts())
        mo.output.append(dict(compute_counts(df["25-q-p2-dataset-webpage-3-internalselection"])))
        mo.output.append(df["25-q-p2-dataset-webpage-3-internalselection-Comment"].dropna().head())
        mo.output.append(df["26-27-q-p2-dataset-webpage-4-internalsize-details"].value_counts())
        mo.output.append(df["26-q-p2-dataset-webpage-4-internalsize"].value_counts())
        mo.output.append(df["28-q-p2-dataset-webpage-5-internallock"].value_counts())
        mo.output.append(df["28-q-p2-dataset-webpage-5-internallock-Comment"].dropna())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Implementation
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned implementation factors + manual insights
    report_cats(out)
    mo.output.append(df["80-q-p3-factors-5-implementation"].value_counts())
    mo.output.append(dict(compute_counts(df["80-q-p3-factors-5-implementation"])))
    return


@app.cell
def _(compute_counts, df, mo, tested_overview):
    # Tested implementation factors + manual insights
    mo.output.append(tested_overview)
    mo.output.append(df["factortested_implementation"].value_counts())
    mo.output.append(dict(compute_counts(df["factortested_implementation"])))

    mo.output.append(df["factortested_implementation_org"].value_counts())
    mo.output.append(dict(compute_counts(df["factortested_implementation_org"])))
    return


@app.cell
def _(df, mo):
    mo.output.append(df["31-q-p2-setup-implementation-2-browserbased"].value_counts())
    mo.output.append(df["42-q-p2-setup-implementation-12-crawlertype"].value_counts())
    mo.output.append(df["42-q-p2-setup-implementation-12-crawlertype-Comment"].dropna().head())
    mo.output.append(df["30-q-p2-setup-implementation-1-name"].value_counts())
    return


@app.cell
def _(compute_counts, df, mo):
    mo.output.append(dict(compute_counts(df['32-q-p2-setup-implementation-3-automation'])))
    mo.output.append(dict(compute_counts(df['36-q-p2-setup-implementation-6-browserinstrumentation'])))

    mo.output.append(df['36-q-p2-setup-implementation-6-browserinstrumentation-Comment'].dropna().head())
    return


@app.cell
def _(df):
    df['34-q-p2-setup-implementation-5-browserused'].value_counts()
    return


@app.cell
def _(compute_counts, df, mo):
    mo.output.append(dict(compute_counts(df['34-q-p2-setup-implementation-5-browserused'])))
    mo.output.append(df['35-q-p2-setup-implementation-6-browserversion'].value_counts())
    mo.output.append(df['35-q-p2-setup-implementation-6-browserversion-Comment'].dropna().head())
    return


@app.cell
def _(df, mo):
    mo.output.append(df['38-q-p2-setup-implementation-8-headless'].value_counts())
    mo.output.append(df['39-q-p2-setup-implementation-9-dimensions'].value_counts())
    return


@app.cell
def _(df, mo):
    mo.output.append(df['44-q-p2-setup-implementation-14-headercustom'].value_counts())
    mo.output.append(df[['31-q-p2-setup-implementation-2-browserbased', '44-q-p2-setup-implementation-14-headercustom']].value_counts())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Environment
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned env factors + manual insights
    report_cats(out)
    mo.output.append(df["81-q-p3-factors-6-env"].value_counts())
    mo.output.append(compute_counts(df["81-q-p3-factors-6-env"]))
    return


@app.cell
def _(compute_counts, df, mo, tested_overview):
    # Tested env factors + manual insights
    mo.output.append(tested_overview)
    mo.output.append(df["factortested_env"].value_counts())
    mo.output.append(compute_counts(df["factortested_env"]))

    mo.output.append(df["factortested_env_org"].value_counts())
    mo.output.append(compute_counts(df["factortested_env_org"]))
    return


@app.cell
def _(df, mo):
    mo.output.append(df["47-q-p2-setup-env-1-platform"].value_counts())
    mo.output.append(df["47-q-p2-setup-env-1-platform-Comment"].dropna())
    return


@app.cell
def _(df, mo):
    mo.output.append(df["48-q-p2-setup-env-2-ip"].value_counts())
    mo.output.append(df["48-q-p2-setup-env-2-ip-Comment"].dropna().head())
    return


@app.cell
def _(df, mo):
    mo.output.append(df["49-q-p2-setup-env-3-iprot"].value_counts())
    mo.output.append(df["49-q-p2-setup-env-3-iprot-Comment"].dropna().head())
    return


@app.cell
def _(compute_counts, df, mo):
    mo.output.append(dict(compute_counts(df["50-q-p2-setup-env-4-geo"])))
    mo.output.append(df["50-q-p2-setup-env-4-geo-Comment"].dropna().head())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Process
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned process factors + manual insights
    report_cats(out)
    mo.output.append(df["82-q-p3-factors-7-process"].value_counts())
    mo.output.append(dict(compute_counts(df["82-q-p3-factors-7-process"])))
    return


@app.cell
def _(compute_counts, df, mo, tested_overview):
    # Tested process factors + manual insights
    mo.output.append(tested_overview)
    mo.output.append(df["factortested_process"].value_counts())
    mo.output.append(dict(compute_counts(df["factortested_process"])))

    mo.output.append(df["factortested_process_org"].value_counts())
    mo.output.append(dict(compute_counts(df["factortested_process_org"])))
    return


@app.cell
def _(df, mo):
    mo.output.append(df["52-q-p2-setup-1-state"].value_counts())
    mo.output.append(df["52-q-p2-setup-1-state-Comment"].dropna().head())
    return


@app.cell
def _(df, mo):
    mo.output.append(df["62-q-p2-process-5-pageinteraction"].value_counts())
    mo.output.append(df["62-q-p2-process-5-pageinteraction-Comment"].dropna().head())
    mo.output.append(df["63-q-p2-process-6-pageinteractiondetails"].value_counts())
    mo.output.append(df["63-q-p2-process-6-pageinteractiondetails-Comment"].dropna().head())
    return


@app.cell
def _(df, mo):
    mo.output.append(df["58-q-p2-process-3-pageload"].value_counts())
    mo.output.append(df["58-q-p2-process-3-pageload-Comment"].dropna())

    mo.output.append(df["60-q-p2-process-4-pagestay"].value_counts())
    mo.output.append(df["60-61-q-p2-process-4-pagestay-seconds"].value_counts())
    mo.output.append(df["60-q-p2-process-4-pagestay-Comment"].dropna())

    # Combined always has a value in pageload, so we can say that 50 did not specify anything
    mo.output.append(df.loc[df["60-q-p2-process-4-pagestay"].str.contains("only")][["60-q-p2-process-4-pagestay", "58-q-p2-process-3-pageload"]])
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Analysis & Reporting
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned analysis factors + manual insights
    report_cats(out)
    mo.output.append(df["83-q-p3-factors-8-reporting"].value_counts())
    mo.output.append(dict(compute_counts(df["83-q-p3-factors-8-reporting"])))
    return


@app.cell
def _():
    # Tested analysis factors + manual insights
    # None tested!
    return


@app.cell
def _(df, mo):
    mo.output.append(df["71-q-p2-analysis-1-exclusion"].value_counts())
    mo.output.append(df["71-q-p2-analysis-1-exclusion-Comment"].dropna())
    return


@app.cell
def _(compute_counts, df, mo):
    mo.output.append(dict(compute_counts(df["72-q-p2-analysis-2-presentation"])))
    mo.output.append(df["72-q-p2-analysis-2-presentation-Comment"].dropna())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Nature of the Web
    """)
    return


@app.cell
def _(compute_counts, df, mo, out, report_cats):
    # Mentioned other factors + manual insights
    report_cats(out)
    mo.output.append(df["84-q-p3-factors-9-other"].value_counts())
    mo.output.append(compute_counts(df["84-q-p3-factors-9-other"]))
    return


@app.cell
def _(compute_counts, df, mo, tested_overview):
    # Tested other factors + manual insights
    mo.output.append(tested_overview)
    mo.output.append(df["factortested_other"].value_counts())
    mo.output.append(compute_counts(df["factortested_other"]))

    mo.output.append(df["factortested_other_org"].value_counts())
    mo.output.append(compute_counts(df["factortested_other_org"]))
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    - Multi-crawl:
        - 28 do not perform multiple crawls, 42 perform multiple crawls
        - Out of the multiple: most perform two crawls (12), however many other counts also exist up to several hundreds of configurations/longitudinal data collections.
        - Purpose of multiple crawls: Out of the 42 that have multiple crawls. 20 evaluate different crawling setups/configurations, 19 do some kind of robustness (e.g., running the 'same' crawl twice or running on different datasets', and 17 do a longitudinal study. Some overlap exists.
    """)
    return


@app.cell
def _(compute_counts, df, mo):
    with mo.redirect_stdout():

        print("Multi-crawl values:")
        mo.output.append(df["16-q-p1-major-9-multicrawl"].value_counts())

        print("Value counts of multi crawl count:")
        mo.output.append(df["69-q-p2-crawlmultiple-1-multiple"].value_counts())

        print("28 do not perform multiple crawls, 42 perform multiple crawls")
        print("Out of the multiple: most perform two crawls (12), however many other counts also exist up to several hundreds of configurations/longitudinal data collections.")

        mo.output.append(df["70-q-p2-crawlmultiple-2-multipledetails"].value_counts())
        mo.output.append(dict(compute_counts(df["70-q-p2-crawlmultiple-2-multipledetails"])))
        print("Out of the 42 that have multiple crawls. 20 evaluate different crawling setups/configurations, 19 do some kind of robustness (e.g., running the 'same' crawl twice or running on different datasets', and 17 do a longitudinal study. Some overlap exists.")
    return


@app.cell
def _(df, mo):
    # Note the 2x2 that used some bot evasion but did not mention this as a factor likely did not state that this could influence the measurement results
    mo.output.append(
        df.assign(
            mentions_bot=df["84-q-p3-factors-9-other"]
                .fillna("[]")
                .str.contains("Bot")
        )[[
            "mentions_bot",
            "45-q-p2-setup-implementation-15-botevasion",
            "56-q-p2-process-1-bot"
        ]].value_counts(dropna=False)
    )
    mo.output.append(df["45-q-p2-setup-implementation-15-botevasion-Comment"].dropna())
    mo.output.append(df["56-q-p2-process-1-bot-Comment"].dropna())
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Good Scientific Practices
    """)
    return


@app.cell(hide_code=True)
def _(lim_false, lim_onlyother, lim_ownsection, lim_true, mo):
    mo.md(rf"""
    - Limitations
        - {lim_true} papers mention limitations, {lim_false} do not mention limitations
        - {lim_ownsection} papers have a named (sub)section limitations (or related such as threats to validity), {lim_onlyother} mention limitations somewhere in the paper but do not have a named (sub)section
    """)
    return


@app.cell
def _(df, mo, pd):
    with mo.redirect_stdout():
        print("Limitations and where do they occur:")
        lim = df["88-q-p4-practices-1-limitations"].value_counts().to_dict()
        lim_true = lim[True]
        lim_false = lim[False]
        print(lim)

        lim = df["89-q-p4-practices-2-limitationsloc"].value_counts().to_dict()
        print(lim)
        lim_ownsection = lim["['Own section']"] + lim["['Other', 'Own section']"]
        lim_onlyother = lim["['Other']"]

        print("No clear trend across years.")
        mo.output.append(pd.crosstab(df["4-q-p1-meta-1-metadata.conference"], df["88-q-p4-practices-1-limitations"].fillna("None")))
        mo.output.append(pd.crosstab(df["4-q-p1-meta-1-metadata.year"], df["88-q-p4-practices-1-limitations"].fillna("None")))

    return lim_false, lim_onlyother, lim_ownsection, lim_true


@app.cell(hide_code=True)
def _(
    ethics_appendix_only,
    ethics_between_the_lines,
    ethics_false,
    ethics_main_text_bold,
    ethics_true,
    mo,
):
    mo.md(rf"""
    - Ethics:
        - {ethics_true} paper mention ethics (or related subset such as IRB or responsible disclosure), {ethics_false} do not touch the topic at all
        - {ethics_main_text_bold} have at least a named paragraph (or a (sub)section) about ethics before the references, {ethics_appendix_only} only mention ethics in the appendix, {ethics_between_the_lines} only mention IRB or ethical process between the lines
        - No clear differences across the conferences, more ethics in recent years
    """)
    return


@app.cell
def _(df, mo, pd):
    with mo.redirect_stdout():
        print("Ethics and location:")
        ethics = df["91-q-p4-practices-4-ethics"].value_counts().to_dict()
        ethics_true = ethics[True]
        ethics_false = ethics[False]

        ethics["loc"] = df["new_ethics_loc__new_ethics_loc"].value_counts().to_dict()
        mo.output.append(ethics)

        ethics_main_text_bold = ethics["loc"]["Own (sub)Section (Before References)"]
        ethics_between_the_lines = ethics["loc"]["Between the lines only"]
        ethics_appendix_only = ethics["loc"]["Own (sub)Section (Appendix)"]

        print("No clear differences betwene the conferences, clearly more ethics section over the years (from 11 without anything mentioned in 2021 to only 2 in 2025")
        mo.output.append(pd.crosstab(df["4-q-p1-meta-1-metadata.conference"], df["new_ethics_loc__new_ethics_loc"].fillna("None")))
        mo.output.append(pd.crosstab(df["4-q-p1-meta-1-metadata.year"], df["new_ethics_loc__new_ethics_loc"].fillna("None")))

    return (
        ethics_appendix_only,
        ethics_between_the_lines,
        ethics_false,
        ethics_main_text_bold,
        ethics_true,
    )


@app.cell
def _(df, mo):
    # Ethics Opt-Out and self-ident
    mo.output.append(df[["46-q-p2-setup-implementation-16-selfident", "21-q-p2-dataset-website-4-optout"]].value_counts())
    mo.output.append(df.loc[df["46-q-p2-setup-implementation-16-selfident"]]["46-q-p2-setup-implementation-16-selfident-Comment"])
    return


@app.cell
def _(df, mo):
    # Robots.txt
    mo.output.append(df["24-q-p2-dataset-webpage-2-internal"].value_counts())
    mo.output.append(df["29-q-p2-dataset-webpage-6-robots"].value_counts())
    mo.output.append(df.loc[df["29-q-p2-dataset-webpage-6-robots-Comment"].notna()][["29-q-p2-dataset-webpage-6-robots", "29-q-p2-dataset-webpage-6-robots-Comment"]])
    return


@app.cell
def _(df, mo):
    # Ethics: parallel and waiting times and co
    mo.output.append(df[["24-q-p2-dataset-webpage-2-internal", "65-q-p2-process-8-parallel"]].value_counts())
    mo.output.append(df.loc[df["65-q-p2-process-8-parallel-Comment"].notna()]["65-q-p2-process-8-parallel-Comment"])
    mo.output.append(df["67-q-p2-process-9-reqssecond"].value_counts())
    return


@app.cell
def _(ast, df, mo):
    # Availability: Open-Science section
    with mo.redirect_stdout():
        avail = df["94-q-p4-practices-6-5-avail"].apply(ast.literal_eval).apply(lambda x: x[0]).value_counts().to_dict()
        print(avail)
        avail_no_section = avail["No such section"]
        avail_section = avail["Open-Science or Similar Section (e.g., Data release)"]

        # TODO: maybe look at the sections in more depth?
        mo.output.append(df.loc[df["94-q-p4-practices-6-5-avail-Comment"].notna()]["94-q-p4-practices-6-5-avail-Comment"])
    return


@app.cell(hide_code=True)
def _(code_avail, code_github, code_link, mo):
    mo.md(rf"""
    - Code:
        - {code_avail["Not mentioned"]} papers do not mention anything about code availability in their paper
            - Interestingly 4 out of these have an AE available badge. One of them have no link in the paper, whereas the other 3 only have data in the provided link.
        - {code_avail["On request"]} paper mentions that code is available upon request
        - The other {70- code_avail["Not mentioned"] - code_avail["On request"]} mention that code is available:
            - {code_avail["Yes"]} have code available without issues detectable at the first glance
            - {code_avail["Missing link"]} mention that the code is released open-source or that they will release the code, but the paper does not contain a link. These seem like submission artifacts that should have been updated for the camera-ready version with a link but where not (for some we could find the corresponding repo on github/author website, for others we could not find anything)
            - {code_avail["Dead link"]} have a link that does not work and {code_avail["Empty repo"]} lead to an empty code repository!
            - {code_avail["Partially"]} have a working link but it "obviously" only contains part of the code (e.g., paper that did a crawl and released a browser extension as a defense and the repo only has the browser extension; or there are open github issues saying that import part of the code is missing and thus it cannot be executed); some of them mention in paper that only part of the code is released, whereas others are vague
        - From {code_link} papers with a link for code, {code_github} are on github. Other options such as Zenodo, gitlab, or Uni/institution websites are very rare (total of 10), some papers have multiple links, e.g., zenodo and github.
    """)
    return


@app.cell
def _(ast, df, mo, pd):
    with mo.redirect_stdout():
        code_avail = df["95-q-p4-practices-7-code"].apply(lambda x: ast.literal_eval(x)[0]).value_counts().to_dict()
        mo.output.append(code_avail)

        print("Interesting: papers with AE badge but no code mentioned")
        mo.output.append(pd.crosstab(df["95-q-p4-practices-7-code"], df["99-q-p4-practices-11-artifact-eval"]).T)
        mo.output.append(df.loc[(df["95-q-p4-practices-7-code"] == "['Not mentioned']") & (df["99-q-p4-practices-11-artifact-eval"] == "['Available']")][["4-q-p1-meta-1-metadata.title","95-q-p4-practices-7-code","99-q-p4-practices-11-artifact-eval","95-q-p4-practices-7-code-Comment"]])

        print("No link:")
        mo.output.append(df.loc[df["95-q-p4-practices-7-code"].str.contains("Missing link")][["4-q-p1-meta-1-metadata.title", "95-q-p4-practices-7-code", "95-q-p4-practices-7-code-Comment"]])

        print("Comments for problematic cases:")
        mo.output.append(df.loc[df["95-q-p4-practices-7-code"].str.contains("Partially|Missing link|Dead link|Empty repo|On request")][["95-q-p4-practices-7-code", "95-q-p4-practices-7-code-Comment"]])

        print("Code where:")
        mo.output.append(df["97-q-p4-practices-9-codewhere"].value_counts())
        code_github = df["97-q-p4-practices-9-codewhere"].str.contains("Github").sum()
        code_link = df["97-q-p4-practices-9-codewhere"].notna().sum()
        print(f"From {code_link} papers with a link for code, {code_github} are on github. Other options such as Zenodo, gitlab, or Uni/institution websites are very rare (total of 10), some papers have multiple links, e.g., zenodo and github.")
        mo.output.append(df[["95-q-p4-practices-7-code", "97-q-p4-practices-9-codewhere", "97-q-p4-practices-9-codewhere-Comment"]])
    return code_avail, code_github, code_link


@app.cell(hide_code=True)
def _(data_avail, data_github, data_link, mo):
    mo.md(rf"""
    - Data:
        - {data_avail["Not mentioned"]} papers do not mention anything about data availabity
        - {70 - data_avail["Not mentioned"]} papers mention data availability in the paper or only mention general availability in the paper but a single glance an the provided link also shows data or another link to data e.g., in the Github README
            - {data_avail["Missing link"]} have a missing link
            - {data_avail["Empty repo"]} have a link that does not contain any data
            - {data_avail["On request"]} mention that data is available on request only (e.g., to trusted researchers)
            - {data_avail["Some data available"]} have some data available. We could not feasibly check whether this is all data collected for the experiment or not. Usually this is clearly only partial data (e.g., a copy of the list of websites crawled, or only high-level results such as a list of all pages crawled and whether they were classified as phishing or not) and not all the data collected by the measurement, often not even enough to rerun their provided analysis scripts.
        - From {data_link} papers with a link for data, {data_github} are at least partially at github. Other options such as Zenodo, gitlab, or Uni/institution websites, Google Drive, Dropbox, etc. are rare, some papers have data at multiple locations, e.g., Google Drive and Github. (Note some of those links are not in the paper but only at the README of the code Github (we looked at the README/landing page, but not deeper).
    """)
    return


@app.cell
def _(ast, compute_counts, df, mo):
    with mo.redirect_stdout():
        data_avail = df["96-q-p4-practices-8-data"].value_counts().to_dict()
        mo.output.append(data_avail)
        # The one case with two options is counted as 'Empty Repo', the paper says the data is available at the link, however, at the link there is only a request form for other datasets, thus 'Empty Repo' is the best match
        data_avail = df["96-q-p4-practices-8-data"].apply(lambda x: ast.literal_eval(x)[0]).value_counts().to_dict()
        data_avail["Some data available"] = data_avail["Yes"] + data_avail["Partially"]
        print("Merge partial + yes as we cannot check that the full data is available:")
        mo.output.append(data_avail)


        mo.output.append(df.loc[df["96-q-p4-practices-8-data"].str.contains("Partially|Missing link|Dead link|Empty repo|On request")][["96-q-p4-practices-8-data", "96-q-p4-practices-8-data-Comment"]])

        mo.output.append(df["98-q-p4-practices-10-datawhere"].value_counts())
        # Note: googe drive + googledrive = 7
        mo.output.append(compute_counts(df["98-q-p4-practices-10-datawhere"]))
        data_github = df["98-q-p4-practices-10-datawhere"].str.contains("Github").sum()
        data_link = df["98-q-p4-practices-10-datawhere"].notna().sum()
        print(f"From {data_link} papers with a link for data, {data_github} are at least partially at github. Other options such as Zenodo, gitlab, or Uni/institution websites, Google Drive, Dropbox, etc. are rare, some papers have data at multiple locations, e.g., Google Drive and Github. (Note some of those links are not in the paper but only at the README of the code Github (we looked at the README/landing page, but not deeper).")
        mo.output.append(df[["96-q-p4-practices-8-data", "98-q-p4-practices-10-datawhere", "98-q-p4-practices-10-datawhere-Comment"]])
    return data_avail, data_github, data_link


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    - Extra Deep Dive: Zenodo and Anonymous4openscience
        - Data redacted
        - Anonymous4openscience:
            - In one of the analyzed papers, we saw a link to https://anonmyous.4open.science that was expired (classified as "dead link"/link that does not work above). As we have the PDFs and extracted text of all 7416 papers, we decided to check the state of such links in the full dataset. For that we performed a search for "4open" on all papers and then manually extracted the links and visited them.
            - A total of 77 papers had an anonymous.4open.science link in their final camera-ready PDF. Out of those 49 were expired, 17 showed the code on anomyous.4open.science platform, and 4 redirected to GitHub, 2 had an 4open.sciece link that was not an artifact of the paper itself but they refered to existing code by others, the remaining 5 had other issues such as showing an empty repo or saying not found.
            - For 20 out of those 77 papers, we saw that they additionally have another link (mostly github, also zenodo) in their paper. For example, they had an expired anonymous4openscience link in the introduction but a working zenodo link in the open science section or the other way round. Hinting at incomplete camera-ready updates.
            - Those links were likely meant only for the submission version but were not or only incompletly updated for the final camera-ready version of the paper. As those links often expire and also have other shortcomings (e.g., no way to open an issue), we suggest that the camera-ready proofing step of conferences should include a scan for such links and notify the authors to replace them.
            - Similarly, we searched for other submission artifacts that likely should not be contained in the camera-ready version and e.g., found 46 matches for "upon publication" (examples "we will open-source our codes upon publication"; in the camera-ready version, no link in the paper, difficult to find for the reader and maybe not published at all)
        - Zenodo:
            - We saw multiple Zenodo links and realized that one can update the records after the submission/AE/conference, so we investigated it.
            - We searched for "zenodo" and a total of 697/7416 papers had a match. In 2021 there were only 8 matches (5 for WWW), whereas in 2025 there were  487 matches (334 at USENIX that semi-required artifact availability and highly encouraged zenodo for that)
            - We the extracted all zenodo URLs from the papers with several regexes (e.g., some papers use https://doi.org/zenodo... and others use https://zenodo.org/records/<id>, ...) and extracted a total of 781 unique URLs (note some paper have multiple URLs as e.g., they have different links for dataset and code or the refer to other used software and cite the zenodo entry from the software)
            - We then used the Zenodo API to fetch the metadata for all those entries. Most interestingly 20 were marked as "restricted" (i.e., only the metadata is visible and the actual artifact is not publicly available). We note that while Zenodo is seen as a permanent repository in contrast to github, this is not completly true. Artifacts can be deleted in the first 30 days (or under special circumstances) and it is always possible to change the visibility to restricted (see https://help.zenodo.org/docs/deposit/manage-records/#delete). We also note that there can be good reasons for restricted artifacts, e.g., due to an embargo or sensitive datasets.
                - 6 papers (5 USENIX 2025, 1 NDSS) split their code/data into public and private parts and included both an open and a restricted Zenodo record
                - We investigated the remaining 14 cases (10 USENIX 2025, 1 CCS 2025, 1 PETS 2025, 1 WWW 2024, 1 USS 2023)
                    - The PETS case is not their own artifact, the CCS case is justified and the USS 2023 has no AE badge
                    - This leaves us with the 10 USENIX 2025 and 1 WWW 2024 paper that only have a restricted link in the paper and have an AE available badge!
                        - 4 are highly problematic as they claim that the artifact is openly available in the "open science" section but it is not available (anymore; seemed like some of them changed after te AE evaluation/conference, zenodo only publishes a last modified timestamp, so it is unclear when they went restricted or if they were restricted from the beginning, for some archived copies in the IA show that they were available in the past). 4 out of these are from the same group. 2 have a link to (parts of the artifact) on github or other resources in the metadata/description of the zenodo record. One is accidentally available in the automatic software heritage archive of zenodo.
                        - 4 justify the restriction in the paper, but it is unclear why they received the available badge then.
                            - One describes the restriction in the "Ethics Considerations" section of the paper that contradicts the Open Science section.
                            - 1 has a restricted link and justifies this with an embargo period in the paper, however, the embargo passed 6 months ago and it is still not available, also unclear how it could receive the AE available badge
                        - 2 have a restricted link, but a newer version of the artifact on Zenodo is available
                        - 1 has a restricted link, but the paper also has a link to github with the code that works
            - We also checked all the links from  https://secartifacts.github.io/usenixsec2025/results:
                - 393 are from Zenodo (including the problematic cases described above)
                - the other 31 links:
                    - 1 github (multiple URLs, the other is zenodo)
                    - 4x software heritage (all work)
                    - 8x osf (1 is broken)
                    - 4x university repositories (all work)
                    - 14x figshare (1 broken)
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    - AE:
        - Note that some conferences do not offer badges, the exact badge definitions differ across conferences and sometimes only a subset of badges is available at the conference (additionally we mapped the generic artifact badge from PETS before 2024 to Available).
        - Roughly half of the year/conference combinations have had no AE process, from the other 19 have no artifact badge, while 15 have at least an available badge and 7 out of these have additional badges.
    """)
    return


@app.cell
def _(df, mo, pd):
    with mo.redirect_stdout():
        print("Note that some conferences do not offer badges, the exact badge definitions differ across conferences and sometimes only a subset of badges is available at the conference (additionally we mapped the generic artifact badge from PETS before 2024 to Available).")
        # Usually always only encouraged and not required
        # USS: 2020+ (starting 2025 semi-required)
        # NDSS: 2024+
        # PETS: 2020+ (generic badge until 2024, then available + reproduced, in 2025 added functional)
        # CCS: 2023+
        # S&P: 2026+
        # IMC: No badge
        # WWW: 2024+ (available badge only)

        conf = df["4-q-p1-meta-1-metadata.conference"]
        year = pd.to_numeric(df["4-q-p1-meta-1-metadata.year"], errors="coerce")

        no_ae_process = (
            ((conf == "uss")    & (year < 2020)) |
            ((conf == "ndss")   & (year < 2024)) |
            ((conf == "popets") & (year < 2020)) |
            ((conf == "ccs")    & (year < 2023)) |
            ((conf == "sp")     & (year < 2026)) |
            ((conf == "imc")) |
            ((conf == "www")    & (year < 2024))
        )

        df.loc[
            no_ae_process,
            "99-q-p4-practices-11-artifact-eval"
        ] = "no AE process"
        mo.output.append(df["99-q-p4-practices-11-artifact-eval"].value_counts())
        print("Roughly half of the year/conference combinations have had no AE process, from the other 19 have no artifact, while 15 have at least an available badge and 7 out of these have additional badges.")
    return


if __name__ == "__main__":
    app.run()
