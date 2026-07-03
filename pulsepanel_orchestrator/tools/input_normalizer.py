"""Orchestrator wrapper for the canonical RAG input normalizer."""

from __future__ import annotations

from pydantic import ValidationError as PydanticValidationError

from pulsepanel_rag.input_normalizer import normalize_clinical_record

from ..base import BaseTool
from ..context import OrchestrationContext
from ..errors import ValidationError


class InputNormalizer(BaseTool):
    """Validate and normalize raw input through the shared RAG contract."""

    @property
    def name(self) -> str:
        return "InputNormalizer"

    def run(self, ctx: OrchestrationContext) -> OrchestrationContext:
        try:
            ctx.record = normalize_clinical_record(ctx.raw_input)
        except PydanticValidationError as exc:
            first_error = exc.errors()[0]
            field = ".".join(str(part) for part in first_error["loc"])
            message = f"ValidationError: {field}: {first_error['msg']}"
            raise ValidationError(message, field=field) from exc
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"ValidationError: {exc}") from exc
        return ctx
