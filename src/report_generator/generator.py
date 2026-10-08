from pathlib import Path

from .evidences import discover_evidences
from .metadata import load_test_metadata
from .powerpoint.presentation import (
    create_working_presentation,
    prepare_working_directory,
    prune_climatic_report_slides,
    publish_report,
    require_report_directory,
    validate_template_path,
)
from .sections.test_assembly import populate_test_assembly_images
from .sections.test_description import populate_test_description
from .sections.test_inputs import populate_test_inputs
from .sections.test_results import populate_test_results
from .sections.tested_parts import populate_tested_parts


def generate_climatic_report(test_root, template_path):
    test_root = Path(test_root)
    template_path = Path(template_path)
    metadata = load_test_metadata(test_root)
    evidence_discovery = discover_evidences(test_root)
    initial_image_paths = evidence_discovery.found_photo_paths_for_type("initial")
    report_directory = require_report_directory(test_root)
    working_directory = prepare_working_directory(test_root)
    validate_template_path(template_path)
    working_path = create_working_presentation(template_path, working_directory, metadata)
    populate_test_description(working_path, metadata)
    populate_tested_parts(working_path, metadata)
    populate_test_assembly_images(
        presentation_path=working_path,
        metadata=metadata,
        image_paths=initial_image_paths,
    )
    populate_test_inputs(working_path, metadata)
    populate_test_results(
        presentation_path=working_path,
        test_root=test_root,
        evidence_discovery=evidence_discovery,
    )
    prune_climatic_report_slides(working_path)
    return publish_report(working_path, report_directory)
