from config import POWERPOINT_TEMPLATE_PATH
from src.report_generator import generate_climatic_report
from src.report_generator.cli import prompt_test_root


def main():
    test_root = prompt_test_root(
        "Test folder path: "
    )

    output_path = generate_climatic_report(
        test_root=test_root,
        template_path=POWERPOINT_TEMPLATE_PATH,
    )

    print(f"PowerPoint created: {output_path}")


if __name__ == "__main__":
    main()
