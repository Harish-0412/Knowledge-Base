import argparse
import textwrap

from answer_builder import AnswerBuilder
from query_router import QueryRoute
from search_service import MAX_SCORE_DROP, MIN_SIMILARITY, SearchService


ROUTE_CHOICES = {
    "auto": None,
    "domain": QueryRoute.DOMAIN.value,
    "compatibility": QueryRoute.COMPATIBILITY.value,
    "hybrid": QueryRoute.HYBRID.value,
}


def clipped(value, limit=900):
    value = value.strip()
    return value if len(value) <= limit else value[: limit - 3].rstrip() + "..."


def print_sources(answer):
    print("\nRetrieved Sources:")
    for index, source in enumerate(answer["retrieved_sources"], start=1):
        print(
            f"  {index}. {source['source_id']} | {source['collection']} | "
            f"score={source['score']:.6f} | source={source['source']}"
        )


def print_answer(answer, verify=False):
    print("\n" + "=" * 78)
    print(f"Question: {answer['question']}")
    print(f"Route: {answer['route']}")
    print("\nSummary:")
    print(textwrap.fill(clipped(answer["summary"]), width=100) if answer["summary"] else "No grounded answer found.")

    print("\nDetailed Explanation:")
    if answer["detailed_explanation"]:
        for index, detail in enumerate(answer["detailed_explanation"], start=1):
            print(f"  [{index}] {textwrap.fill(clipped(detail), width=96, subsequent_indent='      ')}")
    else:
        print("  No retrieved content was available.")

    print_sources(answer)
    confidence = answer["confidence"]
    print(f"\nConfidence: {confidence['level']} ({confidence['score']:.6f})")

    if verify:
        collections = sorted({source["collection"] for source in answer["retrieved_sources"]})
        print("\nVerification:")
        print(f"  Answered: {answer['answered']}")
        print(f"  Grounded only: {answer['grounded_only']}")
        print(f"  Sources present: {bool(answer['retrieved_sources'])}")
        print(f"  Collections represented: {', '.join(collections) if collections else 'none'}")
        print(f"  Relevance policy: score >= {MIN_SIMILARITY:.2f} and within {MAX_SCORE_DROP:.2f} of best match")
        print(f"  Search errors: {answer['errors'] or 'none'}")
    print("=" * 78)


def ask(service, builder, question, top_k, route, verify):
    response = service.search(question, top_k=top_k, route=route)
    answer = builder.build(question, response)
    print_answer(answer, verify=verify)
    return answer


def print_help():
    print(
        """
Commands:
  /help                         Show this help.
  /verify on|off                Toggle verification details.
  /topk N                       Set maximum retrieved sources (default 5).
  /route auto|domain|compatibility|hybrid
                                Override or restore automatic routing.
  /quit                         Exit.

Question families:
  DOMAIN         Definitions and purposes: BIOS, UEFI, TPM, drivers, operating systems.
  COMPATIBILITY Version constraints, requirements, conflicts, remediation, compliance.
  HYBRID         How a domain component affects compatibility or compliance.
""".strip()
    )


def interactive(service, builder, top_k, route, verify):
    print("Knowledge Base Retrieval Console")
    print("Answers are assembled only from Qdrant sources; no LLM is used.")
    print("Type /help for commands or /quit to exit.")
    while True:
        try:
            value = input("\nAsk> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            return
        if not value:
            continue
        if value == "/quit":
            return
        if value == "/help":
            print_help()
            continue
        if value.startswith("/verify "):
            setting = value.split(maxsplit=1)[1].lower()
            if setting not in {"on", "off"}:
                print("Use /verify on or /verify off")
            else:
                verify = setting == "on"
                print(f"Verification is now {'on' if verify else 'off'}.")
            continue
        if value.startswith("/topk "):
            try:
                requested = int(value.split(maxsplit=1)[1])
                if not 1 <= requested <= 20:
                    raise ValueError
                top_k = requested
                print(f"Top K is now {top_k}.")
            except ValueError:
                print("Top K must be an integer from 1 to 20.")
            continue
        if value.startswith("/route "):
            requested = value.split(maxsplit=1)[1].lower()
            if requested not in ROUTE_CHOICES:
                print("Route must be auto, domain, compatibility, or hybrid.")
            else:
                route = ROUTE_CHOICES[requested]
                print(f"Route is now {requested.upper()}.")
            continue
        try:
            ask(service, builder, value, top_k, route, verify)
        except Exception as exc:
            print(f"Search failed: {exc}")


def parse_args():
    parser = argparse.ArgumentParser(description="Ask grounded questions against the Domain and Compatibility Qdrant collections.")
    parser.add_argument("--question", "-q", help="Run one question and exit.")
    parser.add_argument("--top-k", type=int, default=5, choices=range(1, 21), metavar="1-20")
    parser.add_argument("--route", choices=ROUTE_CHOICES, default="auto")
    parser.add_argument("--verify", action="store_true", help="Show grounding and search verification details.")
    return parser.parse_args()


def main():
    args = parse_args()
    service = SearchService()
    builder = AnswerBuilder()
    route = ROUTE_CHOICES[args.route]
    if args.question:
        ask(service, builder, args.question, args.top_k, route, args.verify)
    else:
        interactive(service, builder, args.top_k, route, args.verify)


if __name__ == "__main__":
    main()
