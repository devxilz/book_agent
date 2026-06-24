from langchain_text_splitters import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=3000,
    chunk_overlap=200,
    separators=[
        "\n## ",
        "\n# ",
        "```",
        "\n\n",
        "\n",
        " ",
        ""
    ]
)

def split_text(text):
    return splitter.split_text(text)