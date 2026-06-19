import datetime

DAY_NAMES = {0: 'Lundi', 1: 'Mardi', 2: 'Mercredi', 3: 'Jeudi', 4: 'Vendredi', 5: 'Samedi', 6: 'Dimanche'}

CONTRACT_LABELS = {
    'PERMANENT': ('Permanent',   '#065f46', '#d1fae5'),
    'CONTRACT':  ('Contractuel', '#92400e', '#fef3c7'),
    'VISITING':  ('Vacataire',   '#3730a3', '#e0e7ff'),
}


def _s(val, fallback='—'):
    v = str(val).strip() if val is not None else ''
    return v if v else fallback


def generate_teacher_fiche_html(teacher):
    """Génère une fiche complète d'enseignant en HTML imprimable (même pattern que les factures)."""
    user = teacher.user
    full_name = f"{user.first_name} {user.last_name}".strip() or '—'
    email = _s(user.email)
    phone = _s(getattr(user, 'phone', None))

    contract_label, contract_color, contract_bg = CONTRACT_LABELS.get(
        teacher.contract_type, (teacher.contract_type, '#374151', '#f1f5f9')
    )

    hire_date = teacher.hire_date.strftime('%d/%m/%Y') if teacher.hire_date else '—'
    hourly_rate = f"{float(teacher.hourly_rate):,.0f} FCFA/h" if teacher.hourly_rate else '—'

    # Sites
    sites = teacher.teacher_sites.select_related('site').all()
    sites_str = ', '.join(
        ts.site.name + (' (principal)' if ts.is_primary else '') for ts in sites
    ) or '—'

    # Assignments
    assignments = teacher.class_subjects.select_related(
        'class_obj__level__program', 'subject'
    ).filter(is_active=True)

    # Sessions
    sessions = teacher.sessions.select_related('class_obj', 'subject', 'room').filter(is_active=True)

    # Workload
    weekly_hours = 0.0
    for s in sessions:
        h1 = s.start_time.hour * 60 + s.start_time.minute
        h2 = s.end_time.hour * 60 + s.end_time.minute
        weekly_hours += max(0, h2 - h1) / 60.0
    weekly_hours = round(weekly_hours, 1)

    subjects_count = assignments.values('subject').distinct().count()
    classes_count = assignments.values('class_obj').distinct().count()
    assignments_count = assignments.count()
    sessions_count = sessions.count()

    # Assignments table rows
    aff_rows = ''
    for i, a in enumerate(assignments):
        bg = '#f8fafc' if i % 2 == 0 else 'white'
        aff_rows += f'''
        <tr style="background:{bg}">
          <td style="padding:10px 12px;font-family:monospace;color:#6366f1;font-weight:bold">{_s(a.subject.code)}</td>
          <td style="padding:10px 12px">{_s(a.subject.name)}</td>
          <td style="padding:10px 12px;color:#0891b2;font-weight:600">{_s(a.class_obj.name)}</td>
          <td style="padding:10px 12px;color:#64748b">{_s(a.class_obj.level.name)}</td>
          <td style="padding:10px 12px;color:#64748b">{_s(a.class_obj.level.program.name)}</td>
        </tr>'''
    if not aff_rows:
        aff_rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#94a3b8;font-style:italic">Aucune affectation enregistrée</td></tr>'

    # Sessions table rows
    sess_rows = ''
    for i, s in enumerate(sorted(sessions, key=lambda x: (x.day_of_week, str(x.start_time)))):
        bg = '#f8fafc' if i % 2 == 0 else 'white'
        day = DAY_NAMES.get(s.day_of_week, str(s.day_of_week))
        start = s.start_time.strftime('%H:%M')
        end = s.end_time.strftime('%H:%M')
        room = _s(s.room.name if s.room else None)
        sess_rows += f'''
        <tr style="background:{bg}">
          <td style="padding:10px 12px;font-weight:600;color:#1e293b">{day}</td>
          <td style="padding:10px 12px;font-family:monospace;color:#0891b2">{start} – {end}</td>
          <td style="padding:10px 12px">{_s(s.subject.name)}</td>
          <td style="padding:10px 12px;color:#6366f1;font-weight:600">{_s(s.class_obj.name)}</td>
          <td style="padding:10px 12px;color:#64748b">{room}</td>
        </tr>'''
    if not sess_rows:
        sess_rows = '<tr><td colspan="5" style="padding:20px;text-align:center;color:#94a3b8;font-style:italic">Aucune séance planifiée</td></tr>'

    # Avatar initials
    initials = ((user.first_name or ' ')[0] + (user.last_name or ' ')[0]).upper()

    # Overload
    overloaded = weekly_hours > 18
    load_bg = '#fef2f2' if overloaded else '#f0fdf4'
    load_border = '#fecaca' if overloaded else '#bbf7d0'
    load_color = '#dc2626' if overloaded else '#16a34a'
    load_label = '⚠ Surcharge horaire détectée' if overloaded else '✓ Charge horaire normale'

    # Experiences
    exp_rows = ''
    experiences = teacher.experiences.all()
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

    # Bio section
    bio_section = ''
    if teacher.bio:
        bio_section = f'''
        <div style="margin-top:14px">
          <div class="info-label" style="margin-bottom:6px">Biographie</div>
          <p style="font-size:13px;color:#374151;padding:14px 16px;background:#f8fafc;border-radius:8px;border:1px solid #f1f5f9;line-height:1.7">{teacher.bio}</p>
        </div>'''

    today = datetime.date.today().strftime('%d/%m/%Y')

    return f'''<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fiche Enseignant — {full_name}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; color: #1e293b; background: #f1f5f9; }}
  .page {{ max-width: 880px; margin: 24px auto; background: white; box-shadow: 0 4px 24px rgba(0,0,0,0.12); border-radius: 16px; overflow: hidden; }}

  .header {{ background: linear-gradient(135deg, #1e40af 0%, #0891b2 100%); padding: 32px 40px; color: white; }}
  .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 28px; }}
  .school-name {{ font-size: 18px; font-weight: bold; }}
  .doc-type {{ font-size: 11px; text-transform: uppercase; letter-spacing: 2px; opacity: 0.7; margin-top: 4px; }}
  .header-meta {{ font-size: 12px; opacity: 0.7; text-align: right; line-height: 1.6; }}
  .teacher-row {{ display: flex; align-items: center; gap: 24px; }}
  .avatar {{ width: 76px; height: 76px; border-radius: 50%; background: rgba(255,255,255,0.2); display: flex; align-items: center; justify-content: center; font-size: 28px; font-weight: bold; color: white; border: 3px solid rgba(255,255,255,0.4); flex-shrink: 0; }}
  .teacher-name {{ font-size: 28px; font-weight: 900; margin-bottom: 4px; letter-spacing: -0.5px; }}
  .teacher-id {{ font-size: 13px; opacity: 0.8; font-family: monospace; letter-spacing: 1px; }}
  .contract-badge {{ display: inline-block; margin-top: 10px; padding: 4px 14px; border-radius: 20px; font-size: 11px; font-weight: bold; background: rgba(255,255,255,0.2); color: white; border: 1px solid rgba(255,255,255,0.35); }}

  .kpi-strip {{ display: grid; grid-template-columns: repeat(4, 1fr); border-bottom: 1px solid #e2e8f0; }}
  .kpi {{ padding: 22px 16px; text-align: center; border-right: 1px solid #e2e8f0; }}
  .kpi:last-child {{ border-right: none; }}
  .kpi-value {{ font-size: 30px; font-weight: 900; color: #1e40af; line-height: 1; }}
  .kpi-label {{ font-size: 10px; color: #94a3b8; margin-top: 4px; text-transform: uppercase; letter-spacing: 0.5px; }}

  .body {{ padding: 36px 40px; }}
  .section {{ margin-bottom: 36px; }}
  .section-title {{ font-size: 12px; font-weight: bold; text-transform: uppercase; letter-spacing: 1.2px; color: #1e40af; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid #dbeafe; display: flex; align-items: center; gap: 8px; }}
  .section-title::before {{ content: ''; display: inline-block; width: 4px; height: 16px; background: linear-gradient(180deg, #1e40af, #0891b2); border-radius: 2px; }}

  .info-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .info-row {{ display: flex; gap: 12px; padding: 10px 14px; background: #f8fafc; border-radius: 8px; border: 1px solid #f1f5f9; align-items: flex-start; }}
  .info-label {{ font-size: 10px; font-weight: bold; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; min-width: 110px; flex-shrink: 0; padding-top: 2px; }}
  .info-value {{ font-size: 13px; color: #1e293b; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  thead tr {{ background: linear-gradient(135deg, #1e40af, #0891b2); color: white; }}
  thead th {{ padding: 11px 12px; text-align: left; font-size: 10px; font-weight: bold; text-transform: uppercase; letter-spacing: 0.6px; }}
  tbody tr {{ border-bottom: 1px solid #f1f5f9; transition: background 0.1s; }}
  .table-wrap {{ border-radius: 10px; overflow: hidden; border: 1px solid #e2e8f0; }}

  .load-box {{ margin-top: 16px; padding: 16px 20px; background: {load_bg}; border-radius: 10px; border: 1px solid {load_border}; display: flex; justify-content: space-between; align-items: center; }}
  .load-label {{ font-size: 13px; font-weight: bold; color: {load_color}; }}
  .load-sub {{ font-size: 12px; color: #64748b; margin-top: 3px; }}
  .load-hours {{ font-size: 32px; font-weight: 900; color: {load_color}; line-height: 1; }}
  .load-unit {{ font-size: 11px; color: #94a3b8; margin-top: 2px; text-align: right; }}

  .sig-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 24px; margin-top: 36px; }}
  .sig-box {{ border: 1px solid #e2e8f0; border-radius: 10px; padding: 16px; height: 90px; }}
  .sig-label {{ font-size: 10px; color: #94a3b8; text-align: center; font-weight: bold; text-transform: uppercase; letter-spacing: 0.5px; }}

  .footer {{ background: #f8fafc; padding: 18px 40px; border-top: 1px solid #e2e8f0; display: flex; justify-content: space-between; align-items: center; }}
  .footer-text {{ font-size: 11px; color: #94a3b8; line-height: 1.6; }}

  .print-btn {{ position: fixed; top: 16px; right: 16px; background: linear-gradient(135deg, #1e40af, #0891b2); color: white; border: none; padding: 12px 24px; border-radius: 10px; font-size: 14px; font-weight: bold; cursor: pointer; z-index: 999; box-shadow: 0 4px 14px rgba(30,64,175,0.4); }}

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
        <div class="doc-type">Fiche de l&apos;enseignant</div>
      </div>
      <div class="header-meta">
        <div>Généré le {today}</div>
        <div>Document officiel</div>
      </div>
    </div>
    <div class="teacher-row">
      <div class="avatar">{initials}</div>
      <div>
        <div class="teacher-name">{full_name}</div>
        <div class="teacher-id">Matricule : {_s(teacher.employee_id)}</div>
        <div class="contract-badge">{contract_label}</div>
      </div>
    </div>
  </div>

  <div class="kpi-strip">
    <div class="kpi">
      <div class="kpi-value">{assignments_count}</div>
      <div class="kpi-label">Affectations</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{classes_count}</div>
      <div class="kpi-label">Classes</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{subjects_count}</div>
      <div class="kpi-label">Matières</div>
    </div>
    <div class="kpi">
      <div class="kpi-value">{weekly_hours}h</div>
      <div class="kpi-label">H / semaine</div>
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
          <span class="info-label">Sites</span>
          <span class="info-value">{sites_str}</span>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Informations professionnelles</div>
      <div class="info-grid">
        <div class="info-row">
          <span class="info-label">Matricule</span>
          <span class="info-value" style="font-family:monospace;font-weight:bold;color:#1e40af">{_s(teacher.employee_id)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Type de contrat</span>
          <span class="info-value">
            <span style="background:{contract_bg};color:{contract_color};padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold">{contract_label}</span>
          </span>
        </div>
        <div class="info-row">
          <span class="info-label">Spécialisation</span>
          <span class="info-value">{_s(teacher.specialization)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Qualification</span>
          <span class="info-value">{_s(teacher.qualification)}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Date d&apos;embauche</span>
          <span class="info-value">{hire_date}</span>
        </div>
        <div class="info-row">
          <span class="info-label">Taux horaire</span>
          <span class="info-value">{hourly_rate}</span>
        </div>
      </div>
      {bio_section}
    </div>

    <div class="section">
      <div class="section-title">Affectations — Matières enseignées</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Code</th>
              <th>Matière</th>
              <th>Classe</th>
              <th>Niveau</th>
              <th>Filière</th>
            </tr>
          </thead>
          <tbody>{aff_rows}</tbody>
        </table>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Emploi du temps — Séances planifiées</div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Jour</th>
              <th>Horaire</th>
              <th>Matière</th>
              <th>Classe</th>
              <th>Salle</th>
            </tr>
          </thead>
          <tbody>{sess_rows}</tbody>
        </table>
      </div>
      <div class="load-box">
        <div>
          <div class="load-label">{load_label}</div>
          <div class="load-sub">{sessions_count} séance(s) hebdomadaire(s)</div>
        </div>
        <div>
          <div class="load-hours">{weekly_hours}h</div>
          <div class="load-unit">par semaine</div>
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-title">Expériences professionnelles</div>
      <div class="table-wrap">
        <table>
          <thead><tr>
            <th>Poste</th><th>Établissement / Entreprise</th><th>Période</th><th>Description</th>
          </tr></thead>
          <tbody>{exp_rows if exp_rows else '<tr><td colspan="4" style="padding:20px;text-align:center;color:#94a3b8;font-style:italic">Aucune expérience enregistrée</td></tr>'}</tbody>
        </table>
      </div>
    </div>

    <div class="sig-grid">
      <div class="sig-box">
        <div class="sig-label">Signature de l&apos;enseignant</div>
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
      <div>{full_name} · {_s(teacher.employee_id)}</div>
    </div>
  </div>

</div>
</body></html>'''
