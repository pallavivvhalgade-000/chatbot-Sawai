from app.rag.retrieval import (
    retrieve_relevant_documents,
)


TESTS = [
    (
        "real_estate",
        "What help is available for buying property?",
    ),
    (
        "insurance",
        "Can you help with health insurance?",
    ),
    (
        "it_services",
        "Do you provide website development?",
    ),
]


for service, question in TESTS:

    print()
    print("=" * 70)
    print("SERVICE:", service)
    print("QUESTION:", question)
    print("=" * 70)


    result = (
        retrieve_relevant_documents(
            query=question,
            service=service,
        )
    )


    print(
        "Best relevance:",
        result.best_score,
    )

    print(
        "Accepted chunks:",
        len(result.matches),
    )

    print(
        "Rejected chunks:",
        result.rejected_count,
    )


    for index, (
        document,
        score,
    ) in enumerate(
        result.matches,
        start=1,
    ):
        print()
        print(
            f"Chunk {index}"
        )

        print(
            "Score:",
            round(score, 3),
        )

        print(
            "Service:",
            document.metadata.get(
                "service"
            ),
        )

        print(
            "File:",
            document.metadata.get(
                "filename"
            ),
        )

        print(
            "Text:",
            document.page_content[
                :250
            ].replace(
                "\n",
                " ",
            ),
        )