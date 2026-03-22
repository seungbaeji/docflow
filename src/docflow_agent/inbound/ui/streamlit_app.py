import streamlit as st

from docflow_agent.errors import DocflowError
from docflow_agent.types.source import SourceRef
from docflow_agent.usecases.process_source import process_source


def main() -> None:
    st.title("Source Processing Demo")
    uploaded_file = st.file_uploader("Upload an Excel source", type=["xlsx", "xls"])

    if uploaded_file is None:
        return

    try:
        result = process_source(
            SourceRef(
                name=uploaded_file.name,
                location=uploaded_file.name,
                content_type=uploaded_file.type
                or "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                source_system="upload",
            )
        )
    except DocflowError as exc:
        st.error(str(exc))
        return

    st.json(
        {
            "source_kind": result.source_kind,
            "category": result.category,
            "success": result.success,
            "unit_count": result.unit_count,
            "bundle_data": result.bundle_data,
            "messages": result.messages,
        }
    )


if __name__ == "__main__":
    main()
