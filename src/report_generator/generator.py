from pathlib import Path
from .metadata import load_test_metadata
from .powerpoint.presentation import create_working_presentation, prepare_working_directory, publish_report, require_report_directory, validate_template_path
from .sections.test_assembly import populate_test_assembly_images
from .sections.test_description import populate_test_description
from .sections.test_inputs import populate_test_inputs
from .sections.test_results import populate_test_results
from .sections.tested_parts import populate_tested_parts

def generate_climatic_report(test_root, template_path):
    """
    Generate the PowerPoint report from ``04_Report/test_metadata.json``.

    The metadata is only read: it is never regenerated, and the Excel
    inputs are never opened. The presentation is assembled in
    ``04_Report/_Working`` and the finished file is moved to
    ``04_Report``. Profile charts are native PowerPoint charts built
    from the profile points stored in the metadata.
    """
    test_root = Path(test_root)
    template_path = Path(template_path)
    metadata = load_test_metadata(test_root)
    report_directory = require_report_directory(test_root)
    working_directory = prepare_working_directory(test_root)
    validate_template_path(template_path)
    working_path = create_working_presentation(template_path, working_directory, metadata)
    populate_test_description(working_path, metadata)
    populate_tested_parts(working_path, metadata)
    populate_test_assembly_images(working_path, test_root, metadata)
    populate_test_inputs(working_path, metadata)
    populate_test_results(working_path, test_root)
    return publish_report(working_path, report_directory)
