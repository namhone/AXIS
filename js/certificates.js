(function (global) {
  'use strict';

  var LEVELS = {
    VSTEP: [['Bậc 3 / B1', 'VSTEP_B1'], ['Bậc 4 / B2', 'VSTEP_B2'], ['Bậc 5 / C1', 'VSTEP_C1'], ['Bậc 6 / C2', 'VSTEP_C2']],
    CAMBRIDGE: [['PET / B1', 'CAMBRIDGE_B1'], ['FCE / B2', 'CAMBRIDGE_B2'], ['CAE / C1', 'CAMBRIDGE_C1'], ['CPE / C2', 'CAMBRIDGE_C2']],
    APTIS: [['B1', 'APTIS_B1'], ['B2', 'APTIS_B2'], ['C1', 'APTIS_C1'], ['C2', 'APTIS_C2']],
    HSK: [['HSK 3', 'HSK_3'], ['HSK 4', 'HSK_4'], ['HSK 5', 'HSK_5'], ['HSK 6', 'HSK_6']],
    TOCFL: [['Cấp 3 / B1', 'TOCFL_B1'], ['Cấp 4 / B2', 'TOCFL_B2'], ['Cấp 5 / C1', 'TOCFL_C1'], ['Cấp 6 / C2', 'TOCFL_C2']],
    JLPT: [['N4', 'N4'], ['N3', 'N3'], ['N2', 'N2'], ['N1', 'N1']],
    DELF: [['DELF B1', 'DELF_B1'], ['DELF B2', 'DELF_B2'], ['DALF C1', 'DALF_C1'], ['DALF C2', 'DALF_C2']],
    TOPIK: [['TOPIK 3', 'TOPIK_3'], ['TOPIK 4', 'TOPIK_4'], ['TOPIK 5', 'TOPIK_5'], ['TOPIK 6', 'TOPIK_6']],
    GOETHE: [['B1 / TDN 3', 'GOETHE_B1'], ['B2 / TDN 4', 'GOETHE_B2'], ['C1-C2 / TDN 5', 'GOETHE_C1']],
    DSD: [['DSD I / B1', 'DSD_B1'], ['DSD II / B2', 'DSD_B2'], ['DSD II / C1', 'DSD_C1']],
    TORFL: [['TRKI 1 / B1', 'TORFL_B1'], ['TRKI 2 / B2', 'TORFL_B2'], ['TRKI 3-4 / C1-C2', 'TORFL_C1']]
  };
  var LANGUAGES = [
    { value: 'en', label: '🇬🇧 Tiếng Anh', certificates: [['IELTS Academic', 'IELTS', 'number'], ['TOEFL iBT', 'TOEFL_IBT', 'number'], ['TOEFL ITP', 'TOEFL_ITP', 'number'], ['VSTEP', 'VSTEP', 'level'], ['TOEIC (4 kỹ năng)', 'TOEIC', 'number'], ['Cambridge English', 'CAMBRIDGE', 'level'], ['PTE Academic', 'PTE', 'number'], ['Aptis ESOL', 'APTIS', 'level'], ['SAT', 'SAT', 'number'], ['ACT', 'ACT', 'number']] },
    { value: 'zh', label: '🇨🇳 Tiếng Trung', certificates: [['HSK (kèm HSKK)', 'HSK', 'level'], ['TOCFL', 'TOCFL', 'level']] },
    { value: 'ja', label: '🇯🇵 Tiếng Nhật', certificates: [['JLPT', 'JLPT', 'level'], ['NAT-TEST', 'NAT_TEST', 'number'], ['BJT', 'BJT', 'number']] },
    { value: 'fr', label: '🇫🇷 Tiếng Pháp', certificates: [['DELF / DALF', 'DELF', 'level'], ['TCF', 'TCF', 'number']] },
    { value: 'ko', label: '🇰🇷 Tiếng Hàn', certificates: [['TOPIK', 'TOPIK', 'level']] },
    { value: 'de', label: '🇩🇪 Tiếng Đức', certificates: [['Goethe-Zertifikat / TestDaF', 'GOETHE', 'level'], ['DSD', 'DSD', 'level']] },
    { value: 'ru', label: '🇷🇺 Tiếng Nga', certificates: [['TORFL / TRKI', 'TORFL', 'level']] }
  ];
  var NUMERIC = {
    IELTS: [0, 9, 0.5, 'Nhập điểm Overall (Ví dụ: 6.5)'],
    TOEFL_IBT: [0, 120, 1, 'Nhập điểm TOEFL iBT'],
    TOEFL_ITP: [310, 677, 1, 'Nhập điểm TOEFL ITP'],
    TOEIC: [10, 990, 5, 'Nhập điểm TOEIC'],
    PTE: [10, 90, 1, 'Nhập điểm PTE Academic'],
    SAT: [400, 1600, 10, 'Nhập điểm SAT'],
    ACT: [1, 36, 1, 'Nhập điểm ACT'],
    TCF: [100, 699, 1, 'Nhập điểm TCF'],
    BJT: [0, 800, 1, 'Nhập điểm BJT'],
    NAT_TEST: [0, 180, 1, 'Nhập điểm NAT-TEST'],
  };
  var LEVEL_SCORES = {
    B1: 6, B2: 8, C1: 9, C2: 10,
    VSTEP_B1: 6.5, VSTEP_B2: 8, VSTEP_C1: 9, VSTEP_C2: 10,
    CAMBRIDGE_B1: 6.5, CAMBRIDGE_B2: 8, CAMBRIDGE_C1: 9, CAMBRIDGE_C2: 10,
    APTIS_B1: 6.5, APTIS_B2: 8, APTIS_C1: 9, APTIS_C2: 10,
    HSK_3: 6.5, HSK_4: 8, HSK_5: 9, HSK_6: 10,
    TOCFL_B1: 6.5, TOCFL_B2: 8, TOCFL_C1: 9, TOCFL_C2: 10,
    N4: 6, N3: 7.5, N2: 9, N1: 10,
    DELF_B1: 6.5, DELF_B2: 8, DALF_C1: 9, DALF_C2: 10,
    TOPIK_3: 6.5, TOPIK_4: 8, TOPIK_5: 9, TOPIK_6: 10,
    GOETHE_B1: 6.5, GOETHE_B2: 8, GOETHE_C1: 9,
    DSD_B1: 6.5, DSD_B2: 8, DSD_C1: 9,
    TORFL_B1: 6.5, TORFL_B2: 8, TORFL_C1: 9
  };
  function clamp(value) { return Math.max(0, Math.min(10, Number(value) || 0)); }
  function numericValue(value) {
    var parsed = Number.parseFloat(String(value == null ? '' : value).trim().replace(',', '.'));
    return Number.isFinite(parsed) ? parsed : NaN;
  }
  function convertCertificateToNormalizedScore(language, certType, scoreOrLevel, highSchoolLanguageScore) {
    if (!certType || certType === 'NONE') return clamp(highSchoolLanguageScore);
    var score = numericValue(scoreOrLevel);
    if (certType === 'IELTS') return score >= 7.5 ? 10 : score >= 7 ? 9.5 : score >= 6.5 ? 9 : score >= 6 ? 8 : score >= 5.5 ? 7 : score >= 5 ? 6 : 0;
    if (certType === 'JLPT') return LEVEL_SCORES[scoreOrLevel] || 0;
    if (certType === 'HSK') return LEVEL_SCORES[scoreOrLevel] || 0;
    if (LEVEL_SCORES[scoreOrLevel]) return LEVEL_SCORES[scoreOrLevel];
    if (!Number.isFinite(score)) return 0;
    var ranges = { TOEFL_IBT: [0, 120], TOEFL_ITP: [310, 677], TOEIC: [10, 990], PTE: [10, 90], SAT: [400, 1600], ACT: [1, 36], TCF: [100, 699], BJT: [0, 800], NAT_TEST: [0, 180], DSD: [0, 100] };
    var range = ranges[certType];
    return range ? clamp((score - range[0]) / (range[1] - range[0]) * 10) : 0;
  }
  function isExpired(issueDate, now) {
    if (!issueDate) return false;
    var issued = new Date(issueDate + 'T00:00:00');
    var current = now || new Date();
    var expiry = new Date(issued);
    expiry.setFullYear(expiry.getFullYear() + 2);
    return Number.isFinite(issued.getTime()) && expiry < current;
  }
  global.AxisCertificates = { LANGUAGES: LANGUAGES, LEVELS: LEVELS, NUMERIC: NUMERIC, convertCertificateToNormalizedScore: convertCertificateToNormalizedScore, isExpired: isExpired };
})(window);
