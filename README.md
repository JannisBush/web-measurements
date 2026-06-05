# Artifact for SoK: Hidden Variables in Security and Privacy Web Measurements

This repository contains the supplementary material for the Paper "SoK: Hidden Variables in Security and Privacy Web Measurements".

## Installation
- Install Poetry: https://python-poetry.org/docs/#installation
- Run `poetry install`

## 01-paper-selection
- [paper_selection.csv](01-paper-selection/paper_selection.csv) contains the list of 7416 papers from the 7 conferences for 2021 to 2025 including whether the paper matched the keywords and whether it was decided to be in-scope after manual screening by two coders
- `paper_dir` Directory to hold the PDF and TXT files of the papers. Not provided due to copyright reasons. Contains two dummy TXT files to showcase the structure.
- [keyword_matching.py](01-paper-selection/keyword_matching.py) code that was used to perform the keyword matching. Execute with `poetry run python 01-paper-selection/keyword_matching.py`. The output uses the two dummy TXT files and should show one paper matching the keywords and one not matching the keywords. To run the full matching obtain all PDFs, extract the text content as TXT (e.g., with [PyMuPDF](https://pymupdf.readthedocs.io/en/latest/)) and put the files into `paper_dir` according to the relative path specified in `paper_selection.csv`
- [sampling.py](01-paper-selection/sampling.py) code that was used to sample the 70+2 papers for detailed data extraction. Execute with `poetry run python 01-paper-selection/sampling.py` to verify that the same papers are sampled that are sampled in `paper_selection.csv`

## 02-data-extraction