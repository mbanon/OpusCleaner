import os
import gzip
import sys
from typing import Optional, Iterable, TypeVar, Union, Literal, Any, AsyncIterator
from contextlib import ExitStack
from itertools import chain
from pydantic import BaseModel, parse_obj_as, validator
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, StreamingResponse
from fastapi.encoders import jsonable_encoder
from enum import Enum
import asyncio
import json
import subprocess
import hashlib
from glob import glob
from tempfile import TemporaryFile
from shutil import copyfileobj
from pprint import pprint

from datasets import list_datasets
from sample import sample


DATA_PATH = 'data/train-parts'

FILTER_PATH = 'filters/*.json'

# col.py is used to apply a monolingual filter to a bilingual dataset. Needs
# to be absolute since filters can run from different cwds.
COL_PY = os.path.abspath('./col.py')

SAMPLE_PY = os.path.abspath('./sample.py')

SAMPLE_SIZE = 50


class File(BaseModel):
    path: str
    size: int


class Dataset(BaseModel):
    name: str
    columns: dict[str,File]


class FilterType(Enum):
    BILINGUAL = "bilingual"
    MONOLINGUAL = "monolingual"


class FilterParameterBase(BaseModel):
    type: str
    help: Optional[str]

    def export(self, value: Any) -> str:
        return str(value)


class FilterParameterFloat(FilterParameterBase):
    type: Literal["float"]
    min: Optional[float]
    max: Optional[float]
    default: Optional[float]


class FilterParameterInt(FilterParameterBase):
    type: Literal["int"]
    min: Optional[int]
    max: Optional[int]
    default: Optional[int]


class FilterParameterBool(FilterParameterBase):
    type: Literal["bool"]
    default: Optional[bool]

    def export(self, value: Any) -> str:
        return "1" if value else ""


class FilterParameterStr(FilterParameterBase):
    type: Literal["str"]
    default: Optional[str]
    allowed_values: Optional[list[str]]


FilterParameter = Union[
    FilterParameterFloat,
    FilterParameterInt,
    FilterParameterBool,
    FilterParameterStr
]


class Filter(BaseModel):
    type: FilterType
    name: str # comes from filename by default
    description: Optional[str]
    command: str
    basedir: Optional[str] # same as .json file by default
    parameters: dict[str,FilterParameter]


class FilterStep(BaseModel):
    filter: str
    parameters: dict[str,Any]
    language: Optional[str]

    @validator('filter')
    def check_filter(cls, filter):
        if filter not in FILTERS:
            raise ValueError(f'Unknown filter `{filter}`')
        return filter

    @validator('parameters')
    def check_parameters(cls, parameters, values, **kwargs):
        if 'filter' in values:
            required = set(FILTERS[values['filter']].parameters.keys())
            provided = set(parameters.keys())
            if len(required - provided) > 0:
                raise ValueError(f"Missing filter parameters: {' '.join(required - provided)}")
            if len(provided - required) > 0:
                raise ValueError(f"Provided parameters not supported by the filter: {' '.join(provided - required)}")
        return parameters

    @validator('language', always=True)
    def check_language_is_provided(cls, language, values, **kwargs):
        if 'filter' in values:
            if FILTERS[values['filter']].type == FilterType.BILINGUAL and language is not None:
                raise ValueError('Cannot `language` attribute for a bilingual filter')
            elif FILTERS[values['filter']].type == FilterType.MONOLINGUAL and language is None:
                raise ValueError('`language` attribute required for a monolingual filter')
        return language


def list_filters(path) -> Iterable[Filter]:
    for filename in glob(path, recursive=True):
        try:
            with open(filename) as fh:
                defaults = {
                    "name": os.path.splitext(os.path.basename(filename))[0],
                    "basedir": os.path.dirname(filename)
                }
                yield parse_obj_as(Filter, {**defaults, **json.load(fh)})
        except Exception as e:
            print(f"Could not parse {filename}: {e}", file=sys.stderr)



FILTERS: dict[str,Filter] = {}

def reload_filters():
    global FILTERS
    FILTERS = {definition.name: definition for definition in list_filters(FILTER_PATH)}

reload_filters()


T = TypeVar("T")

def none_throws(optional: Optional[T], message: str = "Unexpected `None`") -> T:
    """Convert an optional to its value. Raises an `AssertionError` if the
    value is `None`"""
    if optional is None:
        raise AssertionError(message)
    return optional


def sample_path(name:str, langs: Iterable[str]):
    languages = '.'.join(sorted(langs))
    return os.path.join(DATA_PATH, f'.sample.{name}.{languages}.gz')


