from app.rag.answering import (
    answer_knowledge_question,
)


def main() -> None:
    print()
    print("Sawai Associates RAG Test")
    print("--------------------------")

    question = input(
        "Enter a question: "
    ).strip()

    if not question:
        print("No question entered.")
        return

    result = answer_knowledge_question(
        question
    )

    print()
    print("ANSWER")
    print("------")
    print(result.answer)

    print()
    print(
        f"Grounded: {result.grounded}"
    )

    print(
        "Handoff recommended: "
        f"{result.handoff_recommended}"
    )

    print(
        f"Reason: {result.reason}"
    )

    print()
    print("SOURCES")
    print("-------")

    if not result.sources:
        print("No sources.")

    else:
        for source in result.sources:
            print(source)


if __name__ == "__main__":
    main()