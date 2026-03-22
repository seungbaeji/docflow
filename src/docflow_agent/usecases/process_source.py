from dataclasses import asdict

from docflow_agent.core.analyze.invoice import analyze_invoice_bundle
from docflow_agent.core.category.invoice import categorize_excel_units
from docflow_agent.core.combine.invoice import combine_invoice_units
from docflow_agent.core.parse.excel import parse_excel_units
from docflow_agent.core.rules.accounting import validate_accounting_rule
from docflow_agent.core.rules.invoice import apply_invoice_rule
from docflow_agent.core.source_kind.detect import detect_source_kind
from docflow_agent.errors import UnsupportedCategoryError, UnsupportedSourceKindError
from docflow_agent.outbound.files import load_spreadsheet_source
from docflow_agent.types.results import ProcessResult
from docflow_agent.types.source import SourceRef


def process_source(source_ref: SourceRef) -> ProcessResult:
    source = load_spreadsheet_source(source_ref)
    source_kind = detect_source_kind(source)

    if source_kind != "excel":
        raise UnsupportedSourceKindError(source_kind)

    units = parse_excel_units(source)
    category = categorize_excel_units(units)

    if category != "invoice":
        raise UnsupportedCategoryError(category)

    bundle = combine_invoice_units(source=source, units=units, category=category)
    bundle = apply_invoice_rule(bundle)
    analysis = analyze_invoice_bundle(bundle)
    validation_errors = validate_accounting_rule(bundle)

    return ProcessResult(
        source_kind=source_kind,
        category=category,
        success=not validation_errors,
        unit_count=len(units),
        bundle_data={
            "bundle": asdict(bundle),
            "analysis": analysis,
        },
        messages=validation_errors or ["Source processed successfully."],
    )
