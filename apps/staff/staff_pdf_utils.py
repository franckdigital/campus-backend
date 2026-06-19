import datetime

CONTRACT_LABELS = {
    'PERMANENT': ('Permanent',   '#065f46', '#d1fae5'),
    'CONTRACT':  ('Contractuel', '#92400e', '#fef3c7'),
    'INTERN':    ('Stagiaire',   '#3730a3', '#e0e7ff'),
}

DEPARTMENT_LABELS = {
    'DIRECTION':    'Direction',
    'SCOLARITE':    'Scolarité',
    'COMPTABILITE': 'Comptabilité',
    'INFORMATIQUE': 'Informatique',
    'SECRETARIAT':  'Secrétariat',
    'BIBLIOTHEQUE': 'Bibliothèque',
    'MAINTENANCE':  'Maintenance',
    'AUTRE':        'Autre',
}


def _s(val, fallback='—'):
    v = str(val).strip() if val is not None else ''
    return v if v else fallback


def generate_staff_fiche_html(staff):
    """Génère une fiche complète de personnel administratif en HTML imprimable."""
    user = staff.user
    full_name = f"{user.first_name} {user.last_name}".strip() or '—'
    email = _s(user.email)
    phone = _s(getattr(user, 'phone', None))

    contract_label, contract_color, contract_bg = CONTRACT_LABELS.get(
        staff.contract_type, (staff.contract_type, '#374151', '#f1f5f9')
    )

    department_label = DEPARTMENT_LABELS.get(staff.department, staff.department)

    hire_date_str = staff.hire_date.strftime('%d/%m/%Y') if staff.hire_date else '—'

    # Years at company
    years_at_company = '—'
    if staff.hire_date:
        today = datetime.date.today()
        delta = today - staff.hire_date
        years = delta.days // 365
        years_at_company = str(years)

    monthly_hours = (staff.contract_hours_per_week * 4) if staff.contract_hours_per_week else None
    hours_per_week_str = f"{staff.contract_hours_per_week}h" if staff.contract_hours_per_week else '—'
    monthly_hours_str = f"{monthly_hours}h" if monthly_hours else '—'

    site_name = staff.site.name if staff.site else '—'
    academic_year_name = staff.academic_year.name if staff.academic_year else '—'

    # Avatar initials
    initials = ((user.first_name or ' ')[0] + (user.last_name or ' ')[0]).upper()

    # Experiences table rows
    exp_rows = ''
    experiences = list(staff.experiences.all())
    for i, exp in enumerate(experiences):
        bg = '#f8fafc' if i % 2 == 0 else 'white'
        start = exp.start_date.strftime('%m/%Y') if exp.start_date else '—'
        end = 'Présent' if exp.is_current else (exp.end_date.strftime('%m/%Y') if exp.end_date else '—')
        desc = f'<br><span style="color:#64748b;font-style:italic">{exp.description}</span>' if exp.description else ''
        exp_rows += f'''
        <tr style="background:{bg}">
          <td style="padding:10px 12px;font-weight:600;color:#0f172a">{_s(exp.position)}</td>
          <td style="padding:10px 12px;color:#0891b2">{_s(exp.company)}</td>
          <td style="padding:10px 12px;font-family:monospace;color:#64748b">{start} – {end}</td>
          <td style="padding:10px 12px">{desc}</td>
        </tr>'''

    if not exp_rows:
        exp_rows = '<tr><td colspan="4" style="padding:20px;text-align:center;color:#94a3b8;font-style:italic">Aucune expérience enregistrée</td></tr>'

    # Bio section
    bio_section = ''
    if staff.bio:
        bio_section = f'''
        <div style="margin-top:14px">
          <div class="info-label" style="margin-bottom:6px">Biographie</div>
          <p style="font-size:13px;color:#374151;padding:14px 16px;background:#f8fafc;border-radius:8px;border:1px solid #f1f5f9;line-height:1.7">{staff.bio}</p>
        </div>'''

    today = datetime.date.today().strftime('%d/%m/%Y')

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fiche Personnel — {full_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; color: #1e293b; background: #f1f5f9; }}
  .page {{ max-width: 880px; margin: 24px auto; background: white; box-shadow: 0 4px 24px rgba(0,0,0,0.12); border-radius: 16px; overflow: hidden; }}

  .header {{ background: linear-gradient(135deg, #0f766e 0%, #0891b2 100%); padding: 32px 40px; color: white; }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }}
  .school-name {{ font-size: 18px; font-weight: bold; }}
  .doc-type {{ font-size: 11px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-top: 4px; }}
  .header-meta {{ font-size: 12px; opacity: 0.7; text-align: right; line-height: 1.6; }}
  .staff-row {{ display: flex; align-items: center; gap: 24px; }}
  .avatar {{ width: 76px; height: 76px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; color: white; border: 3px solid rgba(255,255,255,0.4); flex-shrink: 0; }}
  .staff-name {{ font-size: 28px; font-weight: 900; margin-bottom: 4px; letter-spacing: -0.5px; }}
  .staff-id {{ font-size: 13px; opacity: 0.8; font-family: monospace; letter-spacing: 1px; }}
  .contract-badge {{ display: inline-block; margin-top: 10px; padding: 4px 14px; border-radius: 20px; font-size: 11px; font-weight: bold; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.35); }}

  .kpi-strip {{ display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid #e2e8f0; }}
  .kpi {{ padding: 22px 16px; text-align: center; border-right: 1px solid #e2e8f0; }}
  .kpi:last-child {{ border-right: none; }}
  .kpi-value {{ font-size: 30px; font-weight: 900; color: #0f766e; line-height: 1; }}
  .kpi-label {{ font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}

  .body {{ padding: 36px 40px; }}
  .section {{ margin-bottom: 36px; }}
  .section-title {{ font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1.2px; color: #0f766e; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #ccfbf1; display: flex; align-items: center; gap: 8px; }}
  .section-title::before {{ content: ''; display: inline-block; width: 4px; height: 16px; background: linear-gradient(180deg, #0f766e, #0891b2); border-radius: 2px; }}

  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .info-row {{ display: flex; gap: 12px; padding: 10px 14px; background: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9; align-items: flex-start; }}
  .info-label {{ font-size: 10px; font-weight: bold; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; min-width: 110px; flex-shrink: 0; padding-top: 2px; }}
  .info-value {{ font-size: 13px; color: #1e293b; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead tr {{ background: linear-gradient(135deg, #0f766e, #0891b2); color: white; }}
  thead th {{ padding: 11px 12px; text-align: left; font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.6px; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; transition: background 0.1s; }}
  .table-wrap {{ border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }}

  .sig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 36px; }}
  .sig-box {{ border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; height: 90px; }}
  .sig-label {{ font-size: 10px; color: #94a3b8; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }}

  .footer {{ background: #f8fafc; padding: 18px 40px; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }}
  .footer-text {{ font-size: 11px; color: #94a3b8; line-height: 1.6; }}

  .print-btn {{ position: fixed; top: 16px; right: 16px; background: linear-gradient(135deg, #0f766e, #0891b2); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: bold; cursor: pointer; z-index: 999; box-shadow: 0 4px 14px rgba(15,118,110,0.4); }}

  @media print {{
    body {{ background: white; }}
    .page {{ box-shadow: none; margin: 0; border-radius: 0; }}
    .print-btn {{ display: none; }}
    .kpi-strip, .section {{ break-inside: avoid; }}
  }}
</style>
</head>
<body>
<button class="print-btn" onclick="window.print()">&#128438; Imprimer / PDF</button>

<div class="page">

  <div class="header">
    <div class="header-top">
      <div>
        <div class="school-name">CampusLMS</div>
        <div class="doc-type">Fiche du personnel administratif</div>
      </div>
      <div class="header-meta">
        <div>Généré le {today}</div>
        <div>Document officiel</div>
      </div>
    </div>
    <div class="staff-row">
      <div class="avatar">{initials}</div>
      <div>
        <div class="staff-name">{full_name}</div>
        <div class="staff-id">Matricule : {_s(staff.employee_id)}</div>
        <div class="contract-badge">{contract_label} — {department_label}</div>
      </div>
    </div>
  </div>

  <div class="kpi-strip">
    <div class="kpi">
      <div class="kpi-value">{years_at_company}</div>
      <div class="kpi-label">Années ancienneté</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{hours_per_week_str}</div>
      <div class="kpi-label">H / semaine</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{monthly_hours_str}</div>
      <div class="kpi-label">H / mois</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{len(experiences)}</div>
      <div class="kpi-label">Expériences</div>
    </div>
  </div>

  <div class="body">

    <div class="section">
      <div class="section-title">Informations personnelles</div>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Nom complet</span>
          <span class="info-value"><strong>{full_name}</strong></span>
        </div>
        <div class="info-row">
          <span class="info-label">E-mail</span>
          <span class="info-value">{email}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Téléphone</span>
          <span class="info-value">{phone}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Site</span>
          <span class="info-value">{site_name}</span>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Informations professionnelles</div>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Matricule</span>
          <span class="info-value" style="font-family:monospace;font-weight:bold;color:#0f766e">{_s(staff.employee_id)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Département</span>
          <span class="info-value">{department_label}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Poste</span>
          <span class="info-value"><strong>{_s(staff.position)}</strong></span>
        </div>
        <div class="info-row">
          <span class="info-label">Type de contrat</span>
          <span class="info-value">
            <span style="background:{contract_bg};color:{contract_color};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold">{contract_label}</span>
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">Date d&apos;embauche</span>
          <span class="info-value">{hire_date_str}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Année académique</span>
          <span class="info-value">{academic_year_name}</span>
        </div>
        <div class="info-row">
          <span class="info-label">H / semaine</span>
          <span class="info-value">{hours_per_week_str}</span>
        </div>
        <div class="info-row">
          <span class="info-label">H / mois</span>
          <span class="info-value">{monthly_hours_str}</span>
        </div>
      </div>
      {bio_section}
    </div>

    <div class="section">
      <div class="section-title">Expériences professionnelles</div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Poste</th><th>Établissement / Entreprise</th><th>Période</th><th>Description</th>
          </tr></thead>
          <tbody>{exp_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="sig-grid">
      <div class="sig-box">
        <div class="sig-label">Signature de l&apos;agent</div>
      </div>
      <div class="sig-box">
        <div class="sig-label">Visa du directeur / DRH</div>
      </div>
    </div>

  </div>

  <div class="footer">
    <div class="footer-text">
      <div>Fiche générée automatiquement par CampusLMS</div>
      <div>Document à usage interne — non contractuel</div>
    </div>
    <div class="footer-text" style="text-align:right">
      <div>Généré le {today}</div>
      <div>{full_name} · {_s(staff.employee_id)}</div>
    </div>
  </div>

</div>
</body></html>'''
