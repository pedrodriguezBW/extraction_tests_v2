from config import POWERPOINT_TEMPLATE_PATH
from src.report_generator import generate_climatic_report
from src.report_generator.cli import prompt_test_root
from src.report_generator.paths import metadata_path


def main():
    """
    Generate the report from the existing agent-generated metadata.

    test_metadata.json is produced by an external agent and is only
    read here. The Excel inputs are never opened.
    """
    test_root = prompt_test_root(
        "Test folder path: "
    )

    output_path = generate_climatic_report(
        test_root=test_root,
        template_path=POWERPOINT_TEMPLATE_PATH,
    )

    print(f"Metadata used: {metadata_path(test_root)}")
    print(f"PowerPoint created: {output_path}")


if __name__ == "__main__":
    main()
