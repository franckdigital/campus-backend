import datetime


STATUS_MAP = {
    'PASS':        ('Admis',        '#16a34a', '#dcfce7', '#bbf7d0'),
    'FAIL':        ('Ajourné',      '#dc2626', '#fee2e2', '#fecaca'),
    'CONDITIONAL': ('Conditionnel', '#ca8a04', '#fef9c3', '#fef08a'),
    'HONORS':      ('Mention TB',   '#7c3aed', '#ede9fe', '#ddd6fe'),
    'PENDING':     ('En attente',   '#64748b', '#f1f5f9', '#e2e8f0'),
}

EVAL_TYPE_LABELS = {
    'DEVOIR':     'CC',
    'EXAMEN':     'Examen',
    'TP':         'TP',
    'RATTRAPAGE': 'Rattr.',
}


def _s(val, fallback='—'):
    if val is None or val == '':
        return fallback
    return str(val)


def generate_bulletin_html(card):
    school_name = 'ITA ABIDJAN'
    school_sub  = 'Institut de Technologie et d\'Administration'
    if card.class_group and hasattr(card.class_group, 'site') and card.class_group.site:
        school_name = card.class_group.site.name.upper()
        if hasattr(card.class_group.site, 'city') and card.class_group.site.city:
            school_sub = card.class_group.site.city

    student_name  = _s(card.student.user.full_name if card.student and card.student.user else None)
    matricule     = _s(card.student.matricule if card.student else None)
    class_name    = _s(card.class_group.name if card.class_group else None)
    semester_lbl  = _s(card.semester.label if card.semester else None)
    year_name     = _s(card.semester.academic_year.name if card.semester and card.semester.academic_year else None)

    status_label, st_color, st_bg, st_border = STATUS_MAP.get(card.status, ('—', '#64748b', '#f1f5f9', '#e2e8f0'))
    avg_str  = f"{float(card.average):.2f}/20" if card.average is not None else '—'
    rank_str = f"{card.rank}/{card.total_students}" if card.rank and card.total_students else '—'

    subjects = list((card.subject_averages or {}).values())
    total_coeff    = 0.0
    total_weighted = 0.0

    rows_html = ''
    for s in subjects:
        coeff     = float(s.get('coefficient', 1))
        avg       = float(s.get('average', 0))
        total_coeff    += coeff
        total_weighted += avg * coeff
        avg_color = '#16a34a' if avg >= 10 else '#dc2626'

        rows_html += f"""
        <tr class="subj-row">
          <td class="subj-name">{s.get('subject_name', '—')}</td>
          <td class="center mono">{s.get('subject_code','')}</td>
          <td class="center mono">{coeff:.0f}</td>
          <td class="center mono bold" style="color:{avg_color}">{avg:.2f}</td>
          <td class="center mono">{avg * coeff:.2f}</td>
        </tr>"""

        for g in s.get('grades', []):
            et_label   = EVAL_TYPE_LABELS.get(g.get('eval_type', ''), g.get('eval_type', ''))
            sc         = float(g.get('score_on_20', 0))
            sc_color   = '#16a34a' if sc >= 10 else '#dc2626'
            coef_eval  = float(g.get('eval_coefficient', 1))
            rows_html += f"""
        <tr class="eval-row">
          <td class="eval-name">↳ {g.get('evaluation_title','—')}</td>
          <td class="center mono eval-badge">{et_label}</td>
          <td class="center mono eval-sub">coef {coef_eval:.1f}</td>
          <td class="center mono" style="color:{sc_color}">{sc:.2f}</td>
          <td class="center mono eval-sub"></td>
        </tr>"""

    if subjects:
        global_avg = total_weighted / total_coeff if total_coeff else 0
        total_row  = f"""
        <tr class="total-row">
          <td colspan="2" class="total-label">MOYENNE GÉNÉRALE</td>
          <td class="center mono bold">{total_coeff:.0f}</td>
          <td class="center mono bold" style="color:#1e40af">{global_avg:.2f}/20</td>
          <td class="center mono bold" style="color:#1e40af">{total_weighted:.2f}</td>
        </tr>"""
    else:
        total_row = '<tr class="empty-row"><td colspan="5">Aucune note enregistrée pour ce semestre</td></tr>'

    comment_html = ''
    if card.teacher_comment:
        comment_html += f'<div class="comment"><strong>Appréciation du prof. principal :</strong> {card.teacher_comment}</div>'
    if card.principal_comment:
        comment_html += f'<div class="comment"><strong>Appréciation du directeur :</strong> {card.principal_comment}</div>'

    now = datetime.datetime.now().strftime('%d/%m/%Y à %H:%M')

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bulletin — {student_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'Segoe UI',Arial,sans-serif;background:#f1f5f9;color:#0f172a;}}
.page{{max-width:820px;margin:24px auto;background:#fff;border-radius:16px;
      box-shadow:0 8px 40px rgba(15,23,50,.12);overflow:hidden}}

/* HEADER */
.hdr{{background:linear-gradient(135deg,#1e40af 0%,#0891b2 100%);
      color:#fff;padding:28px 40px;display:flex;align-items:center;
      justify-content:space-between;position:relative;overflow:hidden}}
.hdr::before{{content:'';position:absolute;top:-70px;right:-50px;
              width:220px;height:220px;border-radius:50%;
              background:rgba(255,255,255,.06)}}
.hdr::after{{content:'';position:absolute;bottom:-50px;left:38%;
             width:160px;height:160px;border-radius:50%;
             background:rgba(255,255,255,.04)}}
.hdr-left{{position:relative;z-index:1}}
.school-name{{font-size:22px;font-weight:800;letter-spacing:.05em}}
.school-sub{{font-size:11px;opacity:.65;margin-top:3px;letter-spacing:.1em;text-transform:uppercase}}
.hdr-right{{position:relative;z-index:1;text-align:right}}
.doc-title{{font-size:17px;font-weight:700}}
.doc-period{{font-size:11px;opacity:.7;margin-top:5px}}

/* STUDENT INFO */
.info-section{{padding:22px 40px;border-bottom:2px solid #f0f4f9;background:#fafbff}}
.info-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:16px}}
.info-item{{display:flex;flex-direction:column;gap:3px}}
.info-label{{font-size:10px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em}}
.info-value{{font-size:13px;font-weight:700;color:#0f172a}}

/* KPI STRIP */
.kpi-strip{{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:2px solid #f0f4f9}}
.kpi{{padding:18px 16px;display:flex;flex-direction:column;align-items:center;gap:5px;
      border-right:1px solid #f0f4f9}}
.kpi:last-child{{border-right:none}}
.kpi-label{{font-size:9px;font-weight:700;color:#94a3b8;text-transform:uppercase;letter-spacing:.08em}}
.kpi-value{{font-size:24px;font-weight:800;color:#0f172a}}
.kpi-badge{{font-size:12px;font-weight:700;padding:4px 14px;border-radius:20px;
            background:{st_bg};color:{st_color};border:1px solid {st_border}}}

/* TABLE */
.table-section{{padding:24px 40px}}
.section-title{{font-size:11px;font-weight:800;color:#64748b;text-transform:uppercase;
                letter-spacing:.12em;margin-bottom:14px;display:flex;align-items:center;gap:8px}}
.section-title::before{{content:'';display:inline-block;width:3px;height:14px;
                        background:linear-gradient(135deg,#1e40af,#0891b2);border-radius:2px}}
table{{width:100%;border-collapse:collapse}}
thead tr{{background:linear-gradient(135deg,#1e40af,#0891b2)}}
thead th{{color:#fff;padding:10px 14px;text-align:center;font-size:10px;font-weight:700;
          letter-spacing:.06em;text-transform:uppercase}}
thead th:first-child{{text-align:left;padding-left:16px}}

.subj-row{{background:#fafbff;transition:background .15s}}
.subj-row:hover{{background:#eff6ff}}
.subj-name{{padding:11px 16px;font-weight:700;font-size:13px;color:#0f172a}}
.eval-row{{background:#fff}}
.eval-name{{padding:6px 16px 6px 30px;font-size:11px;color:#64748b;font-style:italic}}
.eval-badge{{font-size:10px;color:#7c3aed;font-weight:700;letter-spacing:.04em}}
.eval-sub{{color:#94a3b8;font-size:11px}}

.center{{text-align:center;padding:9px 14px;vertical-align:middle}}
.mono{{font-family:'Courier New',monospace}}
.bold{{font-weight:700}}

td{{border-bottom:1px solid #f1f5f9;vertical-align:middle}}

.total-row{{background:linear-gradient(90deg,#eff6ff,#f0fdf4);border-top:2px solid #bfdbfe}}
.total-row td{{padding:12px 14px;color:#1e40af}}
.total-label{{padding:12px 16px;font-size:13px;font-weight:800;color:#1e40af;grid-column:span 2}}
.empty-row td{{padding:24px;text-align:center;color:#94a3b8;font-style:italic;font-size:13px}}

/* COMMENT */
.comment{{margin:0 40px 20px;padding:14px 18px;background:#fafbff;border-left:3px solid #3b82f6;
          border-radius:0 8px 8px 0;font-size:13px;color:#374151;line-height:1.5}}

/* SIGNATURES */
.sig-section{{padding:24px 40px;display:flex;justify-content:space-between}}
.sig-block{{text-align:center;min-width:180px}}
.sig-label{{font-size:11px;font-weight:700;color:#475569;margin-bottom:48px}}
.sig-line{{border-top:1px dashed #cbd5e1;padding-top:8px;font-size:10px;color:#94a3b8}}

/* FOOTER */
.footer{{background:#f8fafc;border-top:1px solid #f0f4f9;padding:12px 40px;
         display:flex;justify-content:space-between;align-items:center}}
.footer-text{{font-size:10px;color:#94a3b8}}

/* PRINT BTN */
.print-bar{{position:fixed;top:0;left:0;right:0;background:linear-gradient(90deg,#1e40af,#0891b2);
            padding:10px 20px;display:flex;justify-content:flex-end;gap:12px;
            box-shadow:0 2px 12px rgba(30,64,175,.3);z-index:100}}
.btn-print{{background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);
            color:#fff;padding:8px 20px;border-radius:8px;font-weight:700;font-size:13px;
            cursor:pointer;display:flex;align-items:center;gap:8px;backdrop-filter:blur(8px)}}
.btn-print:hover{{background:rgba(255,255,255,.25)}}
body {{padding-top: 52px}}
@media print{{
  body{{background:#fff;padding-top:0}}
  .print-bar{{display:none}}
  .page{{margin:0;border-radius:0;box-shadow:none;max-width:100%}}
}}
</style>
</head>
<body>
<div class="print-bar">
  <button class="btn-print" onclick="window.print()">🖨️ Imprimer / Enregistrer PDF</button>
</div>

<div class="page">
  <div class="hdr">
    <div class="hdr-left">
      <div class="school-name">{school_name}</div>
      <div class="school-sub">{school_sub}</div>
    </div>
    <div class="hdr-right">
      <div class="doc-title">BULLETIN DE NOTES</div>
      <div class="doc-period">{semester_lbl}</div>
      <div class="doc-period">Année académique {year_name}</div>
    </div>
  </div>

  <div class="info-section">
    <div class="info-grid">
      <div class="info-item">
        <span class="info-label">Étudiant(e)</span>
        <span class="info-value">{student_name}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Matricule</span>
        <span class="info-value">{matricule}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Classe</span>
        <span class="info-value">{class_name}</span>
      </div>
      <div class="info-item">
        <span class="info-label">Année académique</span>
        <span class="info-value">{year_name}</span>
      </div>
    </div>
  </div>

  <div class="kpi-strip">
    <div class="kpi">
      <span class="kpi-label">Moyenne générale</span>
      <span class="kpi-value">{avg_str}</span>
    </div>
    <div class="kpi">
      <span class="kpi-label">Rang / Effectif</span>
      <span class="kpi-value">{rank_str}</span>
    </div>
    <div class="kpi">
      <span class="kpi-label">Matières évaluées</span>
      <span class="kpi-value">{len(subjects)}</span>
    </div>
    <div class="kpi">
      <span class="kpi-label">Décision</span>
      <span class="kpi-badge">{status_label}</span>
    </div>
  </div>

  <div class="table-section">
    <div class="section-title">Détail des notes par matière</div>
    <table>
      <thead>
        <tr>
          <th style="text-align:left;padding-left:16px;width:38%">Matière / Évaluation</th>
          <th>Code</th>
          <th>Coeff.</th>
          <th>Moy./20</th>
          <th>Moy. pond.</th>
        </tr>
      </thead>
      <tbody>
        {rows_html}
        {total_row}
      </tbody>
    </table>
  </div>

  {comment_html}

  <div class="sig-section">
    <div class="sig-block">
      <div class="sig-label">Signature du professeur principal</div>
      <div class="sig-line">Cachet et signature</div>
    </div>
    <div class="sig-block">
      <div class="sig-label">Visa du Chef de département</div>
      <div class="sig-line">Cachet et signature</div>
    </div>
    <div class="sig-block">
      <div class="sig-label">Cachet de la Direction</div>
      <div class="sig-line">Cachet et signature</div>
    </div>
  </div>

  <div class="footer">
    <span class="footer-text">Généré le {now}</span>
    <span class="footer-text">{school_name} · Document officiel · Confidentiel</span>
  </div>
</div>
</body>
</html>"""
