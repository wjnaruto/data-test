from typing import List

from pydantic import BaseModel, Field


class GlossaryFieldVo(BaseModel):
    fieldName: str = Field("", description="The name of the field in the glossary")
    fieldDescription: str = Field("", description="The description of the field in the glossary")
    templateName: str = Field("", description="The name of the template associated with the glossary")

    @classmethod
    def from_record(cls, metadata):
        return cls(
            **metadata,
            fieldName=metadata.get("Field Name", ""),
            fieldDescription=metadata.get("Field Description", ""),
            templateName=metadata.get("Template Name", ""),
        )


class GlossaryTemplateVO(BaseModel):
    templateName: str = Field("", description="The name of the glossary template")
    fields: List[GlossaryFieldVo] = Field(
        default_factory=list,
        description="List of fields in the glossary template",
    )


class GlossaryResponseVO(BaseModel):
    glossaries: List[GlossaryTemplateVO] = Field(default_factory=list, description="List of glossaries")
    total: int = Field(None, description="Total number of glossaries")
    page: int = Field(None, description="Page number")
    pageSize: int = Field(None, description="Page size")
