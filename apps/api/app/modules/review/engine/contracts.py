from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictReviewSchema(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ReviewLocation(StrictReviewSchema):
    paragraph_index: int | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    quoted_text: str | None = None


class ReviewIssue(StrictReviewSchema):
    category: Literal[
        "plot_inconsistency",
        "character_inconsistency",
        "style_deviation",
        "banned_words",
        "ai_flavor",
        "logic_error",
        "quality_low",
        "other",
    ]
    severity: Literal["critical", "major", "minor", "suggestion"]
    location: ReviewLocation | None = None
    description: str
    suggested_fix: str | None = None
    evidence: str | None = None


class ReviewResult(StrictReviewSchema):
    reviewer_id: str
    reviewer_name: str
    status: Literal["passed", "failed", "warning"]
    score: float | None = Field(default=None, ge=0, le=100)
    issues: list[ReviewIssue] = Field(default_factory=list)
    summary: str
    execution_time_ms: int = Field(ge=0)
    tokens_used: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_status_semantics(self) -> "ReviewResult":
        severities = {issue.severity for issue in self.issues}
        has_blocking = any(severity in {"critical", "major"} for severity in severities)
        if self.status == "passed" and self.issues:
            raise ValueError("passed review result cannot contain issues")
        if self.status == "warning":
            if not self.issues:
                raise ValueError("warning review result must contain issues")
            if has_blocking:
                raise ValueError("warning review result cannot contain critical or major issues")
        if self.status == "failed":
            if not self.issues:
                raise ValueError("failed review result must contain issues")
            if not has_blocking:
                raise ValueError("failed review result must contain at least one critical or major issue")
        return self


class ReviewExecutionFailure(StrictReviewSchema):
    reviewer_id: str
    reviewer_name: str
    error_type: Literal["timeout", "invalid_result", "execution_error"]
    message: str
    execution_time_ms: int = Field(ge=0)


class AggregatedReviewResult(StrictReviewSchema):
    overall_status: Literal["passed", "failed"]
    results: list[ReviewResult] = Field(default_factory=list)
    execution_failures: list[ReviewExecutionFailure] = Field(default_factory=list)
    total_issues: int = Field(default=0, ge=0)
    critical_count: int = Field(default=0, ge=0)
    major_count: int = Field(default=0, ge=0)
    minor_count: int = Field(default=0, ge=0)
    pass_rule: Literal["all_pass", "majority_pass", "no_critical"] = "no_critical"

    @model_validator(mode="after")
    def validate_aggregate_semantics(self) -> "AggregatedReviewResult":
        if not self.results and not self.execution_failures:
            raise ValueError("aggregated review result must contain results or execution_failures")
        derived_total = sum(len(result.issues) for result in self.results)
        if self.total_issues != derived_total:
            raise ValueError("total_issues must match derived issue count")
        derived_counts = {"critical": 0, "major": 0, "minor": 0}
        for result in self.results:
            for issue in result.issues:
                if issue.severity in derived_counts:
                    derived_counts[issue.severity] += 1
        if self.critical_count != derived_counts["critical"]:
            raise ValueError("critical_count must match derived issue count")
        if self.major_count != derived_counts["major"]:
            raise ValueError("major_count must match derived issue count")
        if self.minor_count != derived_counts["minor"]:
            raise ValueError("minor_count must match derived issue count")
        if self.execution_failures and self.overall_status != "failed":
            raise ValueError("overall_status must be failed when execution_failures exist")
        return self
