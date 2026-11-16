"""Selection of evidence photos for Test Assembly and Test Results."""

import json
import tempfile
import unittest
from pathlib import Path

from pptx import Presentation
from pptx.util import Cm

from project_fixtures import add_evidence, write_image, write_json, evidence_descriptor
from src.report_generator.evidence_photos import (
    ASSEMBLY_MAX_PHOTOS,
    ASSEMBLY_SECTION,
    RESULTS_SECTION,
    EvidencePhotoLimitError,
    EvidencePhotoNotFoundError,
    EvidencePhotoPathError,
    EvidencePhotoSectionError,
    EvidencePhotoUnsupportedError,
    evidence_photo_relative_path,
    normalize_evidence_photo_path,
    photos_by_evidence,
    resolve_evidence_photo,
    select_evidence_photos,
    selectable_evidence_photos,
)
from src.report_generator.evidences import discover_evidences
from src.report_generator.generator import resolve_evidence_photo_selection


def add_typed_evidence(root, folder, *, sequence, photos, type_, create=True, notes=""):
    directory = add_evidence(root, folder, sequence=sequence, photos=photos, create_photos=create)
    descriptor = json.loads((directory / "evidence.json").read_text(encoding="utf-8"))
    descriptor["type"] = type_
    descriptor["notes"] = notes
    write_json(directory / "evidence.json", descriptor)
    return directory


class EvidencePhotoSelectionTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        (self.root / "02_Evidences").mkdir()
        add_typed_evidence(self.root, "00_Initial", sequence=0, type_="initial",
                           photos=[f"i{n}.jpg" for n in range(1, 7)])
        add_typed_evidence(self.root, "02_Final", sequence=2, type_="final",
                           photos=["f1.jpg", "f2.png"])
        add_typed_evidence(self.root, "01_Incident", sequence=1, type_="incident",
                           photos=["a1.jpg", "a2.jpg", "a3.jpg"])
        self.discovery = discover_evidences(self.root)

    def tearDown(self):
        self._tmp.cleanup()

    def paths(self, photos):
        return [p.relative_path for p in photos]

    def test_sections_split_by_evidence_type(self):
        assembly = selectable_evidence_photos(self.discovery, ASSEMBLY_SECTION)
        results = selectable_evidence_photos(self.discovery, RESULTS_SECTION)
        self.assertEqual(len(assembly), 6)
        self.assertTrue(all(p.section == ASSEMBLY_SECTION for p in assembly))
        self.assertEqual(
            self.paths(results),
            [
                "02_Evidences/01_Incident/a1.jpg",
                "02_Evidences/01_Incident/a2.jpg",
                "02_Evidences/01_Incident/a3.jpg",
                "02_Evidences/02_Final/f1.jpg",
                "02_Evidences/02_Final/f2.png",
            ],
        )

    def test_none_uses_first_four_assembly_and_all_results(self):
        assembly, results = resolve_evidence_photo_selection(self.discovery, None, None)
        self.assertEqual(self.paths(assembly), [f"02_Evidences/00_Initial/i{n}.jpg" for n in range(1, 5)])
        self.assertEqual(len(results), 5)

    def test_empty_lists_select_nothing(self):
        assembly, results = resolve_evidence_photo_selection(self.discovery, [], [])
        self.assertEqual((assembly, results), ([], []))

    def test_explicit_selection_keeps_automatic_order(self):
        selected = [
            "02_Evidences/02_Final/f2.png",
            "02_Evidences\\01_Incident\\a3.jpg",
            "02_Evidences/01_Incident/a1.jpg",
        ]
        results = select_evidence_photos(self.discovery, RESULTS_SECTION, selected)
        self.assertEqual(
            self.paths(results),
            ["02_Evidences/01_Incident/a1.jpg", "02_Evidences/01_Incident/a3.jpg", "02_Evidences/02_Final/f2.png"],
        )

    def test_results_have_no_selection_limit(self):
        add_typed_evidence(self.root, "03_Many", sequence=3, type_="other",
                           photos=[f"m{n:02d}.jpg" for n in range(30)])
        discovery = discover_evidences(self.root)
        everything = [p.relative_path for p in selectable_evidence_photos(discovery, RESULTS_SECTION)]
        self.assertEqual(len(select_evidence_photos(discovery, RESULTS_SECTION, everything)), 35)

    def test_assembly_accepts_four_and_rejects_five(self):
        four = [f"02_Evidences/00_Initial/i{n}.jpg" for n in (6, 2, 5, 1)]
        self.assertEqual(
            self.paths(select_evidence_photos(self.discovery, ASSEMBLY_SECTION, four)),
            [f"02_Evidences/00_Initial/i{n}.jpg" for n in (1, 2, 5, 6)],
        )
        with self.assertRaises(EvidencePhotoLimitError):
            select_evidence_photos(
                self.discovery, ASSEMBLY_SECTION,
                [f"02_Evidences/00_Initial/i{n}.jpg" for n in range(1, 6)],
            )
        self.assertEqual(ASSEMBLY_MAX_PHOTOS, 4)

    def test_photo_of_the_other_section_is_rejected(self):
        with self.assertRaises(EvidencePhotoSectionError):
            select_evidence_photos(self.discovery, ASSEMBLY_SECTION, ["02_Evidences/02_Final/f1.jpg"])
        with self.assertRaises(EvidencePhotoSectionError):
            select_evidence_photos(self.discovery, RESULTS_SECTION, ["02_Evidences/00_Initial/i1.jpg"])

    def test_duplicates_are_rejected(self):
        with self.assertRaises(EvidencePhotoPathError):
            select_evidence_photos(
                self.discovery, RESULTS_SECTION,
                ["02_Evidences/02_Final/f1.jpg", "02_Evidences/02_Final/f1.jpg"],
            )

    def test_invalid_paths_are_rejected(self):
        for bad in ["", "/abs/02_Evidences/x/y.jpg", "C:/02_Evidences/a/b.jpg",
                    "02_Evidences/../02_Final/f1.jpg", "02_Evidences/f1.jpg",
                    "04_Report/_RenderedAssets/a.png", "02_Evidences/02_Final/./f1.jpg", None, 5]:
            with self.subTest(bad=bad), self.assertRaises(EvidencePhotoPathError):
                normalize_evidence_photo_path(bad)
        with self.assertRaises(EvidencePhotoPathError):
            select_evidence_photos(self.discovery, RESULTS_SECTION, "02_Evidences/02_Final/f1.jpg")

    def test_undeclared_missing_and_unsupported_photos(self):
        (self.root / "02_Evidences" / "02_Final" / "loose.jpg").write_bytes(b"x")
        with self.assertRaises(EvidencePhotoNotFoundError):
            resolve_evidence_photo(self.discovery, "02_Evidences/02_Final/loose.jpg")
        add_typed_evidence(self.root, "04_Missing", sequence=4, type_="other", photos=["gone.jpg"], create=False)
        directory = add_typed_evidence(self.root, "05_Odd", sequence=5, type_="other", photos=["clip.heic"], create=False)
        (directory / "clip.heic").write_bytes(b"x")
        discovery = discover_evidences(self.root)
        with self.assertRaises(EvidencePhotoNotFoundError):
            resolve_evidence_photo(discovery, "02_Evidences/04_Missing/gone.jpg")
        with self.assertRaises(EvidencePhotoUnsupportedError):
            resolve_evidence_photo(discovery, "02_Evidences/05_Odd/clip.heic")
        self.assertNotIn(
            "02_Evidences/05_Odd/clip.heic",
            [p.relative_path for p in selectable_evidence_photos(discovery)],
        )

    def test_case_insensitive_match_is_accepted(self):
        photo = resolve_evidence_photo(self.discovery, "02_evidences/02_final/F1.JPG".replace("02_evidences", "02_Evidences"))
        self.assertEqual(photo.relative_path, "02_Evidences/02_Final/f1.jpg")

    def test_photos_grouped_by_evidence(self):
        results = select_evidence_photos(self.discovery, RESULTS_SECTION, None)
        grouped = photos_by_evidence(results)
        self.assertEqual(list(grouped), [results[0].evidence.descriptor_path, results[3].evidence.descriptor_path])
        self.assertEqual([p.name for p in grouped[results[0].evidence.descriptor_path]], ["a1.jpg", "a2.jpg", "a3.jpg"])


if __name__ == "__main__":
    unittest.main()


from unittest.mock import MagicMock, patch

from src.report_generator.evidences import Evidence, EvidenceDiscovery, EvidencePhoto
from src.report_generator.sections import test_assembly, test_results


def _evidence(folder, type_, sequence, names, tmp):
    directory = tmp / "02_Evidences" / folder
    photos = []
    for name in names:
        write_image(directory / name)
        photos.append(EvidencePhoto(saved_name=name, path=directory / name, found=True))
    return Evidence(directory=directory, descriptor_path=directory / "evidence.json",
                    folder_name=folder, type=type_, title=folder, sequence=sequence, photos=photos)


class EvidencePaginationTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def run_results(self, evidences, selection):
        discovery = EvidenceDiscovery(directory=self.tmp / "02_Evidences", found=True, evidences=evidences)
        first = object()
        continuations = []

        def new_slide(**kwargs):
            slide = object(); continuations.append((slide, kwargs)); return slide

        with patch.object(test_results, "Presentation") as presentation_mock, \
                patch.object(test_results, "find_slide_in_section", return_value=first), \
                patch.object(test_results, "clear_slide_body"), \
                patch.object(test_results, "create_continuation_slide", side_effect=new_slide), \
                patch.object(test_results, "populate_evidence_slide") as populate:
            test_results.populate_test_results(
                presentation_path=self.tmp / "r.pptx", test_root=self.tmp,
                evidence_discovery=discovery, result_image_paths=[],
                evidence_photo_paths=selection,
            )
        return populate.call_args_list, continuations

    def test_two_photos_per_slide_with_continuations(self):
        for count, expected_slides in [(0, 1), (1, 1), (2, 1), (3, 2), (5, 3), (9, 5)]:
            with self.subTest(count=count):
                evidence = _evidence(f"01_E{count}", "incident", 1, [f"p{n}.jpg" for n in range(count)], self.tmp)
                calls, continuations = self.run_results([evidence], None)
                self.assertEqual(len(calls), expected_slides)
                self.assertEqual(len(continuations), expected_slides - 1)
                groups = [c.kwargs["image_paths"] for c in calls]
                self.assertTrue(all(len(g) <= 2 for g in groups))
                self.assertEqual([p for g in groups for p in g], [p.path for p in evidence.photos])
                self.assertEqual([c.kwargs["continuation"] for c in calls], [False] + [True] * (expected_slides - 1))

    def test_evidence_without_selected_photos_keeps_its_slide(self):
        first = _evidence("01_A", "incident", 1, ["a.jpg", "b.jpg"], self.tmp)
        second = _evidence("02_B", "final", 2, ["c.jpg"], self.tmp)
        initial = _evidence("00_I", "initial", 0, ["i.jpg"], self.tmp)
        calls, _ = self.run_results([initial, first, second], {second.descriptor_path: [second.photos[0].path]})
        self.assertEqual([c.kwargs["evidence"].folder_name for c in calls], ["01_A", "02_B"])
        self.assertEqual(calls[0].kwargs["image_paths"], [])
        self.assertEqual(calls[1].kwargs["image_paths"], [second.photos[0].path])

    def test_evidence_slide_rejects_more_than_two_photos(self):
        evidence = _evidence("01_A", "incident", 1, ["a.jpg", "b.jpg", "c.jpg"], self.tmp)
        with self.assertRaises(ValueError):
            test_results.populate_evidence_slide(MagicMock(), evidence, [p.path for p in evidence.photos])

    def run_assembly(self, count, equipment=0):
        paths = [write_image(self.tmp / "02_Evidences" / "00_I" / f"i{n}.jpg") for n in range(count)]
        first = MagicMock(name="first")
        created = []

        def new_slide(**kwargs):
            slide = MagicMock(name=f"cont{len(created)}"); created.append((slide, kwargs)); return slide

        metadata = {"equipment": [{"equipment_used": f"E{n}", "equipment_code": str(n)} for n in range(equipment)]}
        with patch.object(test_assembly, "Presentation"), \
                patch.object(test_assembly, "find_slide_in_section", return_value=first), \
                patch.object(test_assembly, "clear_test_assembly_content"), \
                patch.object(test_assembly, "create_continuation_slide", side_effect=new_slide), \
                patch.object(test_assembly, "populate_equipment_continuation_slide") as equipment_slide, \
                patch.object(test_assembly, "add_contained_image") as add_image:
            test_assembly.populate_test_assembly_images(self.tmp / "r.pptx", metadata, paths)
        return paths, first, created, add_image.call_args_list, equipment_slide

    def test_assembly_places_two_photos_per_slide(self):
        for count, continuations in [(0, 0), (1, 0), (2, 0), (3, 1), (4, 1)]:
            with self.subTest(count=count):
                paths, first, created, images, _ = self.run_assembly(count)
                self.assertEqual(len(created), continuations + 1)
                self.assertEqual([c.kwargs["image_path"] for c in images], paths)
                self.assertEqual([c.kwargs["slide"] for c in images][:2], [first] * min(count, 2))
                if continuations:
                    self.assertEqual(created[0][1]["title"], "2. Test Assembly (cont.)")
                    self.assertIs(created[0][1]["reference_slide"], first)
                    self.assertTrue(all(c.kwargs["slide"] is created[0][0] for c in images[2:]))

    def test_photo_continuation_comes_before_equipment_continuations(self):
        _, first, created, _, equipment_slide = self.run_assembly(4, equipment=6)
        self.assertEqual(len(created), 3)
        self.assertIs(created[1][1]["reference_slide"], created[0][0])
        self.assertIs(equipment_slide.call_args.kwargs["slide"], created[1][0])

    def test_assembly_rejects_more_than_four_photos(self):
        with self.assertRaises(ValueError):
            self.run_assembly(5)
