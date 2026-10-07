from pathlib import Path


DEFAULT_TEST_ROOT_PROMPT = (
    "Enter the full path to the test folder: "
)


def prompt_test_root(message: str = DEFAULT_TEST_ROOT_PROMPT) -> Path:
    """Request and normalize a test folder from the console."""
    test_root_text = input(message).strip().strip('"')

    if not test_root_text:
        raise ValueError("No test folder path was provided.")

    return Path(test_root_text).expanduser().resolve()
