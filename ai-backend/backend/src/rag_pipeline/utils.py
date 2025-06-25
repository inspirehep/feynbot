def format_docs(docs):
    return f"\n{'-' * 10}\n".join(
        [
            f"Document {i + 1}: \n"
            + f"Control Number: {d.metadata['control_number']}\n\n"
            + str(d.page_content)
            for i, d in enumerate(docs)
        ]
    )
