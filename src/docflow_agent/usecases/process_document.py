from docflow_agent.core.classify.document import classify_document
from docflow_agent.core.parse.excel import parse_excel_sheet_names
from docflow_agent.core.rules.accounting import validate_accounting_rule
from docflow_agent.core.rules.invoice import apply_invoice_rule
from docflow_agent.errors import UnsupportedDocumentError
from docflow_agent.outbound.files import load_spreadsheet
from docflow_agent.types.common import FileInfo
from docflow_agent.types.results import ProcessResult


def process_document(file_info: FileInfo) -> ProcessResult:
    document = load_spreadsheet(file_info)
    document_type = classify_document(document)

    if document_type != "excel_invoice":
        raise UnsupportedDocumentError(f"Unsupported document type: {document_type}")

    parsed_data = parse_excel_sheet_names(document)
    enriched_data = apply_invoice_rule(parsed_data)
    validation_errors = validate_accounting_rule(enriched_data)

    return ProcessResult(
        document_type=document_type,
        success=not validation_errors,
        parsed_data=enriched_data,
        messages=validation_errors or ["Document processed successfully."],
    )
