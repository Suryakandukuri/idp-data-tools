import re
from pydantic import BaseModel, validator
from typing import Optional
from typing import Literal, Dict, List


def alphanumeric_name(string: str):
    return "".join(re.findall(r"[\w\d ]", string.strip().lower())).replace(" ", "_")


PostgresDType = Literal["NUMERIC", "BOOLEAN", "TEXT", "DATE", "TIMESTAMP"]
polars_dtype_to_postgres_dtype_mapping: Dict[str, PostgresDType] = {
    "UInt8": "NUMERIC",
    "UInt16": "NUMERIC",
    "UInt32": "NUMERIC",
    "UInt64": "NUMERIC",
    "Int8": "NUMERIC",
    "Int16": "NUMERIC",
    "Int32": "NUMERIC",
    "Int64": "NUMERIC",
    "Float32": "NUMERIC",
    "Float64": "NUMERIC",
    "Boolean": "BOOLEAN",
    "Utf8": "TEXT",
    "Categorical": "TEXT",
    "Date": "DATE",
    "Datetime": "TIMESTAMP",
}


class Variable(BaseModel):
    # postgres friendly name with no special characters
    name: str
    # name of the column is assumed to be the variable description
    description: str
    # postgres datatype
    data_type: PostgresDType
    measurement_unit:  Optional[str] = None
    # constant unit / changing unit
    unit_type:  Optional[str] = None

    @validator("name", allow_reuse=True)
    def is_alphanumeric(cls, value):
        if not bool(re.search(r"[^a-z0-9_]", value)):
            return value
        raise ValueError(
            "can only contain lowercase alphanumeric characters and underscores")

    @validator("name", allow_reuse=True)
    def less_than_64_characters(cls, value):
        if not (len(value) > 64):
            return value
        raise ValueError("can not use more than 64 characters")


Sectors = Literal[
"Administration and Governance",
"Animal Husbandry and Fisheries",
"Banking",
"Census",
"Climate & Weather",
"Commodity Boards",
"Commerce",
"Consumer Affairs",
"Covid",
"Crime",
"Culture and Tourism",
"Demographics",
"Digital Infrastructure",
"Economy",
"Elections",
"Energy",
"External Affairs",
"Financial Inclusion",
"Food and Agriculture",
"Forestry and Wildlife",
"General",
"Government Schemes",
"Health",
"Housing",
"Industries",
"Justice",
"National Sample Survey",
"Natural Disasters",
"Other",
"Petroleum and Gas",
"Rural Development",
"Satellite Imagery Data",
"Science",
"Socio Economic",
"Transportation",
"Union Budget",
"Water",
"Other"
]

GranularityLevel = Literal[
    "All India",
    "State",
    "District",
    "Sub-District",
    "Block",
    "Village",
    "Assembly Constituency",
    "Parliamentary Constituency",
    "Gram Panchayat",
    "Other",
    "Point"
]

Frequency = Literal[
    "Daily",
    "Weekly",
    "Fortnightly",
    "Monthly",
    "Quarterly",
    "Yearly",
    "Quinquennially",
    "Other",
    "Seasonal"
]


class ResourceMetadata(BaseModel):
    # domains are referred to as sectors in ckan
    domains: List[str]
    # dataset name is equivalent to package name in ckan
    dataset_name: str
    # Lowest level for which the data is available
    granularity_level: str
    # frequency at which the data is released
    frequency: str
    source_name: str
    source_link: str
    # when was the data last retrieved by us
    data_retrieval_date: str
    # when was the latest data last released on source
    data_last_updated: str
    data_extraction_page: str
    # dataset description
    about: str
    # data collection methodology used by the source
    methodology: str
    # name of the resource in ckan
    resource: str
    # what insights does the dataset provide
    data_insights: str
    # SEO tags
    tags: List[str]
    # similar resources
    similar_datasets: List[str]
    # package description
    package_description: str


class AdditionalInformation(BaseModel):
    years_covered: Optional[str] = None
    notes: Optional[str] = None
    no_of_states: Optional[int] = None
    no_of_districts: Optional[int] = None
    no_of_tehsils: Optional[int] = None
    no_of_villages: Optional[int] = None
    no_of_gps: Optional[int] = None
    no_of_indicators: int
