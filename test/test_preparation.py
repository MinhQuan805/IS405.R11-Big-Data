import pandas as pd
from admission_core.features import major_mapping
from admission_core.preparation import normalize_title, resolve_major


def test_title_resolution_with_vietnamese_accents():
    assert normalize_title("Ngành Kế toán") == "nganh ke toan"
    assert resolve_major("Kế toán (Chất lượng cao)", [("Kế toán", "G"), ("Kiểm toán", "G")]) == (
        "Kế toán", "G", "exact_title")


def test_ambiguous_compound_title_stays_unresolved():
    assert resolve_major("Tài chính – Ngân hàng", [("Tài chính", "G"), ("Ngân hàng", "G")])[0] is None


def test_same_name_in_multiple_groups_stays_unresolved():
    assert resolve_major("Vật lý", [("Vật lý", "G1"), ("Vật lý", "G2")])[0] is None


def test_contextual_mapping_allows_reused_program_codes():
    frame = pd.DataFrame({"school_id": ["S1", "S2", "S1"], "score_year": [2024, 2024, 2025],
        "score_codes": ["P", "P", "P"], "major_name": ["A", "B", "C"], "major_group_name": ["G", "G", "G"]})
    assert len(major_mapping(frame)) == 3
