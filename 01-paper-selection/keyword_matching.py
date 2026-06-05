from concurrent.futures import ProcessPoolExecutor
from functools import lru_cache
import pandas as pd
from tqdm import tqdm
import re

base_path = "01-paper-selection/paper_dir/"

@lru_cache(maxsize=None)
def open_file(path):
    with open(path, 'r', encoding='utf-8') as file:
            page_text = file.read()
    return page_text

def contains_regex(args):
    path, regex_pattern, keywords = args
    try:
        # Read the full content of the text or markdown file
        page_text = open_file(path)

        # Check for regex match and that at least one keyword is in the text
        if keywords:
            return bool(regex_pattern.search(page_text)) and any(keyword in page_text for keyword in keywords)
        # Check for any regex match
        else:
            return bool(regex_pattern.search(page_text))

    except Exception as e:
        # print(f"Error reading {path}: {e}")
        return None
    # No regex found in entire txt
    return False


def compile_patterns(keywords, keyword_patterns=None):
    """Create one regex pattern out of keywords and keyword_patterns.
    keywords are used with word boundaries: \b(keyword1|keyword2)\b
    keyword_patterns are used as is: (pattern1)|(pattern2)
    Additionally all groups are non-captchuring (?:pattern) to speed things up
    Output is compiled pattern: \b(keyword1|keyword2)\b|(pattern1)|(pattern2), compiled with re.IGNORECASE and re.UNICODE
    """
    if keywords:
        final_pattern = rf"\b(?:{'|'.join(map(re.escape, keywords))})\b"

    if keyword_patterns:
        keyword_patterns = f"{'|'.join(f'(?:{pattern})' for pattern in keyword_patterns)}"
        # Either keywords or keyword patterns have to match
        if keywords:
            final_pattern =f"{final_pattern}|{keyword_patterns}"
        # No keywords exist, only use the pattern
        else:
            final_pattern = keyword_patterns
    return re.compile(final_pattern, re.IGNORECASE), final_pattern

def keyword_matching(df, keywords=["tranco", "alexa", "website", "web site"], keyword_patterns=[r"\btop\b(?:\s+\w+){0,3}?\s+\b(web)?site(s)?\b"]):
    # keywords = ["tranco", "alexa", "website", "web site"]
    # Match "Top (up to 3 words in between) (web)site(s)" as well!
    # keyword_patterns = [r"\btop\b(?:\s+\w+){0,3}?\s+\b(web)?site(s)?\b"] 
    pattern, p_string = compile_patterns(keywords, keyword_patterns)
    arguments = []
    for path in df["path_txt"]:
        arguments.append((f"{base_path}{path}", pattern, None))
    with ProcessPoolExecutor(max_workers=100) as executor:
        res = list(tqdm(executor.map(contains_regex, arguments), total=len(df)))
    return res, p_string


def main():
    paper_selection = pd.read_csv("01-paper-selection/paper_selection.csv")
    print(paper_selection["Keyword Match"].value_counts().to_frame())
    matches, details = keyword_matching(paper_selection)
    paper_selection["Keyword Match"] = matches
    paper_selection["Keyword Details"] = details
    print(paper_selection["Keyword Match"].value_counts().to_frame())

if __name__ == "__main__":
    main()