import json
from pathlib import Path

from app.services.career_matching import INDUSTRIES, ROC_WEIGHTS


CATALOG_PATH = Path(__file__).resolve().parents[2] / "data" / "career-catalog.v1.json"


def test_draft_catalog_covers_all_live_codes_without_changing_matching_priorities():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    groups = {item["code"]: item for item in catalog["groups"]}

    assert catalog["matchingFormulaChanged"] is False
    assert catalog["status"] == "draft_for_domain_review"
    assert set(groups) == {item.code for item in INDUSTRIES}
    for industry in INDUSTRIES:
        record = groups[industry.code]
        assert record["name"] == industry.name
        assert record["matchingCriteriaPriority"] == list(industry.priority)
        assert record["currentRocWeights"] == {
            criterion: ROC_WEIGHTS[index]
            for index, criterion in enumerate(industry.priority)
        }


def test_new_vocational_program_mappings_are_explicitly_unverified():
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    programs = catalog["newVocationalPrograms"]

    assert len(programs) == 12
    assert all(item["mappingStatus"] == "proposed_only_unverified" for item in programs)
    assert all(item["source"] == "VET-77-2026" for item in programs)
