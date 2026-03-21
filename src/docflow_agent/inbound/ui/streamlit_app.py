import streamlit as st

from docflow_agent.types.common import FileInfo
from docflow_agent.usecases.process_document import process_document


def main() -> None:
    st.title("Document Processing Demo")
    uploaded_file = st.file_uploader("Upload an Excel invoice", type=["xlsx", "xls"])

    if uploaded_file is None:
        return

    result = process_document(
        FileInfo(
            name=uploaded_file.name,
            path=uploaded_file.name,
            content_type=uploaded_file.type
            or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    )

    st.json(
        {
            "document_type": result.document_type,
            "success": result.success,
            "parsed_data": result.parsed_data,
            "messages": result.messages,
        }
    )


if __name__ == "__main__":
    main()
