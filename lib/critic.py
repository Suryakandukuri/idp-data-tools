# %%
import pandas as pd
from typing import List
from rapidfuzz.process import extractOne
from functools import partial
from enum import Enum, auto
from collections import namedtuple
from typing import List
import numpy as np
from collections import OrderedDict
from itertools import chain
# %%


class TestResultType(Enum):
    ERROR = auto()
    WARNING = auto()
    INFO = auto()
    SUCCESS = auto()


TestResult = namedtuple("TestResult", ["type", "message"])
# %%


def contains_sheets(wb: pd.ExcelFile, sheet_names: List[str], strict=False):
    """
    Checks whether the workbook contains the required sheets.
    """
    sheets = wb.sheet_names if strict else [
        name.strip().lower()
        for name in wb.sheet_names
    ]
    return {
        name: name in sheets
        for name in sheet_names
    }
# %%


required_sheets = ["codebook",
                   "metadata information", "additional information"]


def has_required_sheets(wb: pd.ExcelFile, **kwargs):
    return all(contains_sheets(wb, sheet_names=required_sheets, **kwargs).values())
# %%


def get_similar(name: str, candidates, score_cutoff=90, **kwargs):
    result = extractOne(name, candidates, score_cutoff=score_cutoff, **kwargs)
    return None if result is None else result[0]


def get_similar_or_itself(name: str, candidates, **kwargs):
    match = get_similar(name, candidates, **kwargs)
    return name if match is None else match


# %%
codebook_columns = ['variable name', 'variable description', 'variable type',
                    'unit of measurement', 'unit type']
variable_types = ["text", "numeric", "date", "region", "categorical"]
metadata_fields = ["domain", "dataset name", "granularity level", "frequency", "source name", "source link", "data retrieval date",
                   "data last updated", "data extraction page", "about", "methodology", "resource", "data insights", "tags", "similar datasets","package description"]
additional_information_fields = ["years covered", "number of state(s) / union territories", "additional information",
                                 "number of district(s)", "number of tehsil(s)", "number of gp", "number of villages", "number of indicators"]
# %%


def find_titles_row_in_codebook(df: pd.DataFrame, candidate_rows=[0, 1, 2], titles=codebook_columns):
    max_matches_row = None
    max_matches = 0
    for i in candidate_rows:
        matches = df.iloc[i].str.lower().str.strip().apply(
            partial(get_similar, candidates=titles)).apply(bool).value_counts()
        if True not in matches:
            continue
        num_matches = matches[True]
        if num_matches > max_matches:
            max_matches_row = i
            max_matches = num_matches
    return max_matches_row
# %%


def parse_codebook_headers(df: pd.DataFrame, titles_row: int, titles=codebook_columns):
    df = df.copy()
    df.columns = df.iloc[titles_row].str.lower().str.strip().apply(
        partial(get_similar_or_itself, candidates=titles))
    for col in df.columns:
        df[col] = df[col].str.strip()
    return df.iloc[titles_row+1:].reset_index(drop=True)
# %%


def check_column_titles(s: pd.Series, titles=codebook_columns):
    return {
        n: bool(get_similar(n, candidates=titles))
        for n in s.str.strip().str.lower()
    }
# %%


def check_metadata_fields(s: pd.Series, fields=metadata_fields):
    s = s.str.strip().str.lower().to_list()
    return {
        n: bool(get_similar(n, candidates=s))
        for n in fields
    }


# %%
def parse_metadata(df: pd.DataFrame, fields=metadata_fields):
    return OrderedDict({
        field: df[1][df[0].str.strip().str.lower().apply(
            partial(get_similar, candidates=[field])).apply(bool)].apply(lambda v: v.strip() if type(v) == "str" else v).to_list()
        for field in fields
    })
# %%


def has_invalid_variable_types(s: pd.Series, valid_types = variable_types):
    s = s.str.lower().str.strip()
    valid_crit = s.isin(valid_types)
    if valid_crit.all():
        return False
    else:
        return s[~valid_crit].dropna().to_list()

# %%


def all_rows_have_values(column: pd.Series):
    crit = column.isna() | (column == "")
    return not (crit.any())
# %%


def ignore_sheet_title(df: pd.DataFrame, titles=set(required_sheets)):
    key, value = df.iloc[0, :2].str.strip(
    ).str.lower().replace("", np.nan).to_list()
    if key in required_sheets and pd.isna(value):
        return df.iloc[1:]
    return df
# %%


def get_duplicate_values(column: pd.Series):
    value_counts = column.str.strip().value_counts()
    return value_counts[value_counts > 1].index.unique().tolist()


def critique_additional_information(df: pd.DataFrame, test_results: List[TestResult] = list()):
    if df.shape[1] != 2:
        test_results.append(
            TestResult(TestResultType.ERROR, "Additional information sheet is should contain only two columns where the first column contains the field names and the second column contains their corresponding values."))
        return test_results, None
    df = ignore_sheet_title(df)
    check_fields = check_metadata_fields(
        df[0], fields=additional_information_fields)
    absent_fields = [key for key, value in check_fields.items()
                     if value == False]
    for field in absent_fields:
        test_results.append(
            TestResult(TestResultType.ERROR, f"Couldn't find '{field}' field."))
    if len(absent_fields) == 0:
        test_results.append(
            TestResult(TestResultType.SUCCESS, f"All the required fields are present."))
    additional_information = parse_metadata(df, fields=list(
        set(additional_information_fields) - set(absent_fields)))

    for field, value_list in additional_information.items():
        if len(value_list) > 1:
            test_results.append(
                TestResult(TestResultType.WARNING, f"Multiple values found for '{field}' field."))
        elif len(value_list) == 0 or pd.Series(value_list).replace("", np.nan).isna().any():
            test_results.append(
                TestResult(TestResultType.INFO, f"'{field}' field has no associated value."))
            additional_information[field] = [pd.NA]
            continue
        additional_information[field] = [value_list[-1]]

    return test_results, pd.DataFrame({"key": additional_information.keys(), "value": list(chain(*additional_information.values()))})
