from pathlib import Path
from typing import Annotated, Literal, Union

import yaml
from pydantic import BaseModel, Field


class CsvSource(BaseModel):
    type: Literal["csv"] = "csv"
    path: str
    description: str = ""


class TextSource(BaseModel):
    """A set of free-text artifacts describing an agent's *intent*, not its data.

    The cold-start path: a repo that has no dataset yet — only the agent's spec
    (system prompt, README, tool/function definitions, user stories). Step 1
    infers a ``DomainContext`` from these instead of from sampled rows. Only
    Step 1 is supported for a text source; Steps 2-5 still need labeled data.
    """

    type: Literal["text"] = "text"
    paths: list[str] = Field(
        min_length=1, description="Text/markdown/code files describing the agent"
    )
    description: str = ""


DomainSource = Annotated[Union[CsvSource, TextSource], Field(discriminator="type")]


class TaskSpec(BaseModel):
    """How to read one dataset row as an evaluation task.

    This is the small contract that makes the engine dataset-agnostic: name the
    columns that hold the task input, the gold answer, and (optionally) the
    grounding evidence, and declare how correctness is decided.

    ``kind``:
      - ``grounded_qa``    — answer compared to gold; optionally checked against
        ``grounding_field`` (e.g. FinanceBench: answer must appear in evidence).
      - ``code_execution`` — the prediction is a Python program, scored by
        actually running it (e.g. ScienceAgentBench).
    """

    kind: Literal["grounded_qa", "code_execution"]
    id_field: str = Field(description="Column holding a unique row id")
    input_field: str = Field(description="Column holding the task / question text")
    gold_field: str = Field(description="Column holding the reference answer / program name")
    grounding_field: str | None = Field(
        default=None, description="Column holding supporting evidence (grounded_qa only)"
    )
    category_field: str | None = Field(
        default=None, description="Column to group metrics by; defaults to stratify_by"
    )
    pass_threshold: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Min correctness for a case to pass"
    )


class ProjectConfig(BaseModel):
    project: str = Field(min_length=1)
    domain_sources: list[DomainSource] = Field(min_length=1)
    sample_size: int = 100
    sample_seed: int = 42
    stratify_by: str | None = None
    sample_per_stratum: int = 2
    task: TaskSpec | None = None

    @property
    def category_field(self) -> str | None:
        """Resolved grouping column: explicit task.category_field, else stratify_by."""
        if self.task and self.task.category_field:
            return self.task.category_field
        return self.stratify_by


def load_config(path: str | Path) -> ProjectConfig:
    raw = yaml.safe_load(Path(path).read_text())
    return ProjectConfig.model_validate(raw)