async def compute_sample(name:str, columns:list[tuple[str,os.DirEntry]]):
    langs = [lang for lang, _ in columns]
    with TemporaryFile() as tempfile, gzip.open(tempfile, 'wb') as fout:  # type: ignore[name-defined]
        proc = await asyncio.subprocess.create_subprocess_exec([SAMPLE_PY, '-n', SAMPLE_SIZE] + [file.path for _, file in columns],
            stdout=fout,
            stderr=asyncio.subprocess.PIPE)

        _, stderr = await proc.communicate()

        if proc.returncode != 0:
            raise Exception(f'sample.py returned {proc.returncode}: {stderr.decode()}')

        tempfile.seek(0)

        with open(sample_path(name, langs), 'wb') as fdest:
            copyfileobj(tempfile, fdest)


class FilterOutput(BaseModel):
    stdout: list[dict[str,str]]
    stderr: Optional[str]

    def __init__(self, langs:list[str], stdout:bytes, stderr:Optional[bytes] = None):
        super().__init__(
            stdout=[dict(zip(langs, line.split('\t'))) for line in stdout.decode().split('\n')],
            stderr=stderr.decode() if stderr is not None else None)


async def get_sample(name:str, filters:list[FilterStep]) -> AsyncIterator[FilterOutput]:
    columns: list[tuple[str,os.DirEntry]] = sorted(list_datasets(DATA_PATH)[name].items(), key=lambda pair: pair[0])
    langs = [lang for lang, _ in columns]

    # If we don't have a sample stored, generate one. Doing it in bytes because
    # it might save us parsing utf-8 (also assumptions! It it utf-8?)
    if not os.path.exists(sample_path(name, langs)):
        await compute_sample(name, columns)

    with gzip.open(sample_path(name, langs), 'rb') as fh:
        sample = fh.read()

    yield FilterOutput(langs, sample)

    for i, filter_step in enumerate(filters):
        filter_definition = FILTERS[filter_step.filter]
        
        filter_env = os.environ.copy()
        for name, props in filter_definition.parameters.items():
            filter_env[name] = props.export(filter_step.parameters[name])

        if filter_definition.type == FilterType.BILINGUAL:
            command = filter_definition.command
        elif filter_definition.type == FilterType.MONOLINGUAL:
            column = langs.index(none_throws(filter_step.language))
            command = f'{COL_PY} {column} {filter_definition.command}'
        else:
            raise NotImplementedError()
        
        p_filter = await asyncio.create_subprocess_shell(command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=filter_env,
            cwd=filter_definition.basedir)
        
        # Check exit codes, testing most obvious problems first.
        filter_output, filter_stderr = await p_filter.communicate(input=sample)
        if p_filter.returncode != 0:
            raise Exception(f"Step {i}: {filter_step.filter} failed:\n{filter_stderr!s}")

        yield FilterOutput(langs, filter_output, filter_stderr)

        sample = filter_output


def stream_jsonl(iterable):
    return StreamingResponse(
        (
            json.dumps(jsonable_encoder(line), separators=(',', ':')).encode() + b"\n"
            async for line in iterable
        ),
        media_type='application/json')


app = FastAPI()

app.mount('/static', StaticFiles(directory='static'), name='static')

@app.get('/datasets/')
def api_list_datasets() -> list[Dataset]:
    return [
        Dataset(name=name, columns={
            lang: File(path=file.name, size=file.stat().st_size)
            for lang, file in columns.items()
        })
        for name, columns in list_datasets(DATA_PATH).items()
    ]


@app.get('/datasets/{name}/sample')
async def api_get_dataset(name:str) -> AsyncIterator[FilterOutput]:
    return stream_jsonl(get_sample(name, []))


@app.post('/datasets/{name}/sample')
async def api_get_filtered_dataset(name:str, filters:list[FilterStep]) -> AsyncIterator[FilterOutput]:
    return stream_jsonl(get_sample(name, filters))


def filter_configuration_path(name:str) -> str:
    return os.path.join(DATA_PATH, f'{name}.filters.json')


@app.get('/datasets/{name}/configuration')
def api_get_dataset_filters(name:str) -> list[FilterStep]:
    if not os.path.exists(filter_configuration_path(name)):
        return []

    with open(filter_configuration_path(name), 'r') as fh:
        return parse_obj_as(list[FilterStep], json.load(fh))


@app.post('/datasets/{name}/configuration')
def api_update_dataset_filters(name:str, filters:list[FilterStep]):
    with open(filter_configuration_path(name), 'w') as fh:
        return json.dump([step.dict() for step in filters], fh)


@app.get('/filters/')
def api_get_filters():
    reload_filters()
    return FILTERS


@app.get('/')
def redirect_to_interface():
    return RedirectResponse('/static/index.html')