# %%


def critique_metadata(df: pd.DataFrame, test_results: List[TestResult] = list()):
    if df.shape[1] != 2:
        test_results.append(
            TestResult(TestResultType.ERROR, "Metadata sheet is should contain only two columns where the first column contains the field names and the second column contains their corresponding values."))
        return test_results, None

    check_fields = check_metadata_fields(df[0])
    absent_fields = [key for key, value in check_fields.items()
                     if value == False]
    for field in absent_fields:
        test_results.append(
            TestResult(TestResultType.ERROR, f"Couldn't find '{field}' field."))
    if len(absent_fields) == 0:
        test_results.append(
            TestResult(TestResultType.SUCCESS, f"All the required fields are present."))

    metadata = parse_metadata(df, fields=list(
        set(metadata_fields) - set(absent_fields)))
    for field, value_list in metadata.items():
        if len(value_list) > 1:
            test_results.append(
                TestResult(TestResultType.WARNING, f"Multiple values found for '{field}' field."))
        elif len(value_list) == 0 or pd.Series(value_list).replace("", np.nan).isna().any():
            test_results.append(
                TestResult(TestResultType.ERROR, f"'{field}' field has no associated value."))
            metadata[field] = [pd.NA]
            continue
        metadata[field] = [value_list[0]]

    return test_results, pd.DataFrame({"key": metadata.keys(), "value": list(chain(*metadata.values()))})


# %%


def critique_codebook(df: pd.DataFrame, test_results: List[TestResult] = list()):
    titles_row_idx = find_titles_row_in_codebook(df)
    if titles_row_idx != 1:
        test_results.append(
            TestResult(TestResultType.ERROR, "Column titles in the codebook sheet shoud be on the 2nd row"))

    column_checks = check_column_titles(df.iloc[titles_row_idx])
    unrecognized_columns = [key for key,
                            value in column_checks.items() if value == False]
    if len(unrecognized_columns):
        test_results.append(
            TestResult(TestResultType.WARNING, f"""Unrecognized column titles in the codebook sheet: '{"', '".join(unrecognized_columns)}'"""))

    codebook = parse_codebook_headers(df, titles_row=titles_row_idx)

    missing_cols = list(filter(lambda c: c not in codebook.columns.to_series().apply(
        partial(get_similar_or_itself, candidates=codebook_columns)).tolist(), codebook_columns))
    if len(missing_cols) != 0:
        for col in missing_cols:
            test_results.append(TestResult(TestResultType.ERROR,
                                           f"Couldn't find '{col}' in 'codebook' sheet."))
    else:
        test_results.append(TestResult(TestResultType.SUCCESS,
                                       f"All the required columns are present."))

    invalid_var_types = has_invalid_variable_types(codebook["variable type"])
    if invalid_var_types:
        test_results.append(
            TestResult(TestResultType.ERROR, f"""Invalid variable type: '{"', '".join(set(invalid_var_types))}'."""))
    else:
        test_results.append(
            TestResult(TestResultType.SUCCESS, f"All variable types are valid."))
    codebook["variable type"] = codebook["variable type"].str.lower().str.strip().str.replace("categorical", "text").str.replace("region", "text")

    if "varaible name" in codebook.columns:
        if all_rows_have_values(codebook["variable name"]):
            test_results.append(
                TestResult(TestResultType.ERROR, f"Variable name cannot be empty. One of the rows in 'variable name' column contains an empty value."))
        duplicates = get_duplicate_values(codebook["variable name"])
        if len(duplicates) > 0:
            test_results.append(
                TestResult(TestResultType.ERROR, f"""All variable names should be unique. Duplicates: '{"', '".join(set(duplicates))}'""")
            )

    

    if "variable description" in codebook.columns and not all_rows_have_values(codebook["variable description"]):
        test_results.append(
            TestResult(TestResultType.ERROR, f"Variable description cannot be empty. One of the rows in 'variable description' column contains an empty value."))
    return test_results, codebook

# %%


def critique_sheets(file: pd.ExcelFile, test_results=list()):
    if not has_required_sheets(file):
        test_results.append(
            TestResult(TestResultType.ERROR, "The file must have at least three sheets named 'codebook', 'metadata information', and 'additional information'."))
    else:
        test_results.append(
            TestResult(TestResultType.SUCCESS, "The file has three sheets named 'codebook', 'metadata information', and 'additional information'."))

    return test_results


def critique(file: pd.ExcelFile, test_results=list()):
    test_results = critique_sheets(file)
    test_results, codebook = critique_codebook(file.parse(
        "codebook", header=None), test_results=test_results)
    return test_results, codebook
