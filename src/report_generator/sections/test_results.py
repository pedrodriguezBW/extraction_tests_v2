from __future__ import annotations
from pathlib import Path
from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR
from pptx.util import Cm, Pt
from ..evidences import Evidence, EvidenceDiscovery, discover_evidences
from ..powerpoint.images import add_contained_image, find_test_result_charts
from ..powerpoint.layout import add_section_header
from ..powerpoint.navigation import chunk_items, clear_slide_body, create_continuation_slide, find_slide_in_section
from ..powerpoint.styles import COLOR_GRAY, COLOR_NAVY, CONTENT_LEFT_CM, CONTENT_WIDTH_CM, FONT_FAMILY, FONT_SIZE_LABEL_PT, FONT_SIZE_VALUE_PT, RESULT_HORIZONTAL_GAP_CM, RESULT_VERTICAL_GAP_CM, SINGLE_CHART_HEIGHT_CM, SINGLE_CHART_WIDTH_CM

def add_test_result_image(slide,image_path,left_cm,top_cm,width_cm,height_cm):
    add_contained_image(slide=slide,image_path=image_path,left_cm=left_cm,top_cm=top_cm,width_cm=width_cm,height_cm=height_cm)

def populate_test_results_slide(slide,image_paths):
    count=len(image_paths)
    if not count:return
    top=4.10;height=12.30
    if count==1:
        width=SINGLE_CHART_WIDTH_CM;h=SINGLE_CHART_HEIGHT_CM
        add_test_result_image(slide,image_paths[0],CONTENT_LEFT_CM+(CONTENT_WIDTH_CM-width)/2,top+(height-h)/2,width,h);return
    if count==2:
        width=(CONTENT_WIDTH_CM-RESULT_HORIZONTAL_GAP_CM)/2;h=8.50;y=top+(height-h)/2
        for i,path in enumerate(image_paths):add_test_result_image(slide,path,CONTENT_LEFT_CM+i*(width+RESULT_HORIZONTAL_GAP_CM),y,width,h)
        return
    width=(CONTENT_WIDTH_CM-RESULT_HORIZONTAL_GAP_CM)/2;h=(height-RESULT_VERTICAL_GAP_CM)/2
    pos=[(CONTENT_LEFT_CM,top),(CONTENT_LEFT_CM+width+RESULT_HORIZONTAL_GAP_CM,top),(CONTENT_LEFT_CM,top+h+RESULT_VERTICAL_GAP_CM),(CONTENT_LEFT_CM+width+RESULT_HORIZONTAL_GAP_CM,top+h+RESULT_VERTICAL_GAP_CM)]
    for path,(x,y) in zip(image_paths,pos):add_test_result_image(slide,path,x,y,width,h)

def _reference_text(evidence):
    value=(evidence.reference_value or "").strip();kind=(evidence.reference_type or "").strip()
    if not value:return ""
    if not kind or kind.casefold()=="none":return value
    return f"{value} {kind}"

def _event_label(evidence):
    return (evidence.type or "").strip().replace("_"," ").title()

def _add_evidence_text(slide,evidence):
    add_section_header(slide=slide,title=(evidence.title or evidence.folder_name).strip(),left_cm=CONTENT_LEFT_CM,top_cm=4.05,width_cm=CONTENT_WIDTH_CM)
    parts=[x for x in (_event_label(evidence),_reference_text(evidence)) if x]
    if parts:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(4.85),Cm(CONTENT_WIDTH_CM),Cm(.55));f=box.text_frame;f.clear();f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;p=f.paragraphs[0];p.text=" | ".join(parts);p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_LABEL_PT);p.font.bold=True;p.font.color.rgb=COLOR_GRAY
    notes=(evidence.notes or "").strip()
    if notes:
        box=slide.shapes.add_textbox(Cm(CONTENT_LEFT_CM),Cm(5.45),Cm(CONTENT_WIDTH_CM),Cm(1.10));f=box.text_frame;f.clear();f.word_wrap=True;f.margin_left=f.margin_right=f.margin_top=f.margin_bottom=0;f.vertical_anchor=MSO_ANCHOR.TOP;p=f.paragraphs[0];p.text=notes;p.font.name=FONT_FAMILY;p.font.size=Pt(FONT_SIZE_VALUE_PT);p.font.color.rgb=COLOR_NAVY

def populate_evidence_slide(slide,evidence,image_paths):
    _add_evidence_text(slide,evidence)
    if not image_paths:return
    top=6.75;h=9.25
    if len(image_paths)==1:
        width=20.;add_test_result_image(slide,image_paths[0],CONTENT_LEFT_CM+(CONTENT_WIDTH_CM-width)/2,top,width,h);return
    width=(CONTENT_WIDTH_CM-RESULT_HORIZONTAL_GAP_CM)/2
    for i,path in enumerate(image_paths[:2]):add_test_result_image(slide,path,CONTENT_LEFT_CM+i*(width+RESULT_HORIZONTAL_GAP_CM),top,width,h)

def _result_evidences(discovery):
    return [e for e in discovery.evidences if (e.type or "").strip().casefold()!="initial"]

def populate_test_results(presentation_path,test_root,evidence_discovery=None):
    presentation_path=Path(presentation_path);test_root=Path(test_root);presentation=Presentation(presentation_path)
    first=find_slide_in_section(presentation=presentation,section_title="TEST A",slide_title="4. Test Results")
    clear_slide_body(slide = first,expected_title="4. Test Results")
    charts=find_test_result_charts(test_root=test_root);discovery=evidence_discovery or discover_evidences(test_root);events=_result_evidences(discovery)
    previous=first;used=False
    for group in chunk_items(items=charts,chunk_size=4):
        slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_test_results_slide(slide = slide, image_paths = group);previous=slide
    for evidence in events:
        groups=chunk_items(items=[p.path for p in evidence.found_photos],chunk_size=2) or [[]]
        for group in groups:
            slide=first if not used else create_continuation_slide(presentation=presentation,reference_slide=previous,title="4. Test Results (cont.)");used=True;populate_evidence_slide(slide = slide, evidence = evidence, image_paths = group);previous=slide
    presentation.save(presentation_path)
